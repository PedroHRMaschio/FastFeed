import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from src.core.database import create_db_and_tables
from src.routers import fastapi_users, auth_backend, posts_router
from src.schemas import UserRead, UserCreate, UserUpdate

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables on startup
    await create_db_and_tables()
    yield


app = FastAPI(
    title="FastFeed API",
    description="""
    ## Overview
    
    FastFeed is a modern social media API built with FastAPI.
    
    ### Key Features
    - 🔐 **Authentication**: JWT-based auth with refresh tokens
    - 📸 **Media Upload**: Integration with ImageKit for image/video storage
    - 🚀 **Performance**: Async database operations

    ## Authentication
    
    Most endpoints require authentication. Use the `/auth/jwt/login` endpoint to get a token.
    """,
    version="1.0.0",
    lifespan=lifespan
)

# Global Exception Handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    # Log the full error internally
    logger.error(f"Global error handler caught: {exc}", exc_info=True)
    # Return a generic message to the user
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error. Please contact support."}
    )

# CORS Configuration
origins = [
    "http://localhost:8501",  # Streamlit default port
    "http://localhost:3000",  # React default port
    "http://127.0.0.1:8501",
    "*"                       # Allow all for development
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
