# Local Development

## Prerequisites

- Python 3.11+
- Node.js 18+
- `uv`
- `npm`

## First-Time Setup

1. Copy `backend/.env.example` to `backend/.env`
2. Fill in at least `SECRET_KEY`
3. Add any Qwen3-VL fallback settings needed for local testing
4. Create `frontend/.env.local` if you need a non-default API target or auth
   secret

## Start the Stack

Preferred repository-level helpers:

```bash
scripts\dev.bat
./scripts/dev.sh
```

Manual startup also works:

```bash
cd backend
uv sync
uv run uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

```bash
cd frontend
npm install
npm run dev
```

## Smoke Checks

After startup, verify:

1. `http://localhost:8080/docs` loads
2. `http://localhost:8081` loads
3. Login succeeds
4. The image dashboard can list existing images
5. Qwen prompt pages render if the feature is enabled in the current build

## Common Validation

- Backend tests: `cd backend && uv run pytest`
- Frontend type check: `cd frontend && npm run type-check`
- Frontend E2E tests: `cd frontend && npm run test`
