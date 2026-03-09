# Development Commands

## Backend

Run these from `backend/`:

```bash
uv sync
uv run uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
uv run pytest
uv run black .
uv run ruff check .
uv run mypy app
```

## Frontend

Run these from `frontend/`:

```bash
npm install
npm run dev
npm run build
npm run lint
npm run type-check
npm run test
```

## Combined Startup

Repository-level helper scripts:

```bash
scripts\dev.bat
./scripts/dev.sh
```

These scripts install missing project dependencies when needed and start backend
on `8080` plus frontend on `8081`.

## Useful Validation Commands

Common checks used during implementation:

```bash
cd backend
uv run pytest tests/api/v1/test_ai_prompts.py tests/api/v1/test_ai_analyze.py

cd frontend
npm run type-check
```
