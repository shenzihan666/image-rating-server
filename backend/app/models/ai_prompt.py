"""
AI prompt storage models for configurable model prompts.
"""
from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class AIPrompt(Base):
    """Prompt definition for a specific AI model."""

    __tablename__ = "ai_prompts"
    __table_args__ = (
        UniqueConstraint("model_name", "name", name="uq_ai_prompts_model_name_name"),
    )

    id: str = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    model_name: str = Column(String(100), nullable=False, index=True)
    name: str = Column(String(255), nullable=False)
    description: str | None = Column(Text, nullable=True)
    is_active: bool = Column(Boolean, default=True, nullable=False)
    current_version_id: str | None = Column(
        String(36),
        nullable=True,
    )
    created_at: datetime = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: datetime = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    versions = relationship(
        "AIPromptVersion",
        back_populates="prompt",
        cascade="all, delete-orphan",
        foreign_keys="AIPromptVersion.prompt_id",
        order_by="desc(AIPromptVersion.version_number)",
    )

    def __repr__(self) -> str:
        return f"<AIPrompt(id={self.id}, model_name={self.model_name}, name={self.name})>"


class AIPromptVersion(Base):
    """Versioned prompt snapshot."""

    __tablename__ = "ai_prompt_versions"
    __table_args__ = (
        UniqueConstraint(
            "prompt_id",
            "version_number",
            name="uq_ai_prompt_versions_prompt_id_version_number",
        ),
    )

    id: str = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    prompt_id: str = Column(
        String(36),
        ForeignKey("ai_prompts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_number: int = Column(Integer, nullable=False)
    system_prompt: str = Column(Text, nullable=False)
    user_prompt: str = Column(Text, nullable=False)
    commit_message: str | None = Column(Text, nullable=True)
    created_by: str | None = Column(String(100), nullable=True)
    created_at: datetime = Column(DateTime, default=datetime.utcnow, nullable=False)

    prompt = relationship(
        "AIPrompt",
        back_populates="versions",
        foreign_keys=[prompt_id],
    )

    def __repr__(self) -> str:
        return (
            f"<AIPromptVersion(id={self.id}, prompt_id={self.prompt_id}, "
            f"version_number={self.version_number})>"
        )
