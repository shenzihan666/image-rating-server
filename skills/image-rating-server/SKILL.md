---
name: image_rating_server
description: Manage images and run AI quality analysis via the Image Rating Server CLI (irs). Use when asked to upload images, browse/search/filter the image gallery, view or update image metadata, run NIMA or Qwen3-VL AI analysis, manage AI models, or create and version analysis prompts.
metadata: {"openclaw":{"emoji":"🖼️","requires":{"bins":["uv"]},"os":["darwin","linux"]}}
---

# Image Rating Server

Operate the Image Rating Server through the `irs` CLI. The server is a full-stack image management and AI analysis platform supporting NIMA aesthetic scoring and Qwen3-VL multimodal analysis.

## Prerequisites

- The backend must be running (default `http://localhost:8080`).
- Run all commands from the **backend directory** of the project.
- The CLI is invoked via `uv run irs`.

Verify connectivity first:

```
uv run irs --json images list --page 1 --page-size 1
```

If the backend is on a non-default address, set the environment variable or pass `--base-url`:

```
IMAGE_RATING_BASE_URL=http://host:port uv run irs ...
uv run irs --base-url http://host:port ...
```

## Global Flags

Always place global flags **before** the subcommand:

| Flag | Purpose |
|------|---------|
| `--json` | Machine-readable JSON output (always use this) |
| `--base-url URL` | Backend address (default `http://localhost:8080`) |
| `--timeout N` | Request timeout in seconds (default 30) |
| `--verbose` | Debug info to stderr |

**Important:** Always use `--json` so you can parse structured output. Pipe through `jq` when you need to extract fields.

## Commands

### Images

**List images** (paginated, with optional search and date filters):

```
uv run irs --json images list [--page N] [--page-size N] [--search KEYWORD] [--date-from YYYY-MM-DD] [--date-to YYYY-MM-DD]
```

**Get single image details:**

```
uv run irs --json images get <image_id>
```

**Get AI analysis result for an image:**

```
uv run irs --json images analysis <image_id>
```

**Update image metadata:**

```
uv run irs --json images update <image_id> [--title "New Title"] [--description "New description"]
```

At least one of `--title` or `--description` is required.

**Delete a single image:**

```
uv run irs --json images delete <image_id>
```

**Batch delete images:**

```
uv run irs --json images delete-batch --ids id1,id2,id3
```

Or from a file (one ID per line):

```
uv run irs --json images delete-batch --ids-file ids.txt
```

### Upload

**Upload image files:**

```
uv run irs --json upload files /path/to/image1.jpg /path/to/image2.png
```

Supported formats: `.jpg`, `.jpeg`, `.png`, `.gif`, `.webp`, `.bmp`.
Upload timeout is automatically extended to at least 120 seconds.

### AI Models

**List available models:**

```
uv run irs --json ai models list
```

**Get active model:**

```
uv run irs --json ai models active
```

**Activate a model** (`nima` or `qwen3-vl`):

```
uv run irs --json ai models activate <model_name>
```

**Deactivate the active model:**

```
uv run irs --json ai models deactivate
```

**Get model details and configuration:**

```
uv run irs --json ai models get <model_name>
```

**Update model configuration** (e.g. set Qwen3-VL API credentials):

```
uv run irs --json ai models config set qwen3-vl \
  --set api_key=sk-xxx \
  --set base_url=https://dashscope.aliyuncs.com/compatible-mode/v1 \
  --set model_name=qwen3-vl-plus
```

Or from a JSON file:

```
uv run irs --json ai models config set qwen3-vl --config-json config.json
```

**Test model connection:**

```
uv run irs --json ai models test-connection <model_name>
```

### AI Analysis

**Analyze a single image** (uses the active model):

```
uv run irs --json ai analyze run <image_id> [--force-new]
```

`--force-new` re-runs analysis even if cached results exist.

**Batch analyze multiple images:**

```
uv run irs --json ai analyze batch --ids id1,id2,id3 [--force-new]
```

Or from a file:

```
uv run irs --json ai analyze batch --ids-file ids.txt [--force-new]
```

Batch analysis timeout is automatically extended to at least 300 seconds.

### AI Prompts (Qwen3-VL)

**List prompts:**

```
uv run irs --json ai prompts list [--model-name qwen3-vl]
```

**Create a prompt:**

```
uv run irs --json ai prompts create \
  --model-name qwen3-vl \
  --name "Prompt Name" \
  --system-prompt "You are an image quality analyst." \
  --user-prompt "Analyze this image for composition and lighting." \
  [--description "Optional description"] \
  [--commit-message "Initial version"] \
  [--created-by "author"]
```

For long prompt text, use files instead:

```
uv run irs --json ai prompts create \
  --model-name qwen3-vl \
  --name "Prompt Name" \
  --system-prompt-file /path/to/system_prompt.txt \
  --user-prompt-file /path/to/user_prompt.txt
```

**Get prompt details:**

```
uv run irs --json ai prompts get <prompt_id>
```

**Update prompt metadata:**

```
uv run irs --json ai prompts update <prompt_id> [--name "New Name"] [--description "New desc"] [--is-active true|false]
uv run irs --json ai prompts update <prompt_id> --inactive
```

**Delete a prompt:**

```
uv run irs --json ai prompts delete <prompt_id>
```

**List prompt versions:**

```
uv run irs --json ai prompts versions list <prompt_id>
```

**Create a new prompt version:**

```
uv run irs --json ai prompts versions create <prompt_id> \
  --system-prompt "Updated system prompt" \
  --user-prompt "Updated user prompt" \
  [--commit-message "What changed"] \
  [--created-by "author"]
```

**Get a specific version:**

```
uv run irs --json ai prompts versions get <prompt_id> <version_id>
```

## Working Directory

All `uv run irs` commands must be run from the project's `backend/` directory. Set the working directory before executing:

```
cd /path/to/image-rating-server/backend
```

Or use `exec` with `workdir` parameter pointing to the backend directory.

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 2 | Argument error |
| 3 | Unauthorized (401) |
| 4 | Forbidden (403) |
| 5 | Not found (404) |
| 6 | Validation error (400/409/422) |
| 10 | Server error (5xx) |
| 11 | Network / other error |

Check exit codes to determine if a command succeeded. On non-zero exit, the error message is printed to stderr.

## Safety Rules

- **Never delete images without explicit user confirmation.** Always ask before running `images delete` or `images delete-batch`.
- **Never deactivate the AI model without user confirmation.**
- **Do not expose API keys in output.** When showing model config, redact sensitive fields.
- **Always use `--json` for parsing.** Do not attempt to parse human-readable table output.
- **For long-running batch operations**, inform the user that analysis may take time (batch analyze can run for several minutes).

## Common Workflows

### Upload and analyze images

```bash
# 1. Upload
RESULT=$(uv run irs --json upload files /path/to/photo.jpg)
IMAGE_ID=$(echo "$RESULT" | jq -r '.results[0].image.id')

# 2. Check active model
uv run irs --json ai models active

# 3. Activate model if needed
uv run irs --json ai models activate qwen3-vl

# 4. Analyze
uv run irs --json ai analyze run "$IMAGE_ID"
```

### Browse and search gallery

```bash
# Search for images
uv run irs --json images list --search "sunset" --page 1 --page-size 10

# Filter by date
uv run irs --json images list --date-from 2025-01-01 --date-to 2025-12-31

# Get details for a specific image
uv run irs --json images get <image_id>

# Get its analysis
uv run irs --json images analysis <image_id>
```

### Set up Qwen3-VL model

```bash
# 1. Configure
uv run irs --json ai models config set qwen3-vl \
  --set api_key=sk-xxx \
  --set base_url=https://dashscope.aliyuncs.com/compatible-mode/v1 \
  --set model_name=qwen3-vl-plus

# 2. Test connection
uv run irs --json ai models test-connection qwen3-vl

# 3. Activate
uv run irs --json ai models activate qwen3-vl
```

### Manage prompts

```bash
# List all prompts for qwen3-vl
uv run irs --json ai prompts list --model-name qwen3-vl

# Create a new prompt
uv run irs --json ai prompts create \
  --model-name qwen3-vl \
  --name "Landscape Scorer" \
  --system-prompt "You evaluate landscape photography." \
  --user-prompt "Score this landscape photo on a 1-10 scale."

# Create a new version of an existing prompt
uv run irs --json ai prompts versions create <prompt_id> \
  --system-prompt "You evaluate landscape photography with emphasis on composition." \
  --user-prompt "Score this landscape photo on a 1-10 scale. Focus on rule of thirds." \
  --commit-message "Add composition focus"
```
