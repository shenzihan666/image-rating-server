# CLI Usage Guide

本项目提供业务 API CLI：`irs`，用于直接调用后端 `/api/v1` 的核心能力（images/upload/ai/models/analyze/prompts）。

当前后端未启用内置用户鉴权，CLI 请求不会主动附带用户凭证。

## 1. 快速开始

前置条件：
- 在仓库内完成后端依赖安装（`cd backend && uv sync`）
- 后端服务可访问（默认 `http://localhost:8080`）

查看帮助：

```bash
cd backend
uv run irs --help
```

查看某个命令组帮助：

```bash
uv run irs images --help
uv run irs ai prompts --help
```

## 2. 全局参数

`irs` 根命令支持以下全局参数（必须写在子命令前）：

- `--base-url`：后端地址，默认 `http://localhost:8080`
  - 支持传入：
    - `http://localhost:8080`（CLI 自动补全为 `/api/v1`）
    - `http://localhost:8080/api`
    - `http://localhost:8080/api/v1`
- `--json`：JSON 输出模式（适合脚本/CI）
- `--timeout`：请求超时秒数（默认 `30`）
- `--verbose`：输出请求/响应调试信息到 `stderr`，不会污染 `--json` 的 `stdout`

环境变量：

- `IMAGE_RATING_BASE_URL`

示例：

```bash
uv run irs --base-url http://localhost:8080 images list
uv run irs --json --verbose images list > images.json
```

## 3. 命令总览

### 3.1 images

- `images list [--page --page-size --search --date-from --date-to]`
- `images get <image_id>`
- `images analysis <image_id>`
- `images update <image_id> [--title] [--description]`
- `images delete <image_id>`
- `images delete-batch --ids a,b,c` 或 `--ids-file ids.txt`

示例：

```bash
uv run irs images list --search cat
uv run irs images list --date-from 2024-01-01 --date-to 2024-12-31
uv run irs images update <image_id> --title "new-title"
uv run irs images delete-batch --ids-file ./ids.txt
```

说明：
- `images list` 始终发送 `page` 和 `page_size`
- `--search`、`--date-from`、`--date-to` 仅在显式传参时才会附带到请求中

`ids.txt` 示例（每行一个 ID）：

```text
img-id-1
img-id-2
img-id-3
```

### 3.2 upload

- `upload files <file1> <file2> ... [--hashes '["..."]' | --hashes-file hashes.json]`

示例：

```bash
uv run irs upload files ./a.jpg ./b.png
uv run irs upload files ./a.jpg --hashes-file ./hashes.json
```

说明：
- CLI 会根据文件扩展名推断上传时使用的 MIME type
- 当前内置支持的常见图片类型：`.jpg`、`.jpeg`、`.png`、`.gif`、`.webp`、`.bmp`
- 如果扩展名无法识别，CLI 会回退为 `image/jpeg`

`hashes.json` 示例：

```json
[
  "sha256hex1",
  "sha256hex2"
]
```

### 3.3 ai models

- `ai models list`
- `ai models active`
- `ai models activate <model_name>`
- `ai models deactivate`
- `ai models get <model_name>`
- `ai models config set <model_name> --set key=value [--set ...] [--config-json config.json]`
- `ai models test-connection <model_name>`

示例：

```bash
uv run irs ai models list
uv run irs ai models config set qwen3-vl \
  --set api_key=xxx \
  --set base_url=https://dashscope.aliyuncs.com/compatible-mode/v1 \
  --set model_name=qwen3-vl-plus
uv run irs ai models activate qwen3-vl
```

`config.json` 示例：

```json
{
  "api_key": "xxx",
  "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
  "model_name": "qwen3-vl-plus"
}
```

### 3.4 ai analyze

- `ai analyze run <image_id> [--force-new]`
- `ai analyze batch --ids a,b,c | --ids-file ids.txt [--force-new]`

示例：

```bash
uv run irs ai analyze run <image_id>
uv run irs ai analyze batch --ids-file ./ids.txt --force-new
```

### 3.5 ai prompts

- `ai prompts list [--model-name qwen3-vl]`
- `ai prompts create --model-name <name> --name <name> [--description] [--system-prompt | --system-prompt-file] [--user-prompt | --user-prompt-file] [--commit-message] [--created-by]`
- `ai prompts get <prompt_id>`
- `ai prompts update <prompt_id> [--name] [--description] [--is-active true|false] [--inactive]`
- `ai prompts delete <prompt_id>`
- `ai prompts versions list <prompt_id>`
- `ai prompts versions create <prompt_id> [--system-prompt | --system-prompt-file] [--user-prompt | --user-prompt-file] [--commit-message] [--created-by]`
- `ai prompts versions get <prompt_id> <version_id>`

创建 Prompt（字符串参数方式）：

```bash
uv run irs ai prompts create \
  --model-name qwen3-vl \
  --name "Editorial Scoring" \
  --description "Score editorial quality of images" \
  --system-prompt "You are a strict reviewer" \
  --user-prompt "Analyze {{image_name}}"
```

说明：
- 新创建的 Prompt 默认处于 **active** 状态
- `--description` 是可选参数，用于补充说明 Prompt 用途
- 使用 `--inactive` 创建不活跃的 Prompt
- 可选参数 `--commit-message` 和 `--created-by` 用于版本跟踪

创建 Prompt（文件方式，推荐）：

```bash
uv run irs ai prompts create \
  --model-name qwen3-vl \
  --name "Editorial Scoring" \
  --system-prompt-file ./system_prompt.txt \
  --user-prompt-file ./user_prompt.txt \
  --commit-message "init" \
  --created-by "cli-user"
```

新增版本：

```bash
uv run irs ai prompts versions create <prompt_id> \
  --system-prompt-file ./system_prompt_v2.txt \
  --user-prompt-file ./user_prompt_v2.txt \
  --commit-message "refine tone"
```

更新 Prompt 状态：

```bash
uv run irs ai prompts update <prompt_id> --is-active true
uv run irs ai prompts update <prompt_id> --is-active false
uv run irs ai prompts update <prompt_id> --inactive
```

说明：
- `--is-active true|false` 适合脚本或显式传值场景。解析方式为 `--is-active/--inactive` Click 标志，`true` 对应启用状态，`false` 对应停用状态
- `--inactive` 是 `--is-active false` 的快捷写法
- 不要同时传 `--is-active` 和 `--inactive`

## 4. 输出格式

默认是人类可读格式（表格或 key-value）。

如需机器可读输出，统一加 `--json`：

```bash
uv run irs --json images list
```

建议在脚本中始终使用 `--json`，并通过 `jq` 等工具解析。
如需同时开启调试输出，配合 `--verbose` 即可；调试信息会写入 `stderr`。

## 5. 退出码

- `0`：成功
- `2`：命令参数错误
- `3`：HTTP 401
- `4`：权限不足（403）
- `5`：资源不存在（404）
- `6`：业务校验/冲突（400/409/422）
- `10`：服务端错误（5xx）
- `11`：网络或其他请求错误

## 6. 常见问题

1. 请求地址不对（404/路径错误）  
   检查 `--base-url`，CLI 会自动补 `/api/v1`。推荐直接传服务根地址：`http://localhost:8080`。

2. Prompt 文本太长命令行难维护  
   使用 `--system-prompt-file` 和 `--user-prompt-file`。

3. 批量命令参数太长  
   使用 `--ids-file`，每行一个 ID。

## 7. 脚本化示例

```bash
#!/usr/bin/env bash
set -euo pipefail

BASE_URL="http://localhost:8080"

cd backend

# 拉取第一页图片 ID
IMAGE_ID=$(uv run irs --json --base-url "$BASE_URL" images list \
  | jq -r '.items[0].id')

# 分析该图片
uv run irs --json --base-url "$BASE_URL" ai analyze run "$IMAGE_ID" --force-new
```
