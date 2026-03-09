"""
Qwen3-VL analyzer implementation using an OpenAI-compatible API.
"""
import asyncio
import base64
import json
import mimetypes
import re
from pathlib import Path
from typing import Any

from loguru import logger

from app.core.config import settings
from app.core.database import async_session_maker
from app.services.ai.base import AIModelConfigFieldDef, BaseAIAnalyzer
from app.services.ai.prompt_store import (
    ActivePromptVersion,
    DEFAULT_QWEN_SYSTEM_PROMPT,
    DEFAULT_QWEN_USER_PROMPT,
    get_active_prompt_version,
)

DEFAULT_QWEN_VL_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
DEFAULT_QWEN_VL_MODEL = "qwen3-vl-plus"


class QwenVLAnalyzer(BaseAIAnalyzer):
    """Qwen3-VL remote analyzer."""

    def __init__(self) -> None:
        self._config: dict[str, Any] = {}
        self._loaded = False

    @property
    def name(self) -> str:
        return "qwen3-vl"

    @property
    def description(self) -> str:
        return "Qwen3-VL remote analyzer via OpenAI-compatible API"

    @property
    def config_fields(self) -> tuple[AIModelConfigFieldDef, ...]:
        return (
            AIModelConfigFieldDef(
                key="api_key",
                label="API Key",
                field_type="password",
                required=True,
                secret=True,
                placeholder="sk-...",
                help_text="DashScope or any compatible provider API key",
            ),
            AIModelConfigFieldDef(
                key="base_url",
                label="Base URL",
                field_type="url",
                required=True,
                placeholder=DEFAULT_QWEN_VL_BASE_URL,
                help_text="OpenAI-compatible API base URL",
            ),
            AIModelConfigFieldDef(
                key="model_name",
                label="Model Name",
                field_type="text",
                required=True,
                placeholder=DEFAULT_QWEN_VL_MODEL,
                help_text="Remote vision model identifier",
            ),
        )

    def prepare_configuration(self, config: dict[str, Any] | None) -> dict[str, Any]:
        prepared = {
            "api_key": settings.QWEN3_VL_API_KEY,
            "base_url": settings.QWEN3_VL_BASE_URL or DEFAULT_QWEN_VL_BASE_URL,
            "model_name": settings.QWEN3_VL_MODEL_NAME or DEFAULT_QWEN_VL_MODEL,
        }
        for key, value in super().prepare_configuration(config).items():
            if value is None:
                continue
            if isinstance(value, str) and not value.strip():
                continue
            prepared[key] = value
        prepared["base_url"] = str(
            prepared.get("base_url") or DEFAULT_QWEN_VL_BASE_URL
        ).strip()
        prepared["model_name"] = str(
            prepared.get("model_name") or DEFAULT_QWEN_VL_MODEL
        ).strip()
        api_key = prepared.get("api_key")
        prepared["api_key"] = api_key.strip() if isinstance(api_key, str) else api_key
        return prepared

    async def on_config_updated(self, config: dict[str, Any] | None) -> None:
        self._config = dict(config or {})
        if self._loaded:
            await self.unload()

    async def load(self) -> bool:
        try:
            missing_fields = self.get_missing_required_fields(self._config)
            if missing_fields:
                logger.warning(
                    "Qwen3-VL is missing required configuration: {}",
                    ", ".join(missing_fields),
                )
                self._loaded = False
                return False

            self._loaded = True
            return True
        except Exception as exc:
            logger.error(f"Failed to initialize Qwen3-VL analyzer: {exc}")
            self._loaded = False
            return False

    async def unload(self) -> bool:
        self._loaded = False
        return True

    def is_loaded(self) -> bool:
        return self._loaded

    def _local_image_to_data_url(self, image_path: str) -> str:
        path = Path(image_path)
        if not path.is_file():
            raise FileNotFoundError(f"Image not found: {path}")

        mime_type, _ = mimetypes.guess_type(path.name)
        mime_type = mime_type or "application/octet-stream"
        encoded = base64.b64encode(path.read_bytes()).decode("utf-8")
        return f"data:{mime_type};base64,{encoded}"

    def _extract_json(self, content: Any) -> dict[str, Any] | None:
        if isinstance(content, list):
            content = "".join(
                part.get("text", "") if isinstance(part, dict) else str(part)
                for part in content
            )

        text = str(content).strip()
        if not text:
            return None

        if text.startswith("```"):
            lines = text.splitlines()
            if len(lines) >= 3 and lines[0].startswith("```") and lines[-1].startswith("```"):
                text = "\n".join(lines[1:-1]).strip()
                if text.lower().startswith("json"):
                    text = text[4:].strip()

        try:
            parsed = json.loads(text)
            return parsed if isinstance(parsed, dict) else {"value": parsed}
        except json.JSONDecodeError:
            start = text.find("{")
            end = text.rfind("}")
            if start == -1 or end == -1 or end <= start:
                return None
            try:
                parsed = json.loads(text[start : end + 1])
                return parsed if isinstance(parsed, dict) else {"value": parsed}
            except json.JSONDecodeError:
                return None

    def _extract_score(self, payload: dict[str, Any] | None) -> float | None:
        if not isinstance(payload, dict):
            return None

        for key in ("score", "overall_score", "rating"):
            value = payload.get(key)
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                return float(value)
            if isinstance(value, str):
                try:
                    return float(value.strip())
                except ValueError:
                    continue

        nested = payload.get("result")
        if isinstance(nested, dict):
            return self._extract_score(nested)

        return None

    def _render_prompt_template(
        self,
        template: str,
        variables: dict[str, str],
    ) -> str:
        rendered = template
        for key, value in variables.items():
            rendered = re.sub(
                rf"{{{{\s*{re.escape(key)}\s*}}}}",
                value,
                rendered,
            )
        return rendered

    def _build_prompt_variables(
        self,
        image_path: str,
        config: dict[str, Any],
    ) -> dict[str, str]:
        path = Path(image_path)
        mime_type, _ = mimetypes.guess_type(path.name)
        return {
            "image_name": path.name,
            "mime_type": mime_type or "application/octet-stream",
            "model_name": str(config["model_name"]),
        }

    async def _load_prompt_bundle(self) -> ActivePromptVersion:
        try:
            async with async_session_maker() as session:
                active_prompt = await get_active_prompt_version(session, self.name)
                if active_prompt is not None:
                    return active_prompt
        except Exception as exc:
            logger.warning(f"Failed to load prompt bundle for {self.name}: {exc}")

        return ActivePromptVersion(
            prompt_id="builtin-qwen3-vl-prompt",
            prompt_name="Built-in fallback prompt",
            prompt_description="Fallback prompt when database prompt state is unavailable",
            prompt_version_id="builtin-qwen3-vl-prompt-v1",
            prompt_version_number=1,
            system_prompt=DEFAULT_QWEN_SYSTEM_PROMPT,
            user_prompt=DEFAULT_QWEN_USER_PROMPT,
        )

    def _serialize_usage(self, response: Any) -> dict[str, Any] | None:
        usage = getattr(response, "usage", None)
        if usage is None:
            return None

        if hasattr(usage, "model_dump"):
            dumped = usage.model_dump()
            return dumped if isinstance(dumped, dict) else None

        if isinstance(usage, dict):
            return usage

        return None

    def _sync_analyze(
        self,
        image_path: str,
        prompt_bundle: ActivePromptVersion,
    ) -> dict[str, Any]:
        from openai import OpenAI

        config = self.prepare_configuration(self._config)
        image_url = self._local_image_to_data_url(image_path)
        variables = self._build_prompt_variables(image_path, config)
        system_prompt = prompt_bundle.system_prompt
        user_prompt = self._render_prompt_template(prompt_bundle.user_prompt, variables)
        prompt_metadata = {
            "prompt_id": prompt_bundle.prompt_id,
            "prompt_name": prompt_bundle.prompt_name,
            "prompt_version_id": prompt_bundle.prompt_version_id,
            "prompt_version_number": prompt_bundle.prompt_version_number,
        }

        client = OpenAI(
            api_key=str(config["api_key"]),
            base_url=str(config["base_url"]),
        )
        response = client.chat.completions.create(
            model=str(config["model_name"]),
            temperature=0.0,
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_prompt},
                        {"type": "image_url", "image_url": {"url": image_url}},
                    ],
                },
            ],
        )

        content = response.choices[0].message.content or ""
        parsed_result = self._extract_json(content)
        usage = self._serialize_usage(response)
        model_name = getattr(response, "model", str(config["model_name"]))

        result: dict[str, Any] = parsed_result or {"raw_text": str(content).strip()}
        result.setdefault("model", model_name)
        result["prompt"] = prompt_metadata
        if usage is not None:
            result["usage"] = usage

        return {
            "score": self._extract_score(result),
            "result": result,
            "raw_text": str(content).strip(),
            "model_name": model_name,
            "usage": usage,
            "prompt": prompt_metadata,
        }

    async def analyze(self, image_path: str) -> dict[str, Any]:
        if not self._loaded:
            raise RuntimeError("Model not loaded. Call load() first.")

        try:
            prompt_bundle = await self._load_prompt_bundle()
            return await asyncio.to_thread(self._sync_analyze, image_path, prompt_bundle)
        except ImportError as exc:
            raise RuntimeError(
                "The 'openai' package is required for Qwen3-VL analysis."
            ) from exc
