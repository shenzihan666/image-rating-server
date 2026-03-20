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
| `ALLOWED_ORIGINS` | CORS allowlist | Comma-separated URLs |
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
| `NEXT_PUBLIC_API_URL` | Backend base URL for browser and server calls | `http://localhost:8080` |
| `NEXT_ALLOWED_DEV_ORIGINS` | Dev-only: hostnames allowed to load `/_next/*` when not using localhost (comma-separated) | e.g. `47.113.187.234` or `dev.example.com` |
| `AUTH_SECRET` | Preferred NextAuth secret | Optional but recommended |
| `NEXTAUTH_SECRET` | Fallback NextAuth secret | Used when `AUTH_SECRET` is absent |

## Configuration Precedence

- Backend model config may be persisted in the database
- Backend `.env` values act as runtime fallback defaults
- Frontend environment values only affect frontend runtime behavior and API target
