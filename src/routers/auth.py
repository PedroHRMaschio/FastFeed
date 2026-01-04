import uuid
from typing import Optional

from fastapi import HTTPException, status, Depends, Request
from fastapi_users import BaseUserManager, FastAPIUsers, UUIDIDMixin, models
from fastapi_users.authentication import AuthenticationBackend, BearerTransport, JWTStrategy
from fastapi_users.db import SQLAlchemyUserDatabase

from src.models import User
from src.core.database import get_user_db
from src.core.config import JWT_SECRET, JWT_LIFETIME


class UserManager(UUIDIDMixin, BaseUserManager[User, uuid.UUID]):
    reset_password_token_secret = JWT_SECRET
    verification_token_secret = JWT_SECRET

    async def validate_password(
        self,
        password: str,
        user: models.UP,
    ) -> Optional[str]:
        """
        Validate the password requirements.
        
        Args:
            password (str): The password to validate.
            user (models.UP): The user object.
            
        Returns:
            Optional[str]: Error message if invalid, None if valid.
        """
        if len(password) < 8:
            return "Password must be at least 8 characters long"
        return None

    async def on_after_register(
        self, user: User, request: Optional[Request] = None
    ):
        """Callback executed after successful user registration."""
        print(f"User {user.id} has registered successfully!")

    async def on_after_forgot_password(
        self, user: User, request: Optional[Request] = None
    ):
        """Callback executed after a user requests a password reset."""
        print(f"User {user.id} has forgot their password. Reset token: {user.verification_token}")

    async def on_after_request_verify(
        self, user: User, token: str, request: Optional[Request] = None
    ):
        """Callback executed after a user requests email verification."""
        print(f"Verification requested for user {user.id}. Verification token: {token}")


async def get_user_manager(user_db: SQLAlchemyUserDatabase = Depends(get_user_db)):
    """Dependency to get the user manager instance."""
    yield UserManager(user_db)


bearer_transport = BearerTransport(tokenUrl="auth/jwt/login")


def get_jwt_strategy() -> JWTStrategy:
    """Return the JWT strategy with configured secret and lifetime."""
    return JWTStrategy(secret=JWT_SECRET, lifetime_seconds=JWT_LIFETIME)


auth_backend = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)

fastapi_users = FastAPIUsers[User, uuid.UUID](get_user_manager, [auth_backend])
