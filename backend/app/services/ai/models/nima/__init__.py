"""
NIMA (Neural Image Assessment) model package
"""
from app.services.ai.models.nima.analyzer import NIMAAnalyzer
from app.services.ai.models.nima.model import NIMA

__all__ = ["NIMA", "NIMAAnalyzer"]
