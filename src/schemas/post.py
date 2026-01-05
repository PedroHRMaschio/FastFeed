from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class PostCreate(BaseModel):
    """Schema for creating a new post."""
    caption: str = ""


class PostResponse(BaseModel):
    """Schema for post response."""
    id: UUID
    user_id: UUID
    caption: str | None
    url: str
    file_type: str
    file_name: str
    created_at: datetime
    updated_at: datetime | None = None
    
    model_config = ConfigDict(from_attributes=True)


class PostFeedItem(PostResponse):
    """Schema for a post item in the feed, including ownership status."""
    is_owner: bool
    email: str


class FeedResponse(BaseModel):
    """Schema for the feed response containing a list of posts."""
    posts: list[PostFeedItem]
