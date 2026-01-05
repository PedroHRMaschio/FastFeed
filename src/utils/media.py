import os
import shutil
import uuid
import tempfile
import logging
from typing import Optional, Tuple

from fastapi import UploadFile, HTTPException, status
from imagekitio.models.UploadFileRequestOptions import UploadFileRequestOptions

from src.core.imagekit import imagekit

logger = logging.getLogger(__name__)

def upload_media(file: UploadFile) -> Tuple[str, str, str, str]:
    """
    Upload a file to ImageKit.

    Args:
        file (UploadFile): The file to upload.

    Returns:
        Tuple[str, str, str, str]: (url, file_type, file_name, file_id)
    
    Raises:
        HTTPException: If upload fails.
    """
    temp_file_path = None
    try:
        # Create a temporary file to handle the upload
        suffix = os.path.splitext(file.filename)[1] if file.filename else ""
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_file_path = temp_file.name
            # Ensure we're at the start of the file
            file.file.seek(0)
            shutil.copyfileobj(file.file, temp_file)

        # Upload to ImageKit
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
            
            return (
                upload_result.url,
                file_type,
                upload_result.name,
                upload_result.file_id
            )
        else:
            logger.error(f"ImageKit upload failed: {upload_result.response_metadata}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to upload file to storage service"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error uploading media")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Media upload failed: {str(e)}"
        )
    finally:
        # Clean up temporary file
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
            except OSError as e:
                logger.warning(f"Failed to delete temp file {temp_file_path}: {e}")


def delete_media(file_id: str, file_name: str = "Unknown") -> bool:
    """
    Delete a file from ImageKit using its file_id.

    Args:
        file_id (str): The unique ImageKit file ID.
        file_name (str): The file name for logging purposes.

    Returns:
        bool: True if deletion was attempted (ImageKit doesn't strictly return success/fail in sync mode same way).
    """
    try:
        imagekit.delete_file(file_id)
        logger.info(f"Deleted file {file_name} ({file_id}) from ImageKit")
        return True
    except Exception as e:
        logger.warning(f"Failed to delete file {file_name} from ImageKit: {e}")
        return False
