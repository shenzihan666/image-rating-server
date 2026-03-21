# AI Agent Integration (OpenClaw Skill)

This project provides an OpenClaw Skill that teaches the agent to operate the
Image Rating Server through the `irs` CLI.

## Installation

Copy or symlink the skill into your OpenClaw workspace:

```bash
# Symlink (recommended — stays in sync with repo)
ln -s /path/to/image-rating-server/skills/image-rating-server \
      ~/.openclaw/skills/image-rating-server

# Or copy
cp -r /path/to/image-rating-server/skills/image-rating-server \
      ~/.openclaw/skills/image-rating-server
```

Then start a new session so OpenClaw picks it up:

```
/new
```

Verify:

```bash
openclaw skills list
```

## Prerequisites

The skill requires `uv` on PATH and the backend to be running. Run the
included check script to verify:

```bash
bash ~/.openclaw/skills/image-rating-server/check-env.sh /path/to/backend
```

## What the Skill Covers

The skill teaches the agent all `irs` CLI capabilities:

- **Images** — list, get, search, update, delete, batch delete
- **Upload** — upload image files
- **AI Models** — list, activate/deactivate, configure, test connection
- **AI Analysis** — single and batch analysis
- **AI Prompts** — create, update, delete, version management

## Architecture

```
OpenClaw Agent
    │  exec tool (shell)
    ▼
irs CLI (uv run irs ...)
    │  HTTP (httpx)
    ▼
FastAPI Backend (:8080/api/v1)
    │
    ▼
SQLite + File Storage
```

The agent uses the `exec` tool to run `irs` CLI commands. The CLI communicates
with the backend over HTTP. The backend must be running and reachable.
