from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core.database import create_db_and_tables
from src.routers import fastapi_users, auth_backend, posts_router
from src.schemas import UserRead, UserCreate, UserUpdate


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create db tables
    await create_db_and_tables()
    yield
    # Shutdown events can be added here


app = FastAPI(
    title="FastFeed",
    description="""
    # FastFeed API

    A robust social media backend featuring:
    - 🔐 **Authentication**: JWT-based auth with refresh tokens
    - 📸 **Media Upload**: Integration with ImageKit for image/video storage
    - 🚀 **Performance**: Async database operations

    ## Authentication

    Most endpoints require authentication. Use the `/auth/jwt/login` endpoint to get a token.
    """,
    version="1.0.0",
    lifespan=lifespan,
    contact={
        "name": "PedroHRMaschio",
        "url": "https://github.com/PedroHRMaschio",
    },
    license_info={
        "name": "MIT",
    },
)

# CORS Configuration
# Allow requests from common frontend ports
origins = [
    "http://localhost",
    "http://localhost:3000",
    "http://localhost:8000",
    "http://localhost:8501", # Streamlit
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health", tags=["system"])
async def health_check():
    """Health check endpoint to verify service status."""
    return {"status": "ok", "version": "1.0.0"}

# Include authentication routers
app.include_router(
    fastapi_users.get_auth_router(auth_backend),
    prefix="/auth/jwt",
    tags=["auth"]
)
app.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="/auth",
    tags=["auth"]
)
app.include_router(
    fastapi_users.get_reset_password_router(),
    prefix="/auth",
    tags=["auth"]
)
app.include_router(
    fastapi_users.get_verify_router(UserRead),
    prefix="/auth",
    tags=["auth"]
)
app.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
    prefix="/users",
    tags=["users"]
)

# Include posts router
app.include_router(posts_router)
