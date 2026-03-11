"""
Database-backed AI model state.
"""
import json
from typing import Any

from loguru import logger
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_model import AIModel
from app.services.ai.registry import AIModelRegistry


def _deserialize_config(config_json: str | None) -> dict[str, Any]:
    if not config_json:
        return {}

    try:
        loaded = json.loads(config_json)
        return loaded if isinstance(loaded, dict) else {}
    except json.JSONDecodeError:
        logger.warning("Failed to decode stored AI model config JSON")
        return {}


def _serialize_config(config: dict[str, Any]) -> str | None:
    if not config:
        return None
    return json.dumps(config, ensure_ascii=False)


async def _build_model_payload(record: AIModel) -> dict[str, Any]:
    registry_model = await AIModelRegistry.get_model(record.name)
    config = _deserialize_config(record.config_json)
    config_fields = (
        [field.to_dict() for field in registry_model.config_fields]
        if registry_model is not None
        else []
    )
    configurable = registry_model.supports_configuration if registry_model else False
    configured = registry_model.is_configured(config) if registry_model else True

    return {
        "name": record.name,
        "description": record.description,
        "is_active": record.is_active,
        "is_loaded": registry_model.is_loaded() if registry_model else False,
        "configurable": configurable,
        "configured": configured,
        "config_fields": config_fields,
        "config": registry_model.get_public_config(config) if registry_model else {},
        "configured_secret_fields": (
            registry_model.get_configured_secret_fields(config) if registry_model else []
        ),
    }


async def sync_model_runtime_config(db: AsyncSession, name: str) -> None:
    """Push persisted model configuration into the in-memory analyzer instance."""
    result = await db.execute(select(AIModel).where(AIModel.name == name))
    record = result.scalar_one_or_none()
    if record is None:
        return

    registry_model = await AIModelRegistry.get_model(name)
    if registry_model is None:
        return

    await registry_model.on_config_updated(_deserialize_config(record.config_json))


async def sync_all_model_runtime_configs(db: AsyncSession) -> None:
    """Synchronize persisted model configuration for all registered analyzers."""
    result = await db.execute(select(AIModel))
    for record in result.scalars().all():
        await sync_model_runtime_config(db, record.name)


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
    """List all models from database with registry/config state."""
    result = await db.execute(select(AIModel).order_by(AIModel.name))
    models = result.scalars().all()
    return [await _build_model_payload(model) for model in models]


async def get_active_model(db: AsyncSession) -> AIModel | None:
    """Get the active model record from the database."""
    result = await db.execute(select(AIModel).where(AIModel.is_active))
    return result.scalar_one_or_none()


async def get_model_detail(db: AsyncSession, name: str) -> dict[str, Any] | None:
    """Return detailed model information including public configuration."""
    result = await db.execute(select(AIModel).where(AIModel.name == name))
    record = result.scalar_one_or_none()
    if record is None:
        return None
    return await _build_model_payload(record)


async def update_model_config(
    db: AsyncSession,
    name: str,
    updates: dict[str, Any],
) -> dict[str, Any] | None:
    """Persist model configuration and sync it to the runtime analyzer."""
    result = await db.execute(select(AIModel).where(AIModel.name == name))
    record = result.scalar_one_or_none()
    if record is None:
        return None

    registry_model = await AIModelRegistry.get_model(name)
    if registry_model is None:
        return None

    current_config = _deserialize_config(record.config_json)
    merged_config = registry_model.merge_configuration(current_config, updates)
    record.config_json = _serialize_config(merged_config)
    await db.commit()
    await db.refresh(record)

    await registry_model.on_config_updated(merged_config)
    if record.is_active:
        await AIModelRegistry.set_active(name, force_reload=True)

    return await _build_model_payload(record)


async def test_model_connection(
    db: AsyncSession,
    name: str,
) -> dict[str, Any] | None:
    """Run a model-specific connection test using persisted configuration."""
    result = await db.execute(select(AIModel).where(AIModel.name == name))
    record = result.scalar_one_or_none()
    if record is None:
        return None

    registry_model = await AIModelRegistry.get_model(name)
    if registry_model is None:
        return None

    config = _deserialize_config(record.config_json)
    return await registry_model.test_connection(config)


async def set_active_model(db: AsyncSession, name: str) -> dict[str, Any]:
    """Set a model active in registry and database."""
    result = await db.execute(select(AIModel).where(AIModel.name == name))
    record = result.scalar_one_or_none()
    if record is None:
        return {"status": "not_found"}

    registry_model = await AIModelRegistry.get_model(name)
    if registry_model is None:
        return {"status": "not_found"}

    config = _deserialize_config(record.config_json)
    missing_fields = registry_model.get_missing_required_fields(config)
    if missing_fields:
        return {"status": "not_configured", "missing_fields": missing_fields}

    await registry_model.on_config_updated(config)

    success = await AIModelRegistry.set_active(name)
    if not success:
        return {"status": "failed"}

    await db.execute(update(AIModel).values(is_active=False))
    await db.execute(update(AIModel).where(AIModel.name == name).values(is_active=True))
    await db.commit()
    return {"status": "ok"}


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

    registry_model = await AIModelRegistry.get_model(active.name)
    if registry_model is None:
        await db.execute(
            update(AIModel).where(AIModel.name == active.name).values(is_active=False)
        )
        await db.commit()
        return

    config = _deserialize_config(active.config_json)
    await registry_model.on_config_updated(config)

    if not registry_model.is_configured(config):
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
