# Development Conventions

## Backend Conventions

- Keep route handlers thin; move business logic into `backend/app/services/`
- Use auth dependency aliases from `backend/app/api/deps.py` instead of manually
  re-declaring token parsing in endpoints
- Prefer repository-local service helpers for database workflows instead of raw
  SQL inside controllers
- When adding concurrent batch work, create independent database sessions inside
  worker tasks rather than sharing one session across coroutines

## AI Integration Conventions

- Treat the AI registry as the runtime source for the active model
- Persist model configuration through the store layer so runtime and database
  state stay aligned
- Save analysis results through `AnalysisResultService` so cache reuse and result
  history remain consistent
- For Qwen3-VL, keep prompt metadata and prompt versions separated

## Frontend Conventions

- Centralize backend calls in `frontend/src/lib/api.ts`
- Use NextAuth session state for backend access-token injection and refresh
- Keep shared UI primitives in `frontend/src/components/ui/`
- Keep dashboard features under route-specific folders in `frontend/src/app/dashboard/`

## UX Patterns Already In Use

- The image gallery supports selection mode and batch actions
- Image list filters use `date_from` and `date_to` query parameters
- Prompt editing uses a dedicated sidebar entry rather than model config action
  buttons
- Qwen3-VL results are rendered as structured detail content instead of raw JSON

## Documentation Convention

When a feature changes behavior, update the matching document under `docs/` in
the same change set rather than leaving `CLAUDE.md` to drift.
