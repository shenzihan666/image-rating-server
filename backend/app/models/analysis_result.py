"""
Analysis Result database model - stores AI analysis results persistently
"""
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Column, DateTime, Float, ForeignKey, String, Text

from app.core.database import Base

if TYPE_CHECKING:
    pass


class AnalysisResult(Base):
    """
    AnalysisResult model for storing AI analysis results.

    Each image can have multiple analysis results from different models
    or from re-analyzing with the same model.
    """

    __tablename__ = "analysis_results"

    id: str = Column(String(36), primary_key=True, index=True)
    image_id: str = Column(String(36), ForeignKey("images.id", ondelete="CASCADE"), nullable=False, index=True)
    model: str = Column(String(100), nullable=False, index=True)  # "nima", etc.
    score: float | None = Column(Float, nullable=True)  # Mean score (1-10)
    min_score: float | None = Column(Float, nullable=True)
    max_score: float | None = Column(Float, nullable=True)
    distribution: str | None = Column(Text, nullable=True)  # JSON encoded distribution array
    details: str | None = Column(Text, nullable=True)  # JSON encoded full details
    created_at: datetime = Column(DateTime, default=datetime.utcnow, index=True)

    def __repr__(self) -> str:
        return f"<AnalysisResult(id={self.id}, image_id={self.image_id}, model={self.model}, score={self.score})>"
