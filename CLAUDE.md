# CLAUDE.md

This repository is a full-stack image management and AI analysis platform.

## Project Goal
- Provide one workflow for authenticated image upload, browsing, detail review, and AI-assisted quality analysis.
- Keep analysis results persistent so the frontend can reuse cached output instead of recomputing by default.
- Support model operations and prompt management without mixing them into unrelated screens.
- Treat Qwen3-VL prompt management as the current active feature area on top of the original NIMA quality-scoring flow.

## System Snapshot
- Backend: FastAPI, async SQLAlchemy, SQLite, service-oriented modules.
- Frontend: Next.js 15 App Router, TypeScript, Tailwind CSS, shadcn/ui, NextAuth.
- AI layer: one active model at runtime; current model paths are NIMA and Qwen3-VL.
- Main user surfaces: auth, upload, image gallery, image detail, AI analysis, prompt management.

## Read Docs For Details
- Start with `docs/README.md`.
- Project background: `docs/project/project-overview.md`
- Architecture: `docs/architecture/README.md`
- API surface: `docs/api/README.md`
- Commands and environment: `docs/development/README.md`
- Feature notes: `docs/features/README.md`
- Delivery history: `docs/changes/README.md`
- Operational guides: `docs/runbooks/README.md`

Use the `docs/` tree for commands, routes, configuration, conventions, and feature history.
