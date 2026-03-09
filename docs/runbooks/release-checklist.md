# Release Checklist

## Backend

- Confirm schema changes are applied before deployment
- Verify the backend starts with the target environment variables
- Check `/docs` and `/api/v1/` root availability
- Confirm image upload and image listing still work

## Frontend

- Run `npm run build`
- Run `npm run type-check`
- Verify login and dashboard routing
- Verify image detail pages still render current analysis data

## Qwen3-VL

- Confirm model configuration is present in database or `.env`
- Confirm the default prompt is seeded when expected
- Verify prompt list, prompt detail, version history, and compare flow
- Verify analysis results retain prompt metadata after execution

## Documentation

- Update the relevant page under `docs/features/`
- Add or update a dated file under `docs/changes/` for notable deliveries
- Keep root `CLAUDE.md` short and move detail into `docs/`
