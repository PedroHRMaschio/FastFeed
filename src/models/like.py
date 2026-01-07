from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from src.models.user import Base

class Like(Base):
    """Like model representing a user liking a post."""
    __tablename__ = "likes"

    user_id = Column(UUID(as_uuid=True), ForeignKey("user.id"), primary_key=True)
    post_id = Column(UUID(as_uuid=True), ForeignKey("posts.id"), primary_key=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="likes")
    post = relationship("Post", back_populates="likes")

    def __repr__(self):
        return f"<Like user={self.user_id} post={self.post_id}>"
