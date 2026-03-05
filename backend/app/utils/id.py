"""
Utility functions for ID generation
"""
import uuid


def generate_id() -> str:
    """
    Generate a unique ID.

    Returns:
        UUID string
    """
    return str(uuid.uuid4())
