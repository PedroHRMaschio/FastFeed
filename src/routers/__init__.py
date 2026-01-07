from src.routers.auth import fastapi_users, auth_backend
from src.routers.posts import router as posts_router
from src.routers.comments import router as comments_router

__all__ = ["fastapi_users", "auth_backend", "posts_router", "comments_router"]
