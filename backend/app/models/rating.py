"""
Rating database model
"""
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint

if TYPE_CHECKING:
    pass

from app.core.database import Base


class Rating(Base):
    """
    Rating model for storing user ratings on images.
    """

    __tablename__ = "ratings"
    __table_args__ = (
        UniqueConstraint("user_id", "image_id", name="unique_user_image_rating"),
    )

    id: str = Column(String(36), primary_key=True, index=True)
    user_id: str = Column(String(36), ForeignKey("users.id"), nullable=False)
    image_id: str = Column(String(36), ForeignKey("images.id"), nullable=False)
    score: int = Column(Integer, nullable=False)  # 1-5 rating
    comment: str | None = Column(String(1000), nullable=True)
    created_at: datetime = Column(DateTime, default=datetime.utcnow)
    updated_at: datetime = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    # user: Mapped["User"] = relationship(back_populates="ratings")
    # image: Mapped["Image"] = relationship(back_populates="ratings")

    def __repr__(self) -> str:
        return f"<Rating(id={self.id}, user_id={self.user_id}, image_id={self.image_id}, score={self.score})>"
