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
- `app/api/deps.py` - Dependency injection (auth, database sessions)
- `app/core/` - Configuration, security (JWT), database, logging
- `app/models/` - SQLAlchemy ORM models (User, Image, Rating, AIModel)
- `app/schemas/` - Pydantic request/response schemas
- `app/services/` - Business logic layer
  - `services/auth.py` - Authentication service
  - `services/storage.py` - File storage with atomic write and hash computation
  - `services/image_upload.py` - Image upload validation and deduplication
  - `services/concurrent_upload.py` - Concurrent upload control (max 3 parallel)
  - `services/ai/` - AI model registry and analyzers
    - `registry.py` - Model registration and active model management
    - `store.py` - Database persistence for model state
    - `models/nima/` - NIMA implementation for image quality scoring

### Frontend Structure
- `src/app/` - Next.js App Router pages
  - `(auth)/` - Public auth pages (login)
  - `dashboard/` - Protected dashboard pages with sidebar layout
- `src/components/ui/` - shadcn/ui components
- `src/lib/api.ts` - Axios API client with auth interceptors
- `src/lib/auth.ts` - Token management utilities
- `src/store/auth-store.ts` - Zustand auth state (persisted)

### API Endpoints
- `/api/v1/auth/*` - Authentication (login, register, refresh, logout)
- `/api/v1/users/*` - User management
- `/api/v1/upload` - Image upload with hash verification and deduplication
- `/api/v1/ai/models/*` - AI model management (list, activate, deactivate)

### Key Patterns

**Dependency Injection**: Use `CurrentUser`, `ActiveUser`, `OptionalUser` type aliases from `app/api/deps.py` for auth. Use `Annotated[AsyncSession, Depends(get_db)]` for database sessions.

**AI Model Registry**: Only one AI model can be active at a time. Models implement `BaseAIAnalyzer` interface with `load()`, `unload()`, `is_loaded()`, and `analyze()` methods. State is persisted to database via `store.py`.

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
