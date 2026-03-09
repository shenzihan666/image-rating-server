# Qwen3-VL Prompt Management

## Overview

This feature adds a complete prompt lifecycle for `qwen3-vl`:

- Prompt metadata management
- Immutable prompt versions
- Version history and diff
- Runtime active-version resolution
- Result-to-prompt traceability

## Functional Design

### Prompt Metadata

Prompt metadata remains editable without mutating version history:

- `name`
- `description`
- `is_active`

This keeps operational metadata separate from versioned prompt content.

### Prompt Versioning

Each prompt content save creates a new version containing:

- `system_prompt`
- `user_prompt`
- `commit_message`

Design rules:

- Versions are immutable
- History remains inspectable
- Any historical version can be loaded into the editor as the next save baseline

### Version Comparison

The frontend supports selecting two versions and opening a diff view. This avoids
introducing a dedicated backend compare API while still supporting review workflows.

### Active Prompt Resolution

At runtime, the Qwen3-VL analyzer:

1. Resolves the active prompt
2. Fetches the current version payload
3. Injects `system_prompt` and `user_prompt` into the model request
4. Renders template variables in `user_prompt`

Supported variables currently include:

- `{{image_name}}`
- `{{mime_type}}`
- `{{model_name}}`

### Fallback Strategy

The system avoids runtime breakage by falling back safely:

- A default Qwen3-VL prompt is seeded if no prompt exists
- A built-in fallback prompt is used if prompt resolution fails at runtime

## Backend Changes

### Data Model

New tables:

- `ai_prompts`
- `ai_prompt_versions`

Extended table:

- `analysis_results`

### API Surface

The prompt API includes:

- `GET /api/v1/ai/prompts?model_name=qwen3-vl`
- `POST /api/v1/ai/prompts`
- `GET /api/v1/ai/prompts/{prompt_id}`
- `PATCH /api/v1/ai/prompts/{prompt_id}`
- `DELETE /api/v1/ai/prompts/{prompt_id}`
- `GET /api/v1/ai/prompts/{prompt_id}/versions`
- `POST /api/v1/ai/prompts/{prompt_id}/versions`
- `GET /api/v1/ai/prompts/{prompt_id}/versions/{version_id}`

### Output Contract

The default prompt guides the model toward JSON output with common keys such as:

- `score`
- `summary`
- `strengths`
- `weaknesses`
- `tags`

That reduces frontend branching and improves downstream readability.

## Frontend Changes

New pages were added for:

- Prompt listing
- Prompt creation
- Prompt detail and version editing
- Version comparison

Supported user actions include:

- Browse prompts
- Create prompts
- Save new versions
- Load historical versions into the editor
- Compare versions
- Edit metadata
- Switch the active prompt

## Configuration

Qwen3-VL uses the following runtime settings:

- `QWEN3_VL_API_KEY`
- `QWEN3_VL_BASE_URL`
- `QWEN3_VL_MODEL_NAME`

Notes:

- API keys are not returned to the browser
- `.env` is a fallback source, not the primary persisted source
- Persisted database config takes precedence over `.env`

## Validation

Validated outcomes include:

- Default prompt seeding
- Initial version creation on prompt creation
- Version number increment on save
- Runtime use of the active database-backed prompt
- Prompt metadata persistence on analysis results
- Frontend prompt management workflows
- Qwen3-VL result rendering in the image detail page

## Known Limitations

- Only `qwen3-vl` is supported
- Template rendering is intentionally lightweight
- There is no prompt evaluation workflow yet
- There is no concurrent editing conflict handling yet

## Recommended Next Steps

1. Add draft and publish states for prompt changes
2. Add a prompt test console for single-image validation
3. Add prompt version rollback
4. Add schema validation for structured model output
5. Record model configuration snapshots alongside prompt versions for deeper auditability
