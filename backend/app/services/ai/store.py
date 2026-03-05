"""
Database-backed AI model state
"""

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_model import AIModel
from app.services.ai.registry import AIModelRegistry


async def ensure_ai_models(db: AsyncSession) -> None:
    """Ensure built-in models exist in the database."""
    specs = await AIModelRegistry.list_models()
    for spec in specs:
        result = await db.execute(select(AIModel).where(AIModel.name == spec["name"]))
        existing = result.scalar_one_or_none()
        if existing:
            if existing.description != spec["description"]:
                existing.description = spec["description"]
        else:
            db.add(
                AIModel(
                    name=spec["name"],
                    description=spec["description"],
                    is_active=False,
                )
            )
    await db.commit()


async def list_models(db: AsyncSession) -> list[dict]:
    """List all models from database with registry load status."""
    result = await db.execute(select(AIModel).order_by(AIModel.name))
    models = result.scalars().all()
    items: list[dict] = []
    for model in models:
        reg = await AIModelRegistry.get_model(model.name)
        items.append(
            {
                "name": model.name,
                "description": model.description,
                "is_active": model.is_active,
                "is_loaded": reg.is_loaded() if reg else False,
            }
        )
    return items


async def get_active_model(db: AsyncSession) -> AIModel | None:
    """Get the active model record from the database."""
    result = await db.execute(select(AIModel).where(AIModel.is_active))
    return result.scalar_one_or_none()


async def set_active_model(db: AsyncSession, name: str) -> str:
    """Set a model active in registry and database.

    Returns: "ok", "not_found", or "failed"
    """
    result = await db.execute(select(AIModel).where(AIModel.name == name))
    record = result.scalar_one_or_none()
    if record is None:
        return "not_found"

    if await AIModelRegistry.get_model(name) is None:
        return "not_found"

    success = await AIModelRegistry.set_active(name)
    if not success:
        return "failed"

    await db.execute(update(AIModel).values(is_active=False))
    await db.execute(update(AIModel).where(AIModel.name == name).values(is_active=True))
    await db.commit()
    return "ok"


async def deactivate_model(db: AsyncSession) -> bool:
    """Deactivate the active model in registry and database."""
    await AIModelRegistry.deactivate()
    await db.execute(update(AIModel).values(is_active=False))
    await db.commit()
    return True


async def restore_active_model(db: AsyncSession) -> None:
    """Restore active model from database into registry at startup."""
    active = await get_active_model(db)
    if active is None:
        return

    if await AIModelRegistry.get_model(active.name) is None:
        await db.execute(
            update(AIModel).where(AIModel.name == active.name).values(is_active=False)
        )
        await db.commit()
        return

    success = await AIModelRegistry.set_active(active.name)
    if not success:
        await db.execute(
            update(AIModel).where(AIModel.name == active.name).values(is_active=False)
        )
        await db.commit()
