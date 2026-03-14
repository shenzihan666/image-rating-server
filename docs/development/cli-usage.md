# CLI Usage Guide

本项目提供业务 API CLI：`irs`，用于直接调用后端 `/api/v1` 的所有核心能力（auth/users/images/upload/ai/models/analyze/prompts）。

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
- `--token`：Bearer Access Token（无状态，不会持久化）
- `--json`：JSON 输出模式（适合脚本/CI）
- `--timeout`：请求超时秒数（默认 `30`）
- `--verbose`：预留调试开关

环境变量：
- `IMAGE_RATING_BASE_URL`
- `IMAGE_RATING_TOKEN`

示例：

```bash
uv run irs --base-url http://localhost:8080 --token <ACCESS_TOKEN> images list
uv run irs --json --token <ACCESS_TOKEN> auth me
```

## 3. 认证说明（无状态）

CLI 不保存登录态，每次执行鉴权命令时都需要：
- 显式传 `--token`，或
- 预先设置 `IMAGE_RATING_TOKEN`

登录获取 token：

```bash
uv run irs --json auth login --email demo@example.com --password password123
```

使用 refresh token 换取新 token：

```bash
uv run irs --json auth refresh --refresh-token <REFRESH_TOKEN>
```

查看当前用户：

```bash
uv run irs --token <ACCESS_TOKEN> auth me
```

## 4. 命令总览

### 4.1 auth

- `auth login`
- `auth refresh`
- `auth logout`
- `auth me`

示例：

```bash
uv run irs --token <ACCESS_TOKEN> auth logout
```

### 4.2 users

- `users me`
- `users update --email ... --full-name ...`
- `users change-password --old-password ... --new-password ...`
- `users list --page 1 --page-size 20`
- `users get <user_id>`

示例：

```bash
uv run irs --token <ACCESS_TOKEN> users update --full-name "New Name"
uv run irs --token <ACCESS_TOKEN> users list --page 1 --page-size 50
```

### 4.3 images

- `images list [--page --page-size --search --date-from --date-to]`
- `images get <image_id>`
- `images analysis <image_id>`
- `images update <image_id> [--title] [--description]`
- `images delete <image_id>`
- `images delete-batch --ids a,b,c` 或 `--ids-file ids.txt`

示例：

```bash
uv run irs --token <ACCESS_TOKEN> images list --search cat
uv run irs --token <ACCESS_TOKEN> images update <image_id> --title "new-title"
uv run irs --token <ACCESS_TOKEN> images delete-batch --ids-file ./ids.txt
```

`ids.txt` 示例（每行一个 ID）：

```text
img-id-1
img-id-2
img-id-3
```

### 4.4 upload

- `upload files <file1> <file2> ... [--hashes '["..."]' | --hashes-file hashes.json]`

示例：

```bash
uv run irs --token <ACCESS_TOKEN> upload files ./a.jpg ./b.png
uv run irs --token <ACCESS_TOKEN> upload files ./a.jpg --hashes-file ./hashes.json
```

`hashes.json` 示例：

```json
[
  "sha256hex1",
  "sha256hex2"
]
```

### 4.5 ai models

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

### 4.6 ai analyze

- `ai analyze run <image_id> [--force-new]`
- `ai analyze batch --ids a,b,c | --ids-file ids.txt [--force-new]`

示例：

```bash
uv run irs --token <ACCESS_TOKEN> ai analyze run <image_id>
uv run irs --token <ACCESS_TOKEN> ai analyze batch --ids-file ./ids.txt --force-new
```

### 4.7 ai prompts

- `ai prompts list [--model-name qwen3-vl]`
- `ai prompts create ...`
- `ai prompts get <prompt_id>`
- `ai prompts update <prompt_id> [--name] [--description] [--is-active true|false]`
- `ai prompts delete <prompt_id>`
- `ai prompts versions list <prompt_id>`
- `ai prompts versions create <prompt_id> ...`
- `ai prompts versions get <prompt_id> <version_id>`

创建 Prompt（字符串参数方式）：

```bash
uv run irs ai prompts create \
  --model-name qwen3-vl \
  --name "Editorial Scoring" \
  --system-prompt "You are a strict reviewer" \
  --user-prompt "Analyze {{image_name}}" \
  --commit-message "init" \
  --created-by "cli-user"
```

创建 Prompt（文件方式，推荐）：

```bash
uv run irs ai prompts create \
  --model-name qwen3-vl \
  --name "Editorial Scoring" \
  --system-prompt-file ./system_prompt.txt \
  --user-prompt-file ./user_prompt.txt
```

新增版本：

```bash
uv run irs ai prompts versions create <prompt_id> \
  --system-prompt-file ./system_prompt_v2.txt \
  --user-prompt-file ./user_prompt_v2.txt \
  --commit-message "refine tone"
```

## 5. 输出格式

默认是人类可读格式（表格或 key-value）。

如需机器可读输出，统一加 `--json`：

```bash
uv run irs --json --token <ACCESS_TOKEN> images list
```

建议在脚本中始终使用 `--json`，并通过 `jq` 等工具解析。

## 6. 退出码

- `0`：成功
- `2`：命令参数错误
- `3`：认证失败（缺 token 或 401）
- `4`：权限不足（403）
- `5`：资源不存在（404）
- `6`：业务校验/冲突（400/409/422）
- `10`：服务端错误（5xx）
- `11`：网络或其他请求错误

## 7. 常见问题

1. 提示 `Missing token`  
   说明当前命令需要鉴权，但未传 `--token` 且未设置 `IMAGE_RATING_TOKEN`。

2. 请求地址不对（404/路径错误）  
   检查 `--base-url`，CLI 会自动补 `/api/v1`。推荐直接传服务根地址：`http://localhost:8080`。

3. Prompt 文本太长命令行难维护  
   使用 `--system-prompt-file` 和 `--user-prompt-file`。

4. 批量命令参数太长  
   使用 `--ids-file`，每行一个 ID。

## 8. 脚本化示例

```bash
#!/usr/bin/env bash
set -euo pipefail

BASE_URL="http://localhost:8080"
TOKEN="$IMAGE_RATING_TOKEN"

cd backend

# 拉取第一页图片 ID
IMAGE_ID=$(uv run irs --json --base-url "$BASE_URL" --token "$TOKEN" images list \
  | jq -r '.items[0].id')

# 分析该图片
uv run irs --json --base-url "$BASE_URL" --token "$TOKEN" ai analyze run "$IMAGE_ID" --force-new
```
