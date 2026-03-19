# API Overview

## Base Paths

- API root: `/api/v1`
- OpenAPI UI: `/docs`

The FastAPI app in this repository exposes the routes below without a built-in
user table or `/users` API. Add gateway or middleware auth if you need protection.

## Images

Routes under `/api/v1/images`:

- `GET /`
  - Paginated list with `page`, `page_size`, `search`, `date_from`, `date_to`
- `GET /{image_id}`
- `PATCH /{image_id}`
- `DELETE /{image_id}`
- `POST /batch/delete`

Image list responses include latest AI score metadata when available.

## Upload

Route under `/api/v1/upload`:

- `POST /`
  - Multi-file upload with optional `hashes` JSON payload for deduplication

Operational notes:

- Max files per request is controlled by backend settings
- Upload processing uses concurrent workers with isolated database sessions

## AI Models

Routes under `/api/v1/ai/models`:

- `GET /models`
- `GET /models/active`
- `POST /models/active`
- `DELETE /models/active`
- `GET /models/{model_name}`
- `PUT /models/{model_name}/config`

Only one model can be active at runtime.

## AI Analysis

Routes under `/api/v1/ai/analyze`:

- `POST /analyze/{image_id}`
- `POST /analyze/batch`

Behavior notes:

- Single-image analysis reuses the latest cached result unless `force_new=true`
- Batch analysis requires an active model
- Saved results retain prompt metadata when the active model is Qwen3-VL

## AI Prompts

Routes under `/api/v1/ai/prompts`:

- `GET /prompts`
- `POST /prompts`
- `GET /prompts/{prompt_id}`
- `PATCH /prompts/{prompt_id}`
- `DELETE /prompts/{prompt_id}`
- `GET /prompts/{prompt_id}/versions`
- `POST /prompts/{prompt_id}/versions`
- `GET /prompts/{prompt_id}/versions/{version_id}`

These routes are currently used for Qwen3-VL prompt lifecycle management.

## Frontend Integration Notes

- The frontend API client lives in `frontend/src/lib/api.ts`
- NextAuth injects backend access tokens into API requests
- The frontend uses typed helper groups for auth, users, images, upload, AI
  analyze, and AI prompt flows
