from imagekitio import ImageKit
from src.core.config import IMAGEKIT_URL, IMAGEKIT_PUBLIC_KEY, IMAGEKIT_FILE_KEY

imagekit = ImageKit(
    url_endpoint=IMAGEKIT_URL,
    private_key=IMAGEKIT_FILE_KEY,
    public_key=IMAGEKIT_PUBLIC_KEY
)
