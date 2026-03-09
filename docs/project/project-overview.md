# Project Overview

## Background

Image Rating Server started as a full-stack application for storing images and
running quality scoring against them. The original AI path centered on NIMA. The
project has since expanded into a broader image analysis workspace with managed
model configuration, persistent result storage, and Qwen3-VL prompt operations.

## Product Goals

- Give authenticated users a single place to upload and manage image assets
- Persist image metadata and AI analysis results for reuse in the dashboard
- Support model-specific workflows without coupling them to generic image screens
- Keep prompt changes traceable for Qwen3-VL by storing immutable versions

## Main User Surface

The current product surface includes:

- Login and authenticated dashboard access
- Multi-image upload with deduplication and hash verification
- Paginated image gallery with search, date filtering, and batch actions
- Image detail view with AI result presentation
- AI model activation and configuration
- Qwen3-VL prompt listing, editing, version history, and comparison

## Stack Snapshot

- Backend: FastAPI, async SQLAlchemy, Pydantic settings, SQLite by default
- Frontend: Next.js 15 App Router, TypeScript, Tailwind CSS, shadcn/ui
- Authentication: JWT backend with NextAuth credential-session integration
- AI analysis: NIMA quality scoring and Qwen3-VL multimodal analysis

## Current Delivery Focus

The most recent delivery work centers on Qwen3-VL:

- Database-backed prompt management
- Immutable prompt version history
- Runtime prompt injection in the analyzer
- Structured Qwen3-VL result rendering in the image detail page

For implementation details, continue with:

- [Architecture Overview](../architecture/system-overview.md)
- [API Overview](../api/api-overview.md)
- [Development Docs](../development/README.md)
- [Qwen3-VL Feature Docs](../features/qwen3-vl/README.md)
