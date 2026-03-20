# Environment

## Default Local Ports

- Backend API: `http://localhost:8080`
- OpenAPI docs: `http://localhost:8080/docs`
- Frontend app: `http://localhost:8081`

## Backend Environment Variables

Use `backend/.env.example` as the starting template.

| Variable | Purpose | Default / Note |
| --- | --- | --- |
| `APP_NAME` | Application name | `Image Rating Server` |
| `APP_VERSION` | Version string | `0.1.0` |
| `DEBUG` | Debug mode | `false` in code, `true` in example |
| `ENVIRONMENT` | Runtime environment label | `development` |
| `HOST` | Backend bind host | `0.0.0.0` |
| `PORT` | Backend port | `8080` |
| `SECRET_KEY` | JWT signing key | Required |
| `ALGORITHM` | JWT algorithm | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access-token lifetime | `30` |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Refresh-token lifetime | `7` |
| `FRONTEND_URL` | Primary frontend origin | `http://localhost:8081` |
| `ALLOWED_ORIGINS` | CORS allowlist | Comma-separated origins; with the default Next proxy, browsers call `/api/v1` on the frontend origin, so CORS is often unnecessary for that path |
| `DATABASE_URL` | SQLAlchemy database URL | SQLite by default |
| `DATABASE_ECHO` | SQL logging toggle | `false` |
| `LOG_LEVEL` | Runtime log level | `INFO` |
| `LOG_FILE_PATH` | Backend log file | `logs/app.log` |
| `QWEN3_VL_API_KEY` | Qwen3-VL API key fallback | Optional |
| `QWEN3_VL_BASE_URL` | Qwen3-VL base URL fallback | Optional |
| `QWEN3_VL_MODEL_NAME` | Qwen3-VL model fallback | Optional |
| `UPLOAD_DIR` | Upload storage path | `uploads` |
| `UPLOAD_MAX_FILE_SIZE` | Max single-file size | `52428800` |
| `UPLOAD_MAX_FILES_PER_REQUEST` | Max files per upload request | `10` |
| `UPLOAD_ALLOWED_EXTENSIONS` | Allowed file extensions | Comma-separated |

## Frontend Environment Variables

Create `frontend/.env.local` for local overrides.

| Variable | Purpose | Default / Note |
| --- | --- | --- |
| `BACKEND_URL` | URL the **Next.js server** uses to proxy `/api/v1/*` and `/uploads/*` to FastAPI | Falls back to `NEXT_PUBLIC_API_URL`, then `http://127.0.0.1:8080` |
| `NEXT_PUBLIC_API_URL` | Optional fallback for `BACKEND_URL` when unset (not required in the browser for API calls) | e.g. `http://localhost:8080` for local dev |
| `NEXT_ALLOWED_DEV_ORIGINS` | Dev-only: hostnames allowed to load `/_next/*` when not using localhost (comma-separated) | e.g. `47.113.187.234` or `dev.example.com` |
| `AUTH_SECRET` | Preferred NextAuth secret | Optional but recommended |
| `NEXTAUTH_SECRET` | Fallback NextAuth secret | Used when `AUTH_SECRET` is absent |

## Configuration Precedence

- Backend model config may be persisted in the database
- Backend `.env` values act as runtime fallback defaults
- Frontend: the browser calls **same-origin** `/api/v1` and `/uploads`; set `BACKEND_URL` (or `NEXT_PUBLIC_API_URL`) so the Next process can reach the API on whatever host/port it listens (localhost, Docker service name, `127.0.0.1`, etc.)—no fixed public IP in the client bundle
