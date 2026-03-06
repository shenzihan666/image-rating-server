# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Full-stack image rating application with AI-powered image quality analysis (NIMA - Neural Image Assessment).

**Backend**: FastAPI + SQLAlchemy (async) + SQLite
**Frontend**: Next.js 15 (App Router) + TypeScript + Tailwind CSS + shadcn/ui + Zustand

## Commands

### Backend (from `backend/` directory)
```bash
uv sync                           # Install dependencies
uv run uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload  # Dev server
uv run pytest                     # Run tests
uv run black .                    # Format code
uv run ruff check .               # Lint
uv run mypy app                   # Type check
```

### Frontend (from `frontend/` directory)
```bash
npm install                       # Install dependencies
npm run dev                       # Dev server (port 8081)
npm run build                     # Production build
npm run lint                      # ESLint
npm run type-check                # TypeScript check
npm run test                      # Playwright E2E tests
```

### Combined Dev Startup
```bash
# Windows
scripts\dev.bat

# Linux/Mac
./scripts/dev.sh
```

## Architecture

### Backend Structure
- `app/main.py` - FastAPI app factory with lifespan management
- `app/api/v1/router.py` - API route aggregation
- `app/api/v1/endpoints/` - API endpoint modules
  - `auth.py` - Authentication endpoints
  - `images.py` - Image CRUD, batch delete, date filtering
  - `ai_analyze.py` - Single/batch analysis, model management
  - `upload.py` - Image upload with hash verification
- `app/api/deps.py` - Dependency injection (auth, database sessions)
- `app/core/` - Configuration, security (JWT), database, logging
- `app/models/` - SQLAlchemy ORM models
  - `User` - User accounts
  - `Image` - Image metadata and ratings
  - `Rating` - User ratings for images
  - `AIModel` - AI model state
  - `AnalysisResult` - AI analysis results (persistent)
- `app/schemas/` - Pydantic request/response schemas
  - `image.py` - Image schemas with AI score fields
  - `analyze.py` - Analysis request/response
  - `batch.py` - Batch operation schemas
- `app/services/` - Business logic layer
  - `auth.py` - Authentication service
  - `storage.py` - File storage with atomic write and hash computation
  - `image_upload.py` - Image upload validation and deduplication
  - `image.py` - Image service with date filtering
  - `concurrent_upload.py` - Concurrent upload control (max 3 parallel)
  - `concurrent_analyze.py` - Concurrent batch analysis (max 3 parallel)
  - `analysis_result.py` - Analysis result persistence service
  - `ai/` - AI model registry and analyzers
    - `registry.py` - Model registration and active model management
    - `store.py` - Database persistence for model state
    - `models/nima/` - NIMA implementation for image quality scoring

### Frontend Structure
- `src/app/` - Next.js App Router pages
  - `(auth)/` - Public auth pages (login)
  - `dashboard/` - Protected dashboard pages with sidebar layout
    - `dashboard/images/` - Image gallery with batch selection
      - `page.tsx` - Images list with selection mode, batch operations, date filter
      - `[id]/page.tsx` - Individual image detail page
- `src/components/ui/` - shadcn/ui components
- `src/lib/api.ts` - Axios API client with auth interceptors, batch operations
- `src/lib/auth.ts` - Token management utilities
- `src/lib/image-url.ts` - Image URL utility for serving uploads
- `src/store/auth-store.ts` - Zustand auth state (persisted)

### API Endpoints
- `/api/v1/auth/*` - Authentication (login, register, refresh, logout)
- `/api/v1/users/*` - User management
- `/api/v1/images` - Image management
  - `GET /` - List images with pagination, search, and date filtering
  - `GET /{id}` - Get single image
  - `PATCH /{id}` - Update image metadata
  - `DELETE /{id}` - Delete single image
  - `POST /batch/delete` - Batch delete multiple images
- `/api/v1/upload` - Image upload with hash verification and deduplication
- `/api/v1/ai/models/*` - AI model management (list, activate, deactivate)
- `/api/v1/ai/analyze` - AI analysis
  - `POST /{image_id}` - Analyze single image (caches results)
  - `POST /batch` - Batch analyze multiple images

### Key Patterns

**Dependency Injection**: Use `CurrentUser`, `ActiveUser`, `OptionalUser` type aliases from `app/api/deps.py` for auth. Use `Annotated[AsyncSession, Depends(get_db)]` for database sessions.

**AI Model Registry**: Only one AI model can be active at a time. Models implement `BaseAIAnalyzer` interface with `load()`, `unload()`, `is_loaded()`, and `analyze()` methods. State is persisted to database via `store.py`.

**AI Analysis Persistence**: Analysis results are automatically saved to `analysis_results` table. When analyzing an image, check for cached results first (unless `force_new=true`). The `AnalysisResultService` handles saving/retrieving scores.

**Batch Operations**: Use `ConcurrentAnalyzeService` and `ConcurrentUploadService` patterns for parallel processing. Both use `asyncio.Semaphore(max_concurrent=3)` to limit concurrent operations. Each concurrent task creates its own database session to avoid race conditions.

**Auth Flow**: JWT tokens stored in localStorage. Access token in Authorization header. 401 responses trigger automatic redirect to /login.

## Ports
- Backend API: 8080
- Frontend: 8081
- API Docs: http://localhost:8080/docs

## Environment Variables

Backend (`backend/.env`):
- `SECRET_KEY` - JWT signing key (required)
- `DATABASE_URL` - Default: sqlite+aiosqlite:///./app.db
- `FRONTEND_URL` - CORS origin, default: http://localhost:8081

Frontend (`frontend/.env.local`):
- `NEXT_PUBLIC_API_URL` - Backend URL, default: http://localhost:8080

## Data Models

### Image (with AI scores)
The `ImageResponse` schema includes AI analysis fields:
- `ai_score` - Latest analysis score (1-10 for NIMA)
- `ai_model` - Name of model used for analysis
- `ai_analyzed_at` - Timestamp of analysis

These are populated by joining with `analysis_results` table and fetching the latest result per image.

### AnalysisResult
Stores AI analysis results for persistence:
- `id`, `image_id`, `model` - Identifiers
- `score`, `min_score`, `max_score` - Score metrics
- `distribution` - JSON encoded score distribution
- `details` - JSON encoded full analysis details
- `created_at` - Analysis timestamp

## Frontend Patterns

### Selection Mode
The images gallery uses a selection mode pattern:
- Toggle "Select" button to enter selection mode
- In selection mode: checkboxes appear, clicking selects items
- Batch action bar appears with Analyze/Delete buttons
- Exiting selection mode clears selections

### Date Filtering
Images can be filtered by date range using ISO format date strings (`date_from`, `date_to` query params).
