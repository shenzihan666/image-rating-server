# System Overview

## Scope

This document describes the stable repository structure and the main runtime
patterns used across the backend and frontend.

## High-Level Shape

The system is split into two applications:

- `backend/`
  - FastAPI API, database models, service layer, and AI integrations
- `frontend/`
  - Next.js dashboard, authentication UI, and model-management screens

The frontend talks to the backend over `/api/v1`. AI analysis results are stored
in the database so the UI can reuse the latest result instead of triggering a new
model run on every page load.

## Backend Structure

### Entry and Core

- `backend/app/main.py`
  - FastAPI application setup and lifespan bootstrapping
- `backend/app/core/config.py`
  - Environment-backed settings and runtime defaults
- `backend/app/core/database.py`
  - Async engine, sessions, and schema initialization
- `backend/app/core/security.py`
  - JWT helpers and password hashing

### HTTP Layer

- `backend/app/api/v1/router.py`
  - Aggregates all API v1 routers
- `backend/app/api/deps.py`
  - Shared auth and database dependencies
- `backend/app/api/v1/endpoints/`
  - Endpoint modules for auth, users, images, upload, AI analyze, and AI prompts

### Domain and Service Layer

- `backend/app/models/`
  - SQLAlchemy ORM models such as `User`, `Image`, `Rating`, `AIModel`, and
    `AnalysisResult`
- `backend/app/schemas/`
  - Pydantic request and response schemas
- `backend/app/services/`
  - Business logic for auth, image management, upload, result persistence, and
    concurrent processing
- `backend/app/services/ai/`
  - Model registry, prompt store, runtime configuration store, and analyzer
    implementations

## Frontend Structure

### App Router Surfaces

- `frontend/src/app/(auth)/`
  - Public authentication routes
- `frontend/src/app/dashboard/`
  - Protected dashboard shell and feature pages
- `frontend/src/app/dashboard/images/`
  - Gallery page and image detail route
- `frontend/src/app/dashboard/ai-analyze/`
  - Model management and Qwen3-VL prompt pages

### Shared Frontend Modules

- `frontend/src/lib/api.ts`
  - Axios client, typed API helpers, and auth-aware request handling
- `frontend/src/lib/auth.config.ts`
  - NextAuth credential provider and token refresh behavior
- `frontend/src/components/ui/`
  - Shared UI primitives
- `frontend/src/components/layout/`
  - Shared layout components

## Cross-Cutting Runtime Patterns

### Dependency Injection

Use the aliases from `backend/app/api/deps.py` in endpoints:

- `CurrentUser`
- `ActiveUser`
- `OptionalUser`

Database access in endpoints should continue to come from
`Annotated[AsyncSession, Depends(get_db)]`.

### Service-First Business Logic

Endpoints should remain thin. Validation, database workflows, and orchestration
belong in `backend/app/services/`, not inside route handlers.

### AI Model Registry

Only one AI model can be active at a time. Runtime activation is coordinated
through `backend/app/services/ai/registry.py`, while persisted configuration lives
in the store layer.

### Cached Analysis Results

`AnalysisResultService` persists model output. Single-image analysis first checks
for the latest cached result unless `force_new=true` is requested.

### Concurrency Limits

Batch upload and batch analysis use dedicated concurrent services. Each concurrent
task creates its own database session and uses a semaphore limit to avoid race
conditions and uncontrolled resource usage.

### Authentication Flow

The backend issues JWT access and refresh tokens. The frontend uses NextAuth
credentials flow to acquire, refresh, and inject those tokens into API requests.

## Data Model Snapshot

- `User`
  - Account identity and profile data
- `Image`
  - Uploaded file metadata and ownership
- `Rating`
  - Rating-related persistence for image scoring workflows
- `AIModel`
  - Stored model configuration and activation state
- `AnalysisResult`
  - Persistent AI output, scores, and Qwen prompt metadata

For feature-specific flow details, see:

- [API Overview](../api/api-overview.md)
- [Qwen3-VL Prompt Management Architecture](./qwen3-vl-prompt-management.md)
