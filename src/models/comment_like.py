from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from src.models.user import Base

class CommentLike(Base):
    """CommentLike model representing a user liking a comment."""
    __tablename__ = "comment_likes"

    user_id = Column(UUID(as_uuid=True), ForeignKey("user.id"), primary_key=True)
    comment_id = Column(UUID(as_uuid=True), ForeignKey("comments.id"), primary_key=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="comment_likes")
    comment = relationship("Comment", back_populates="likes")

    def __repr__(self):
        return f"<CommentLike user={self.user_id} comment={self.comment_id}>"
