from dotenv import load_dotenv
import os

load_dotenv()

# JWT Configuration
JWT_SECRET = os.getenv("JWT_SECRET")
JWT_LIFETIME = int(os.getenv("JWT_LIFETIME", "3600"))

# ImageKit Configuration
IMAGEKIT_URL = os.getenv("IMAGEKIT_URL")
IMAGEKIT_PUBLIC_KEY = os.getenv("IMAGEKIT_PUBLIC_KEY")
IMAGEKIT_FILE_KEY = os.getenv("IMAGEKIT_FILE_KEY")
