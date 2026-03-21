# MCP Server

The MCP (Model Context Protocol) server exposes the Image Rating Server API as
tools that AI agents can call via natural language. It communicates with the
backend over HTTP, identical to the CLI.

## Quick Start

```bash
cd backend
uv sync
uv run irs-mcp
```

The server starts in **stdio** transport mode, which is the standard for local
AI agent integrations.

## Connecting to OpenClaw

1. Make sure the backend is running (`uv run uvicorn app.main:app --port 8080`).
2. Add the following to `~/.config/openclaw/openclaw.json5`:

```json5
{
  mcp: {
    servers: {
      "image-rating": {
        command: "uv",
        args: ["run", "irs-mcp"],
        cwd: "/absolute/path/to/backend"
      }
    }
  }
}
```

3. OpenClaw will auto-detect and load the 25 tools on next startup.

## Connecting to Claude Desktop

Add to Claude Desktop's `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "image-rating": {
      "command": "uv",
      "args": ["run", "irs-mcp"],
      "cwd": "/absolute/path/to/backend"
    }
  }
}
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `IMAGE_RATING_BASE_URL` | `http://localhost:8080` | Backend API URL |
| `IMAGE_RATING_TIMEOUT` | `30` | Request timeout in seconds |

## Available Tools (25)

### Images

| Tool | Description |
|------|-------------|
| `list_images` | List images with pagination, search, and date filters |
| `get_image` | Get detailed info about a single image |
| `get_image_analysis` | Get the latest AI analysis result for an image |
| `update_image` | Update an image's title and/or description |
| `delete_image` | Delete an image and its file |
| `delete_images_batch` | Delete multiple images at once |

### Upload

| Tool | Description |
|------|-------------|
| `upload_images` | Upload image files from local paths |

### AI Models

| Tool | Description |
|------|-------------|
| `list_ai_models` | List all available AI models |
| `get_active_model` | Get the currently active model |
| `activate_model` | Activate a model (nima, qwen3-vl) |
| `deactivate_model` | Deactivate the current model |
| `get_model_detail` | Get model details and config fields |
| `update_model_config` | Update model configuration |
| `test_model_connection` | Test model connectivity |

### AI Analysis

| Tool | Description |
|------|-------------|
| `analyze_image` | Run AI analysis on a single image |
| `batch_analyze_images` | Batch analyze multiple images |

### AI Prompts

| Tool | Description |
|------|-------------|
| `list_prompts` | List prompts, optionally filtered by model |
| `get_prompt` | Get prompt details |
| `create_prompt` | Create a new prompt with initial version |
| `update_prompt` | Update prompt metadata |
| `delete_prompt` | Delete a prompt and all versions |
| `list_prompt_versions` | List all versions of a prompt |
| `get_prompt_version` | Get a specific prompt version |
| `create_prompt_version` | Create a new version of a prompt |

### Utility

| Tool | Description |
|------|-------------|
| `health_check` | Check if the backend is reachable |

## Architecture

```
AI Agent (OpenClaw / Claude)
    │  stdio / MCP protocol
    ▼
MCP Server (app/mcp_server.py)
    │  HTTP (httpx)
    ▼
FastAPI Backend (:8080/api/v1)
    │
    ▼
SQLite + File Storage
```

The MCP server is a thin wrapper that translates MCP tool calls into REST API
requests. It shares no database connections with the backend and can run on a
separate machine as long as the backend URL is reachable.
