import pytest
import io
from unittest.mock import MagicMock, patch
from fastapi import UploadFile, HTTPException

from src.utils.media import upload_media, delete_media

# Mock response object from ImageKit
class MockImageKitResponse:
    def __init__(self, url, name, file_id, http_status_code=200):
        self.url = url
        self.name = name
        self.file_id = file_id
        self.response_metadata = MagicMock()
        self.response_metadata.http_status_code = http_status_code

def create_upload_file(filename: str, content: bytes, content_type: str):
    file = io.BytesIO(content)
    return UploadFile(file=file, filename=filename, headers={"content-type": content_type})

class TestMediaUtils:
    
    @patch("src.utils.media.imagekit")
    def test_upload_media_image_success(self, mock_imagekit):
        """Test successful image upload."""
        # Setup mock return value
        mock_response = MockImageKitResponse(
            url="http://imagekit.io/test.jpg",
            name="test.jpg",
            file_id="12345"
        )
        mock_imagekit.upload_file.return_value = mock_response

        # Create dummy file
        file = create_upload_file("test.jpg", b"image content", "image/jpeg")

        # Call function
        url, file_type, name, file_id = upload_media(file)

        # Assertions
        assert url == "http://imagekit.io/test.jpg"
        assert file_type == "image"
        assert name == "test.jpg"
        assert file_id == "12345"
        mock_imagekit.upload_file.assert_called_once()

    @patch("src.utils.media.imagekit")
    def test_upload_media_video_success(self, mock_imagekit):
        """Test successful video upload."""
        mock_response = MockImageKitResponse(
            url="http://imagekit.io/test.mp4",
            name="test.mp4",
            file_id="67890"
        )
        mock_imagekit.upload_file.return_value = mock_response

        file = create_upload_file("test.mp4", b"video content", "video/mp4")

        url, file_type, name, file_id = upload_media(file)

        assert file_type == "video"
        assert file_id == "67890"

    @patch("src.utils.media.imagekit")
    def test_upload_media_failure(self, mock_imagekit):
        """Test upload failure from ImageKit."""
        # Mock a 500 response from ImageKit
        mock_response = MockImageKitResponse("", "", "", 500)
        mock_imagekit.upload_file.return_value = mock_response

        file = create_upload_file("test.jpg", b"content", "image/jpeg")

        with pytest.raises(HTTPException) as exc_info:
            upload_media(file)
        
        assert exc_info.value.status_code == 502
        assert "Failed to upload" in exc_info.value.detail

    @patch("src.utils.media.imagekit")
    def test_delete_media_success(self, mock_imagekit):
        """Test successful deletion."""
        mock_imagekit.delete_file.return_value = None
        
        result = delete_media("file_id_123")
        
        assert result is True
        mock_imagekit.delete_file.assert_called_once_with("file_id_123")

    @patch("src.utils.media.imagekit")
    def test_delete_media_exception(self, mock_imagekit):
        """Test deletion when exception occurs."""
        mock_imagekit.delete_file.side_effect = Exception("Delete failed")
        
        result = delete_media("file_id_123")
        
        assert result is False
