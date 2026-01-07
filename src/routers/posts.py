import logging
import uuid
from typing import List

from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, HTTPException, File, UploadFile, Form, Depends, status

from src.core.database import get_async_session
from src.models import Post, User, Like
from src.schemas.post import PostResponse, FeedResponse, PostFeedItem
from src.dependencies import current_active_user
from src.utils import upload_media, delete_media

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/posts", tags=["posts"])


@router.post("", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = File(...),
    caption: str = Form(""),
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
) -> Post:
    """
    Upload a file (image or video) and create a new post.

    Args:
        file (UploadFile): The file to upload.
        caption (str): Optional caption for the post.
        user (User): The current authenticated user.
        session (AsyncSession): Database session.

    Returns:
        Post: The created post object.

    Raises:
        HTTPException: If upload fails or database error occurs.
    """
    try:
        # Upload media using utility function
        url, file_type, file_name, file_id = upload_media(file)

        post = Post(
            user_id=user.id,
            caption=caption,
            url=url,
            file_type=file_type,
            file_name=file_name,
            file_id=file_id
        )
        session.add(post)
        await session.commit()
        await session.refresh(post)
        return post

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error creating post")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/feed", response_model=FeedResponse)
async def get_feed(
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user)
) -> FeedResponse:
    """
    Get the feed of posts from all users.

    Args:
        session (AsyncSession): Database session.
        user (User): Current authenticated user.

    Returns:
        FeedResponse: List of posts with user details and ownership flag.
    """
    # Eager load user data to avoid N+1 queries
    result = await session.execute(
        select(Post).order_by(Post.created_at.desc())
    )
    posts = result.scalars().all()

    # Manual user fetch to ensure reliability
    user_ids = {post.user_id for post in posts}
    user_dict = {}

    if user_ids:
        result = await session.execute(
            select(User).where(User.id.in_(user_ids))
        )
        users = result.scalars().all()
        user_dict = {user.id: user.email for user in users}

    # Fetch likes count and user liked status
    post_ids = [post.id for post in posts]
    likes_data = {}
    user_likes = set()

    if post_ids:
        # Count likes for each post
        likes_result = await session.execute(
            select(Like.post_id, func.count(Like.user_id))
            .where(Like.post_id.in_(post_ids))
            .group_by(Like.post_id)
        )
        likes_data = {row[0]: row[1] for row in likes_result.all()}

        # Check which posts the current user liked
        user_likes_result = await session.execute(
            select(Like.post_id)
            .where(Like.post_id.in_(post_ids))
            .where(Like.user_id == user.id)
        )
        user_likes = {row[0] for row in user_likes_result.all()}

    posts_data = []
    for post in posts:
        # Get email from dictionary, fallback to "Unknown User"
        user_email = user_dict.get(post.user_id, "Unknown User")

        posts_data.append(
            PostFeedItem.model_validate(
                {
                    "id": post.id,
                    "user_id": post.user_id,
                    "caption": post.caption,
                    "url": post.url,
                    "file_type": post.file_type,
                    "file_name": post.file_name,
                    "created_at": post.created_at,
                    "updated_at": post.updated_at,
                    "is_owner": post.user_id == user.id,
                    "email": user_email,
                    "likes_count": likes_data.get(post.id, 0),
                    "is_liked": post.id in user_likes
                }
            )
        )
    return FeedResponse(posts=posts_data)


@router.delete("/{post_id}", status_code=status.HTTP_200_OK)
async def delete_post(
    post_id: str,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user)
) -> dict:
    """
    Delete a specific post.

    Args:
        post_id (str): UUID string of the post to delete.
        session (AsyncSession): Database session.
        user (User): Current authenticated user.

    Returns:
        dict: Success message.

    Raises:
        HTTPException: If post not found or user unauthorized.
        ValueError: If post_id is not a valid UUID.
    """
    try:
        try:
            post_uuid = uuid.UUID(post_id)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid post ID format")

        result = await session.execute(select(Post).where(Post.id == post_uuid))
        post = result.scalars().first()

        if not post:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

        if post.user_id != user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not authorized to delete this post")

        # Delete from ImageKit using utility
        delete_media(post.file_id, post.file_name)

        await session.delete(post)
        await session.commit()
        return {"success": True, "message": "Post deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error deleting post {post_id}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.post("/{post_id}/like", status_code=status.HTTP_201_CREATED)
async def like_post(
    post_id: str,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user)
) -> dict:
    """
    Like a specific post.

    Args:
        post_id (str): UUID string of the post to like.
        session (AsyncSession): Database session.
        user (User): Current authenticated user.

    Returns:
        dict: Success message.
    """
    try:
        try:
            post_uuid = uuid.UUID(post_id)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid post ID format")

        result = await session.execute(select(Post).where(Post.id == post_uuid))
        post = result.scalars().first()

        if not post:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

        # Check if already liked
        existing_like = await session.execute(
            select(Like).where(Like.user_id == user.id, Like.post_id == post_uuid)
        )
        if existing_like.scalars().first():
            return {"message": "Post already liked"}

        like = Like(user_id=user.id, post_id=post_uuid)
        session.add(like)
        await session.commit()
        return {"message": "Post liked successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error liking post {post_id}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.delete("/{post_id}/like", status_code=status.HTTP_200_OK)
async def unlike_post(
    post_id: str,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user)
) -> dict:
    """
    Unlike a specific post.

    Args:
        post_id (str): UUID string of the post to unlike.
        session (AsyncSession): Database session.
        user (User): Current authenticated user.

    Returns:
        dict: Success message.
    """
    try:
        try:
            post_uuid = uuid.UUID(post_id)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid post ID format")

        result = await session.execute(select(Post).where(Post.id == post_uuid))
        post = result.scalars().first()

        if not post:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

        # Check if liked
        result = await session.execute(
            select(Like).where(Like.user_id == user.id, Like.post_id == post_uuid)
        )
        like = result.scalars().first()

        if not like:
            return {"message": "Post not liked yet"}

        await session.delete(like)
        await session.commit()
        return {"message": "Post unliked successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error unliking post {post_id}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.patch("/{post_id}", response_model=PostResponse)
async def update_post(
    post_id: str,
    caption: str | None = Form(None),
    file: UploadFile | str | None = File(None),
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user)
) -> Post:
    """
    Update a specific post (caption and/or file).

    Args:
        post_id (str): UUID string of the post to update.
        caption (str | None): New caption (optional).
        file (UploadFile | str | None): New file to replace the existing one (optional).
                                      Note: str allowed to handle empty form fields from some clients.
        session (AsyncSession): Database session.
        user (User): Current authenticated user.

    Returns:
        Post: The updated post object.
    """
    try:
        try:
            post_uuid = uuid.UUID(post_id)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid post ID format")

        result = await session.execute(select(Post).where(Post.id == post_uuid))
        post = result.scalars().first()

        if not post:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

        if post.user_id != user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not authorized to update this post")

        # Update caption if provided
        if caption is not None:
            post.caption = caption

        # Update file if provided and valid (check for filename to ensure it's a file object)
        if file and hasattr(file, 'filename') and file.filename:
            # 1. Delete old file from ImageKit using utility
            delete_media(post.file_id, post.file_name)

            # 2. Upload new file using utility
            # Note: upload_media handles the whole temp file process
            url, file_type, file_name, file_id = upload_media(file)

            # Update post with new file details
            post.url = url
            post.file_type = file_type
            post.file_name = file_name
            post.file_id = file_id

        # Update timestamp (managed by onupdate in model, but we can trigger it)
        # SQLAlchemy handles onupdate automatically when fields change.
        # But if we want to ensure it, we can touch it, though usually unnecessary.
        
        await session.commit()
        await session.refresh(post)
        return post

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error updating post {post_id}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")
