import os
import uuid
import shutil
import logging
import tempfile
from typing import List

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from imagekitio.models.UploadFileRequestOptions import UploadFileRequestOptions
from fastapi import APIRouter, HTTPException, File, UploadFile, Form, Depends, status

from src.core.imagekit import imagekit
from src.core.database import get_async_session
from src.models import Post, User
from src.schemas.post import PostResponse, FeedResponse, PostFeedItem
from src.dependencies import current_active_user

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
    temp_file_path = None

    try:
        # Create a temporary file to handle the upload
        suffix = os.path.splitext(file.filename)[1] if file.filename else ""
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_file_path = temp_file.name
            shutil.copyfileobj(file.file, temp_file)

        # Upload to ImageKit
        # Note: imagekitio library doesn't fully support async yet, so this might block slightly
        # In a high-scale app, run this in a thread pool
        with open(temp_file_path, "rb") as f:
            upload_result = imagekit.upload_file(
                file=f,
                file_name=file.filename or f"upload-{uuid.uuid4()}",
                options=UploadFileRequestOptions(
                    use_unique_file_name=True,
                    tags=["backend-upload"]
                )
            )

        if upload_result.response_metadata.http_status_code == 200:
            content_type = file.content_type or "application/octet-stream"
            file_type = "video" if content_type.startswith("video/") else "image"

            post = Post(
                user_id=user.id,
                caption=caption,
                url=upload_result.url,
                file_type=file_type,
                file_name=upload_result.name
            )
            session.add(post)
            await session.commit()
            await session.refresh(post)
            return post
        else:
            logger.error(f"ImageKit upload failed: {upload_result.response_metadata}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to upload file to storage service"
            )

    except Exception as e:
        logger.exception("Error creating post")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    finally:
        # Clean up temporary file
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
            except OSError as e:
                logger.warning(f"Failed to delete temp file {temp_file_path}: {e}")
        file.file.close()


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
                    "is_owner": post.user_id == user.id,
                    "email": user_email
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

        # Delete from ImageKit
        try:
            # Since we don't store file_id, we need to find it first using the unique file_name
            files = imagekit.list_files({
                "name": post.file_name,
                "limit": 1
            })

            # Check if we found the file and safely access the list
            if files and hasattr(files, 'list') and files.list:
                file_id = files.list[0].file_id
                imagekit.delete_file(file_id)
                logger.info(f"Deleted file {post.file_name} ({file_id}) from ImageKit")
            else:
                logger.warning(f"Could not find file {post.file_name} in ImageKit for deletion")

        except Exception as e:
             logger.warning(f"Failed to delete file from ImageKit: {e}")

        await session.delete(post)
        await session.commit()
        return {"success": True, "message": "Post deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error deleting post {post_id}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")
