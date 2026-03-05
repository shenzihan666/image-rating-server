"""
Image database model
"""
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, relationship

if TYPE_CHECKING:
    from .user import User

from app.core.database import Base


class Image(Base):
    """
    Image model for storing image metadata and ratings.
    """

    __tablename__ = "images"

    id: str = Column(String(36), primary_key=True, index=True)
    user_id: str = Column(String(36), ForeignKey("users.id"), nullable=False)
    title: str = Column(String(255), nullable=False)
    description: Optional[str] = Column(Text, nullable=True)
    file_path: str = Column(String(500), nullable=False)
    file_size: int = Column(Integer, nullable=False)  # in bytes
    width: int = Column(Integer, nullable=True)
    height: int = Column(Integer, nullable=True)
    mime_type: str = Column(String(100), nullable=False)
    average_rating: float = Column(Float, default=0.0)
    rating_count: int = Column(Integer, default=0)
    created_at: datetime = Column(DateTime, default=datetime.utcnow)
    updated_at: datetime = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    # user: Mapped["User"] = relationship(back_populates="images")

    def __repr__(self) -> str:
        return f"<Image(id={self.id}, title={self.title}, average_rating={self.average_rating})>"
