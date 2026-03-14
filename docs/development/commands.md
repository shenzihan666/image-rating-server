# Development Commands

## macOS Bootstrap

Install runtime dependencies with Homebrew:

```bash
brew update
brew install python@3.11 node uv
```

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

## Backend CLI (Business API)

Run from `backend/`:

```bash
# Show CLI help
uv run irs --help

# Login (returns access/refresh token)
uv run irs --json auth login --email demo@example.com

# List images with token
uv run irs --token <ACCESS_TOKEN> images list --page 1 --page-size 20

# List images in JSON while keeping verbose diagnostics on stderr
uv run irs --json --verbose --token <ACCESS_TOKEN> images list > images.json

# Update prompt active status
uv run irs ai prompts update <PROMPT_ID> --is-active false
uv run irs ai prompts update <PROMPT_ID> --inactive

# Batch analyze images
uv run irs --token <ACCESS_TOKEN> ai analyze batch --ids img1,img2 --force-new
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
