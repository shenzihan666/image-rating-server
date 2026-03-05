"""
AI model database entity
"""
from datetime import datetime
from uuid import uuid4

from sqlalchemy import Boolean, Column, DateTime, String, Text
from sqlalchemy.orm import Mapped

from app.core.database import Base


class AIModel(Base):
    """AI model registry stored in the database."""

    __tablename__ = "ai_models"

    id: Mapped[str] = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
        nullable=False,
    )
    name: Mapped[str] = Column(String(100), unique=True, index=True, nullable=False)
    description: Mapped[str] = Column(Text, nullable=False)
    is_active: Mapped[bool] = Column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    def __init__(self, **kwargs):
        """Initialize AIModel with default id if not provided."""
        if "id" not in kwargs:
            kwargs["id"] = str(uuid4())
        super().__init__(**kwargs)

    def __repr__(self) -> str:
        return f"<AIModel(id={self.id}, name={self.name}, is_active={self.is_active})>"
