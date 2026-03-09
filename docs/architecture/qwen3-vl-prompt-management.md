# Qwen3-VL Prompt Management Architecture

## Scope

This document focuses on the Qwen3-VL prompt-management and result-rendering
changes. It does not attempt to describe the full system.

## High-Level Flow

Two application flows were extended:

1. Prompt management flow
2. Qwen3-VL analysis execution flow

### Prompt Management Flow

The frontend prompt pages call dedicated prompt APIs. The backend persists prompt
metadata separately from immutable prompt versions.

Key properties:

- Prompt metadata and prompt content are stored separately
- Every prompt content save creates a new immutable version
- Runtime execution resolves the active prompt version
- Analysis results keep the prompt version metadata used at execution time

### Analysis Execution Flow

When an image is analyzed with `qwen3-vl`, the analyzer resolves the active
prompt, renders the prompt template variables, invokes the OpenAI-compatible API,
parses the response, and stores a normalized result payload.

## Core Components

### Backend

- `backend/app/services/ai/prompt_store.py`
  - Prompt CRUD, version creation, active prompt resolution, default seed logic
- `backend/app/services/ai/models/qwen_vl/analyzer.py`
  - Qwen3-VL analyzer, prompt injection, template rendering, response
    normalization
- `backend/app/api/v1/endpoints/ai_prompts.py`
  - Prompt management API surface
- `backend/app/services/analysis_result.py`
  - Result persistence, including prompt metadata tracking
- `backend/app/core/database.py`
  - Schema migrations for prompt tables and analysis result extensions

### Frontend

- `frontend/src/app/dashboard/ai-analyze/qwen3-vl/prompts/*`
  - Prompt list, create, and detail pages
- `frontend/src/app/dashboard/layout.tsx`
  - Dedicated sidebar entry for prompt management
- `frontend/src/app/dashboard/images/[id]/page.tsx`
  - Structured Qwen3-VL result presentation

## Data Model Summary

### `ai_prompts`

Stores prompt metadata:

- `id`
- `model_name`
- `name`
- `description`
- `is_active`
- `current_version_id`
- `created_at`
- `updated_at`

### `ai_prompt_versions`

Stores immutable prompt content versions:

- `id`
- `prompt_id`
- `version_number`
- `system_prompt`
- `user_prompt`
- `commit_message`
- `created_by`
- `created_at`

### `analysis_results` Extensions

Tracks which prompt version produced a result:

- `prompt_version_id`
- `prompt_name`
- `prompt_version_number`

## Configuration Strategy

Qwen3-VL runtime configuration follows this priority order:

1. Persisted database configuration
2. `.env` fallback values
3. Built-in defaults when applicable

This keeps local setup simple while preserving database-stored runtime settings as
the source of truth.

## Constraints

This implementation intentionally stays narrow:

- Only `qwen3-vl` is supported
- Only `system_prompt` and `user_prompt` are managed
- No multi-model prompt platform abstraction yet
- No prompt evaluation, sandbox testing, or rollout workflow yet
