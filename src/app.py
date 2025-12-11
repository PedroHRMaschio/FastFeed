from typing import List
from sqlalchemy import select
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import FastAPI, HTTPException, File, UploadFile, Form, Depends, status

from src.schemas import PostCreate, PostResponse
from src.db import Post, create_db_and_tables, get_async_session


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_db_and_tables()
    yield
    

app = FastAPI(lifespan=lifespan)


@app.post("/posts")
async def uploaf_file(
    file: UploadFile = File(...),
    caption: str = Form(""),
    session: AsyncSession = Depends(get_async_session)
):
    post = Post(
        caption=caption,
        url="testurl",
        file_type="photo",
        file_name="testname"
    )
    session.add(post)
    await session.commit()
    await session.refresh(post)
    return post


@app.get("/feed")
async def get_feed(
    session: AsyncSession = Depends(get_async_session)
):
    result = await session.execute(select(Post).order_by(Post.created_at.desc()))
    posts = result.scalars().all()

    posts_data = []
    for post in posts:
        posts_data.append(
            {
                "id": str(post.id),
                "caption": post.caption,
                "url": post.url,
                "file_type": post.file_type,
                "file_name": post.file_name,
                "created_at": post.created_at.isoformat()
            }
        )
    return {"posts": posts_data}

