from dotenv import load_dotenv
from imagekitio import ImageKit
import os

load_dotenv()

imagekit = ImageKit(
    url_endpoint=os.getenv("IMAGEKIT_URL"),
    private_key=os.getenv("IMAGEKIT_FILE_KEY"),
    public_key=os.getenv("IMAGEKIT_PUBLIC_KEY")
)
