import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from src.models import Post, Like

@pytest.mark.asyncio
async def test_like_post(authenticated_client: AsyncClient, session: AsyncSession, test_post: Post):
    response = await authenticated_client.post(f"/posts/{test_post.id}/like")
    assert response.status_code == 201
    assert response.json() == {"message": "Post liked successfully"}

    # Like it again
    response = await authenticated_client.post(f"/posts/{test_post.id}/like")
    assert response.status_code == 201
    assert response.json() == {"message": "Post already liked"}

@pytest.mark.asyncio
async def test_unlike_post(authenticated_client: AsyncClient, test_post: Post):
    # First like it
    await authenticated_client.post(f"/posts/{test_post.id}/like")

    # Then unlike it
    response = await authenticated_client.delete(f"/posts/{test_post.id}/like")
    assert response.status_code == 200
    assert response.json() == {"message": "Post unliked successfully"}

    # Unlike again
    response = await authenticated_client.delete(f"/posts/{test_post.id}/like")
    assert response.status_code == 200
    assert response.json() == {"message": "Post not liked yet"}

@pytest.mark.asyncio
async def test_like_non_existent_post(authenticated_client: AsyncClient):
    random_id = uuid.uuid4()
    response = await authenticated_client.post(f"/posts/{random_id}/like")
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_feed_likes_info(authenticated_client: AsyncClient, test_post: Post):
    # Initial check
    response = await authenticated_client.get("/posts/feed")
    assert response.status_code == 200
    data = response.json()
    post_item = next(p for p in data["posts"] if p["id"] == str(test_post.id))
    assert post_item["likes_count"] == 0
    assert post_item["is_liked"] is False

    # Like the post
    await authenticated_client.post(f"/posts/{test_post.id}/like")

    # Check feed again
    response = await authenticated_client.get("/posts/feed")
    assert response.status_code == 200
    data = response.json()
    post_item = next(p for p in data["posts"] if p["id"] == str(test_post.id))
    assert post_item["likes_count"] == 1
    assert post_item["is_liked"] is True

    # Unlike the post
    await authenticated_client.delete(f"/posts/{test_post.id}/like")

     # Check feed again
    response = await authenticated_client.get("/posts/feed")
    assert response.status_code == 200
    data = response.json()
    post_item = next(p for p in data["posts"] if p["id"] == str(test_post.id))
    assert post_item["likes_count"] == 0
    assert post_item["is_liked"] is False
