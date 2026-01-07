import uuid
from typing import List
import traceback
import logging

from sqlalchemy import select, func, desc, asc
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, HTTPException, Depends, status

from src.core.database import get_async_session
from src.models import Comment, Post, User, CommentLike
from src.schemas.comment import CommentCreate, CommentRead, CommentUpdate
from src.dependencies import current_active_user

logger = logging.getLogger(__name__)

router = APIRouter(tags=["comments"])


@router.post("/posts/{post_id}/comments", response_model=CommentRead, status_code=status.HTTP_201_CREATED)
async def create_comment(
    post_id: str,
    comment_in: CommentCreate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    try:
        try:
            post_uuid = uuid.UUID(post_id)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid post ID format")

        # Verify post exists
        post = await session.get(Post, post_uuid)
        if not post:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

        # Verify parent comment if provided
        if comment_in.parent_id:
            parent = await session.get(Comment, comment_in.parent_id)
            if not parent:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parent comment not found")
            if parent.post_id != post_uuid:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Parent comment belongs to a different post")

        comment = Comment(
            user_id=user.id,
            post_id=post_uuid,
            parent_id=comment_in.parent_id,
            content=comment_in.content
        )
        session.add(comment)
        await session.commit()
        await session.refresh(comment)

        # Construct response
        return CommentRead(
            id=comment.id,
            user_id=comment.user_id,
            post_id=comment.post_id,
            parent_id=comment.parent_id,
            content=comment.content,
            created_at=comment.created_at,
            updated_at=comment.updated_at,
            email=user.email,
            likes_count=0,
            is_liked=False,
            children=[]
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error creating comment")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/posts/{post_id}/comments", response_model=List[CommentRead])
async def get_comments(
    post_id: str,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    try:
        try:
            post_uuid = uuid.UUID(post_id)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid post ID format")

        # Fetch all comments for the post
        # IMPORTANT: Eager load 'user' so we can access email
        result = await session.execute(
            select(Comment)
            .where(Comment.post_id == post_uuid)
            .options(selectinload(Comment.user))
        )
        comments = result.scalars().all()

        if not comments:
            return []

        comment_ids = [c.id for c in comments]

        # Fetch likes count
        likes_result = await session.execute(
            select(CommentLike.comment_id, func.count(CommentLike.user_id))
            .where(CommentLike.comment_id.in_(comment_ids))
            .group_by(CommentLike.comment_id)
        )
        likes_map = {row[0]: row[1] for row in likes_result.all()}

        # Fetch user likes
        user_likes_result = await session.execute(
            select(CommentLike.comment_id)
            .where(CommentLike.comment_id.in_(comment_ids))
            .where(CommentLike.user_id == user.id)
        )
        user_likes = {row[0] for row in user_likes_result.all()}

        # Build tree
        comment_map = {}
        root_comments = []

        # First pass: create CommentRead objects
        for comment in comments:
            # Handle potential missing user (though should be enforced by FK)
            # The 'selectinload' above should have populated it.
            # If it's None, it might be due to session expire/refresh behavior or testing artifacts.

            user_email = "Unknown"
            if comment.user:
                user_email = comment.user.email
            else:
                # Try to reload if missing? Or just log warning?
                # In sqlite+asyncio tests, sometimes relationships need explicit handling or refresh?
                # But selectinload usually works.
                # Let's try to fetch user if missing
                pass

            comment_read = CommentRead(
                id=comment.id,
                user_id=comment.user_id,
                post_id=comment.post_id,
                parent_id=comment.parent_id,
                content=comment.content,
                created_at=comment.created_at,
                updated_at=comment.updated_at,
                email=user_email,
                likes_count=likes_map.get(comment.id, 0),
                is_liked=comment.id in user_likes,
                children=[]
            )
            comment_map[comment.id] = comment_read

        # Second pass: build hierarchy
        for comment in comments:
            c_read = comment_map[comment.id]
            if comment.parent_id:
                if comment.parent_id in comment_map:
                    comment_map[comment.parent_id].children.append(c_read)
            else:
                root_comments.append(c_read)

        # Sort functions
        def sort_children(children):
            if not children:
                return

            if len(children) <= 3:
                children.sort(key=lambda x: x.likes_count, reverse=True)
            else:
                top_3 = sorted(children, key=lambda x: x.likes_count, reverse=True)[:3]
                top_3_ids = {c.id for c in top_3}

                rest = [c for c in children if c.id not in top_3_ids]
                rest.sort(key=lambda x: x.created_at)

                children[:] = top_3 + rest

            for child in children:
                sort_children(child.children)

        # Sort root comments by likes
        root_comments.sort(key=lambda x: x.likes_count, reverse=True)

        # Sort children
        for root in root_comments:
            sort_children(root.children)

        return root_comments

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error fetching comments for post {post_id}")
        traceback.print_exc() # Ensure it prints to stderr for pytest -s
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.delete("/comments/{comment_id}", status_code=status.HTTP_200_OK)
async def delete_comment(
    comment_id: str,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    try:
        try:
            comment_uuid = uuid.UUID(comment_id)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid comment ID format")

        comment = await session.get(Comment, comment_uuid)
        if not comment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")

        if comment.user_id != user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete this comment")

        await session.delete(comment)
        await session.commit()
        return {"message": "Comment deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error deleting comment {comment_id}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.patch("/comments/{comment_id}", response_model=CommentRead)
async def update_comment(
    comment_id: str,
    comment_in: CommentUpdate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    try:
        try:
            comment_uuid = uuid.UUID(comment_id)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid comment ID format")

        comment = await session.get(Comment, comment_uuid)
        if not comment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")

        if comment.user_id != user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update this comment")

        comment.content = comment_in.content
        await session.commit()
        await session.refresh(comment)

        # We need likes count and status to match response model
        likes_count = await session.scalar(
            select(func.count(CommentLike.user_id)).where(CommentLike.comment_id == comment_uuid)
        )
        is_liked = await session.scalar(
            select(CommentLike).where(CommentLike.comment_id == comment_uuid, CommentLike.user_id == user.id)
        ) is not None

        # Re-fetch user email
        comment_user = await session.get(User, comment.user_id)

        return CommentRead(
            id=comment.id,
            user_id=comment.user_id,
            post_id=comment.post_id,
            parent_id=comment.parent_id,
            content=comment.content,
            created_at=comment.created_at,
            updated_at=comment.updated_at,
            email=comment_user.email,
            likes_count=likes_count or 0,
            is_liked=is_liked,
            children=[]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error updating comment {comment_id}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/comments/{comment_id}/like", status_code=status.HTTP_201_CREATED)
async def like_comment(
    comment_id: str,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    try:
        try:
            comment_uuid = uuid.UUID(comment_id)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid comment ID format")

        comment = await session.get(Comment, comment_uuid)
        if not comment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")

        existing_like = await session.get(CommentLike, (user.id, comment_uuid))
        if existing_like:
            return {"message": "Comment already liked"}

        like = CommentLike(user_id=user.id, comment_id=comment_uuid)
        session.add(like)
        await session.commit()
        return {"message": "Comment liked successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error liking comment {comment_id}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.delete("/comments/{comment_id}/like", status_code=status.HTTP_200_OK)
async def unlike_comment(
    comment_id: str,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    try:
        try:
            comment_uuid = uuid.UUID(comment_id)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid comment ID format")

        like = await session.get(CommentLike, (user.id, comment_uuid))
        if not like:
            return {"message": "Comment not liked"}

        await session.delete(like)
        await session.commit()
        return {"message": "Comment unliked successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error unliking comment {comment_id}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
