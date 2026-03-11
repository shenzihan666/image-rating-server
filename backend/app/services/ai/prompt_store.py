"""
Persistence helpers for versioned AI prompts.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import Select, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_prompt import AIPrompt, AIPromptVersion

QWEN3_VL_PROMPT_NAME = "Default Image Analysis Prompt"
LEGACY_DEFAULT_QWEN_SYSTEM_PROMPT = (
    "You are a professional image analysis assistant. "
    "Always return valid JSON only, with no markdown fences or extra commentary."
)
LEGACY_DEFAULT_QWEN_USER_PROMPT = (
    "Analyze the provided image carefully.\n"
    "Use this context when helpful:\n"
    "- image_name: {{image_name}}\n"
    "- mime_type: {{mime_type}}\n"
    "- model_name: {{model_name}}\n\n"
    "Return a JSON object with these keys when they can be inferred:\n"
    "- score: numeric overall score\n"
    "- summary: concise summary\n"
    "- strengths: array of strings\n"
    "- weaknesses: array of strings\n"
    "- tags: array of strings"
)
DEFAULT_QWEN_SYSTEM_PROMPT = """你是一名娱乐直播平台的主播资料照片审核专家。

## 你的任务
判断这张照片是否适合作为娱乐主播的资料展示图，并打分。
你必须给出明确的"合格"或"不合格"结论，不允许"存疑"。

## 严格规则
1. 仅根据图片可见信息判断，禁止推断年龄、种族等敏感属性
2. 输出合法 JSON，不加 Markdown 标记

## 前置检查：人像判断
首先判断照片中是否有清晰可辨的人物正脸或半身像。
- 如果不是人像照片（风景、物品、动物、纯文字等）→ 直接判定"不合格"，final_score=1.0

## 核心判断逻辑
问自己一个问题：如果我是直播平台用户，看到这张资料图，我会想点进去看吗？
- 让人想点击 → 合格
- 没有点击欲望 → 不合格

## 评分维度（每项1-10分）

### anchor_appeal（主播吸引力）— 权重55%
最核心维度。这个人在照片中的整体展示效果能否吸引观众。

| 分数 | 含义 | 典型表现 |
|------|------|---------|
| 9-10 | 极具吸引力 | 专业级：妆发精致、表情有感染力、构图完美、让人忍不住想点击 |
| 7-8  | 有吸引力 | 整体不错：五官清晰、有镜头感、看着舒服、有想了解的欲望 |
| 5-6  | 一般 | 就是个正常人的普通照片，不会特别想点进去看 |
| 3-4  | 缺乏吸引力 | 角度差/遮挡多/表情僵硬/毫无展示意识 |
| 1-2  | 完全无吸引力 | 无法辨认/严重不适合 |

关键：普通好看但没有"展示感"的照片 = 5-6分，不要因为颜值高就给7+
重要区分：
- 好看的社交/旅行/生活随拍 → anchor_appeal 最多6分（好看≠有展示感）
- 有意识地面对镜头展示自己 → 可给7+

### show_readiness（直播准备度）— 权重30%
这张照片是否像是"准备好要做主播"的人拍的。

| 分数 | 含义 | 典型表现 |
|------|------|---------|
| 9-10 | 完全就绪 | 专业造型+专业拍摄，一看就是要做主播/网红的人 |
| 7-8  | 基本就绪 | 造型整洁、有搭配意识、照片有准备感 |
| 5-6  | 准备不足 | 日常穿着状态，没有为"展示"做特别准备；或在居家环境但穿着整洁有妆发 |
| 3-4  | 明显没准备 | 随手拍/衣着随意/邋遢/睡衣状态 |
| 1-2  | 完全没准备 | 完全不当的着装或状态 |

关键陷阱：
- 证件照/工装照虽然穿着正式，但不像"准备做主播"→ 给4-5分
- 精心打扮的自拍虽然好看，但如果明显是社交场景而非展示 → 给5-6分
- 居家环境但人物妆发整洁、有镜头意识 → 给5分（不要因为背景是家里就压到3-4）
- 居家且衣着邋遢、无展示意识 → 给3分

### image_standard（画面达标度）— 权重15%
纯粹评估照片技术层面是否达到基本门槛。

| 分数 | 含义 |
|------|------|
| 8-10 | 清晰明亮，无技术问题 |
| 6-7  | 基本清晰，小瑕疵不影响观看 |
| 4-5  | 有明显技术问题但能看 |
| 1-3  | 严重技术问题，模糊/过暗/过曝 |

## 硬伤扣分（从加权总分中直接扣减）
- 面部被遮挡超30%（手/头发/物品）→ -2.0
- 聊天截图/拼图/带边框水印 → -2.0
- 过度美颜导致五官变形 → -1.5
- 穿着严重不当 → -2.0
- 背景极度脏乱（注意：普通居家环境不算脏乱）→ -1.0
- 证件照/正装工装照风格 → -0.5

## 输出格式
{
  "is_portrait": true,
  "decision": "合格 或 不合格",
  "decision_reason": "一句话理由，20字内",
  "scores": {
    "anchor_appeal": {"score": 0, "reason": "20字内"},
    "show_readiness": {"score": 0, "reason": "20字内"},
    "image_standard": {"score": 0, "reason": "20字内"}
  },
  "penalties": ["命中的硬伤"],
  "penalty_total": 0,
  "final_score": 0
}

## 计算规则
weighted = anchor_appeal × 0.55 + show_readiness × 0.30 + image_standard × 0.15
final_score = max(1.0, round(weighted - penalty_total, 1))

## 决策规则（必须严格遵守）
- final_score ≥ 6.0 → "合格"
- final_score < 6.0 → "不合格"
- 不允许输出"存疑"，必须二选一
"""
DEFAULT_QWEN_USER_PROMPT = """请审核这张主播候选人照片。

打分要点：
1. 先判断是否为人像照片，非人像直接不合格
2. 先问自己：看到这张图你会想点击了解这个主播吗？想→倾向合格，不想→倾向不合格
3. 普通自拍/生活照/证件照，无论人多好看，anchor_appeal不应超过6分
4. 只有真正有"展示感"、"让人想看"的照片才配7+
5. 居家环境不等于不合格，关键看人的妆发和状态，而不是背景
6. 硬伤必扣，不能手软
7. 必须做出合格/不合格的明确判断，不要存疑

严格按JSON格式输出。"""


@dataclass(frozen=True)
class ActivePromptVersion:
    """Resolved prompt version payload used by runtime analyzers."""

    prompt_id: str
    prompt_name: str
    prompt_description: str | None
    prompt_version_id: str
    prompt_version_number: int
    system_prompt: str
    user_prompt: str


def _isoformat(value: datetime | None) -> str:
    if value is None:
        return ""
    return value.isoformat()


def _serialize_version(version: AIPromptVersion) -> dict[str, Any]:
    return {
        "id": version.id,
        "prompt_id": version.prompt_id,
        "version_number": version.version_number,
        "system_prompt": version.system_prompt,
        "user_prompt": version.user_prompt,
        "commit_message": version.commit_message,
        "created_by": version.created_by,
        "created_at": _isoformat(version.created_at),
    }


def _serialize_prompt(
    prompt: AIPrompt,
    current_version: AIPromptVersion | None,
) -> dict[str, Any]:
    return {
        "id": prompt.id,
        "model_name": prompt.model_name,
        "name": prompt.name,
        "description": prompt.description,
        "is_active": prompt.is_active,
        "current_version_id": current_version.id if current_version else prompt.current_version_id,
        "current_version_number": current_version.version_number if current_version else None,
        "created_at": _isoformat(prompt.created_at),
        "updated_at": _isoformat(prompt.updated_at),
        "current_version": _serialize_version(current_version) if current_version else None,
    }


async def _get_current_version(
    db: AsyncSession,
    prompt: AIPrompt,
) -> AIPromptVersion | None:
    if prompt.current_version_id:
        result = await db.execute(
            select(AIPromptVersion).where(AIPromptVersion.id == prompt.current_version_id)
        )
        version = result.scalar_one_or_none()
        if version is not None:
            return version

    result = await db.execute(
        select(AIPromptVersion)
        .where(AIPromptVersion.prompt_id == prompt.id)
        .order_by(AIPromptVersion.version_number.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _deactivate_other_prompts(
    db: AsyncSession,
    model_name: str,
    active_prompt_id: str,
) -> None:
    await db.execute(
        update(AIPrompt)
        .where(
            AIPrompt.model_name == model_name,
            AIPrompt.id != active_prompt_id,
            AIPrompt.is_active.is_(True),
        )
        .values(is_active=False)
    )


async def ensure_default_prompts(db: AsyncSession) -> None:
    """Seed default prompt records required by the runtime."""
    existing = await get_active_prompt_version(db, "qwen3-vl")
    if existing is not None:
        if (
            existing.prompt_name == QWEN3_VL_PROMPT_NAME
            and existing.prompt_version_number == 1
            and existing.system_prompt.strip() == LEGACY_DEFAULT_QWEN_SYSTEM_PROMPT
            and existing.user_prompt.strip() == LEGACY_DEFAULT_QWEN_USER_PROMPT
        ):
            result = await db.execute(
                select(AIPromptVersion).where(AIPromptVersion.id == existing.prompt_version_id)
            )
            version = result.scalar_one_or_none()
            if version is not None:
                version.system_prompt = DEFAULT_QWEN_SYSTEM_PROMPT
                version.user_prompt = DEFAULT_QWEN_USER_PROMPT
                version.commit_message = "Initial default prompt (v5_01_gentle_fix baseline)"
                await db.commit()
        return

    prompt_result = await db.execute(
        select(AIPrompt)
        .where(AIPrompt.model_name == "qwen3-vl")
        .order_by(AIPrompt.created_at.asc())
        .limit(1)
    )
    prompt = prompt_result.scalar_one_or_none()
    if prompt is None:
        created = await create_prompt(
            db,
            model_name="qwen3-vl",
            name=QWEN3_VL_PROMPT_NAME,
            description="Default managed prompt for Qwen3-VL image analysis",
            system_prompt=DEFAULT_QWEN_SYSTEM_PROMPT,
            user_prompt=DEFAULT_QWEN_USER_PROMPT,
            commit_message="Initial default prompt (v5_01_gentle_fix baseline)",
            created_by="system",
            is_active=True,
        )
        if created is not None:
            return

    if prompt is None:
        return

    versions = await list_prompt_versions(db, prompt.id)
    if not versions:
        await create_prompt_version(
            db,
            prompt.id,
            system_prompt=DEFAULT_QWEN_SYSTEM_PROMPT,
            user_prompt=DEFAULT_QWEN_USER_PROMPT,
            commit_message="Initial default prompt (v5_01_gentle_fix baseline)",
            created_by="system",
        )
        prompt.is_active = True
        await db.commit()
        await db.refresh(prompt)

    if not prompt.is_active:
        prompt.is_active = True
        await db.commit()
        await db.refresh(prompt)
    await _deactivate_other_prompts(db, prompt.model_name, prompt.id)
    await db.commit()


async def list_prompts(
    db: AsyncSession,
    model_name: str | None = None,
) -> list[dict[str, Any]]:
    """List prompts for a model."""
    stmt: Select[tuple[AIPrompt]] = select(AIPrompt).order_by(
        AIPrompt.updated_at.desc(),
        AIPrompt.created_at.desc(),
    )
    if model_name:
        stmt = stmt.where(AIPrompt.model_name == model_name)

    result = await db.execute(stmt)
    prompts = result.scalars().all()
    payloads: list[dict[str, Any]] = []
    for prompt in prompts:
        current_version = await _get_current_version(db, prompt)
        payloads.append(_serialize_prompt(prompt, current_version))
    return payloads


async def get_prompt(
    db: AsyncSession,
    prompt_id: str,
) -> dict[str, Any] | None:
    """Fetch a prompt and its current version."""
    result = await db.execute(select(AIPrompt).where(AIPrompt.id == prompt_id))
    prompt = result.scalar_one_or_none()
    if prompt is None:
        return None

    current_version = await _get_current_version(db, prompt)
    return _serialize_prompt(prompt, current_version)


async def create_prompt(
    db: AsyncSession,
    *,
    model_name: str,
    name: str,
    description: str | None,
    system_prompt: str,
    user_prompt: str,
    commit_message: str | None,
    created_by: str | None,
    is_active: bool,
) -> dict[str, Any] | None:
    """Create a prompt and its initial version."""
    prompt = AIPrompt(
        model_name=model_name,
        name=name.strip(),
        description=description.strip() if isinstance(description, str) and description.strip() else None,
        is_active=is_active,
    )
    db.add(prompt)
    await db.flush()

    version = AIPromptVersion(
        prompt_id=prompt.id,
        version_number=1,
        system_prompt=system_prompt.strip(),
        user_prompt=user_prompt.strip(),
        commit_message=commit_message.strip() if isinstance(commit_message, str) and commit_message.strip() else None,
        created_by=created_by.strip() if isinstance(created_by, str) and created_by.strip() else None,
    )
    db.add(version)
    await db.flush()

    prompt.current_version_id = version.id
    if prompt.is_active:
        await _deactivate_other_prompts(db, prompt.model_name, prompt.id)

    await db.commit()
    await db.refresh(prompt)
    await db.refresh(version)
    return _serialize_prompt(prompt, version)


async def update_prompt(
    db: AsyncSession,
    prompt_id: str,
    updates: dict[str, Any],
) -> dict[str, Any] | None:
    """Update prompt metadata."""
    result = await db.execute(select(AIPrompt).where(AIPrompt.id == prompt_id))
    prompt = result.scalar_one_or_none()
    if prompt is None:
        return None

    if "name" in updates and updates["name"] is not None:
        prompt.name = str(updates["name"]).strip()

    if "description" in updates:
        description = updates["description"]
        prompt.description = (
            str(description).strip()
            if isinstance(description, str) and description.strip()
            else None
        )

    if "is_active" in updates and updates["is_active"] is not None:
        prompt.is_active = bool(updates["is_active"])
        if prompt.is_active:
            await _deactivate_other_prompts(db, prompt.model_name, prompt.id)

    await db.commit()
    await db.refresh(prompt)
    current_version = await _get_current_version(db, prompt)
    return _serialize_prompt(prompt, current_version)


async def delete_prompt(db: AsyncSession, prompt_id: str) -> bool:
    """Delete a prompt and keep one prompt active when possible."""
    result = await db.execute(select(AIPrompt).where(AIPrompt.id == prompt_id))
    prompt = result.scalar_one_or_none()
    if prompt is None:
        return False

    model_name = prompt.model_name
    was_active = prompt.is_active
    await db.delete(prompt)
    await db.commit()

    if was_active:
        replacement_result = await db.execute(
            select(AIPrompt)
            .where(AIPrompt.model_name == model_name)
            .order_by(AIPrompt.updated_at.desc(), AIPrompt.created_at.desc())
            .limit(1)
        )
        replacement = replacement_result.scalar_one_or_none()
        if replacement is not None:
            replacement.is_active = True
            await _deactivate_other_prompts(db, replacement.model_name, replacement.id)
            await db.commit()
        elif model_name == "qwen3-vl":
            await ensure_default_prompts(db)

    return True


async def list_prompt_versions(
    db: AsyncSession,
    prompt_id: str,
) -> list[dict[str, Any]]:
    """List versions for a prompt."""
    result = await db.execute(
        select(AIPromptVersion)
        .where(AIPromptVersion.prompt_id == prompt_id)
        .order_by(AIPromptVersion.version_number.desc())
    )
    return [_serialize_version(version) for version in result.scalars().all()]


async def get_prompt_version(
    db: AsyncSession,
    prompt_id: str,
    version_id: str,
) -> dict[str, Any] | None:
    """Fetch a specific version."""
    result = await db.execute(
        select(AIPromptVersion).where(
            AIPromptVersion.prompt_id == prompt_id,
            AIPromptVersion.id == version_id,
        )
    )
    version = result.scalar_one_or_none()
    if version is None:
        return None
    return _serialize_version(version)


async def create_prompt_version(
    db: AsyncSession,
    prompt_id: str,
    *,
    system_prompt: str,
    user_prompt: str,
    commit_message: str | None,
    created_by: str | None,
) -> dict[str, Any] | None:
    """Create a new version and mark it current."""
    result = await db.execute(select(AIPrompt).where(AIPrompt.id == prompt_id))
    prompt = result.scalar_one_or_none()
    if prompt is None:
        return None

    version_count_result = await db.execute(
        select(func.max(AIPromptVersion.version_number)).where(
            AIPromptVersion.prompt_id == prompt_id
        )
    )
    next_version = (version_count_result.scalar_one_or_none() or 0) + 1
    version = AIPromptVersion(
        prompt_id=prompt_id,
        version_number=next_version,
        system_prompt=system_prompt.strip(),
        user_prompt=user_prompt.strip(),
        commit_message=commit_message.strip() if isinstance(commit_message, str) and commit_message.strip() else None,
        created_by=created_by.strip() if isinstance(created_by, str) and created_by.strip() else None,
    )
    db.add(version)
    await db.flush()

    prompt.current_version_id = version.id
    await db.commit()
    await db.refresh(version)
    return _serialize_version(version)


async def get_active_prompt_version(
    db: AsyncSession,
    model_name: str,
) -> ActivePromptVersion | None:
    """Resolve the active prompt version for a model."""
    result = await db.execute(
        select(AIPrompt)
        .where(AIPrompt.model_name == model_name, AIPrompt.is_active.is_(True))
        .order_by(AIPrompt.updated_at.desc(), AIPrompt.created_at.desc())
        .limit(1)
    )
    prompt = result.scalar_one_or_none()
    if prompt is None:
        return None

    current_version = await _get_current_version(db, prompt)
    if current_version is None:
        return None

    return ActivePromptVersion(
        prompt_id=prompt.id,
        prompt_name=prompt.name,
        prompt_description=prompt.description,
        prompt_version_id=current_version.id,
        prompt_version_number=current_version.version_number,
        system_prompt=current_version.system_prompt,
        user_prompt=current_version.user_prompt,
    )
