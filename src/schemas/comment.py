from typing import List, Optional
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CommentCreate(BaseModel):
    content: str
    parent_id: Optional[UUID] = None


class CommentUpdate(BaseModel):
    content: str


class CommentRead(BaseModel):
    id: UUID
    user_id: UUID
    post_id: UUID
    parent_id: Optional[UUID]
    content: str
    created_at: datetime
    updated_at: Optional[datetime]
    email: str
    likes_count: int
    is_liked: bool
    children: List["CommentRead"] = []

    model_config = ConfigDict(from_attributes=True)
