#!/usr/bin/env bash
# Quick environment check for the Image Rating Server skill.
# Usage: bash {baseDir}/check-env.sh [backend_dir] [base_url]
set -euo pipefail

BACKEND_DIR="${1:-$(pwd)}"
BASE_URL="${2:-${IMAGE_RATING_BASE_URL:-http://localhost:8080}}"

errors=0

echo "=== Image Rating Server environment check ==="

# 1. uv available?
if command -v uv &>/dev/null; then
  echo "[OK] uv found: $(uv --version 2>/dev/null || echo 'unknown')"
else
  echo "[FAIL] uv not found on PATH"
  errors=$((errors + 1))
fi

# 2. backend dir exists and has pyproject.toml?
if [[ -f "$BACKEND_DIR/pyproject.toml" ]]; then
  echo "[OK] backend dir: $BACKEND_DIR"
else
  echo "[FAIL] pyproject.toml not found in $BACKEND_DIR"
  errors=$((errors + 1))
fi

# 3. backend reachable?
if command -v curl &>/dev/null; then
  HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 "$BASE_URL/health" 2>/dev/null || echo "000")
  if [[ "$HTTP_CODE" == "200" ]]; then
    echo "[OK] backend reachable at $BASE_URL (HTTP $HTTP_CODE)"
  else
    echo "[WARN] backend not reachable at $BASE_URL (HTTP $HTTP_CODE)"
  fi
else
  echo "[SKIP] curl not available, cannot check backend connectivity"
fi

# 4. irs CLI runnable?
if [[ -f "$BACKEND_DIR/pyproject.toml" ]] && command -v uv &>/dev/null; then
  if (cd "$BACKEND_DIR" && uv run irs --help &>/dev/null); then
    echo "[OK] irs CLI is runnable"
  else
    echo "[WARN] irs CLI failed — run 'uv sync' in $BACKEND_DIR first"
  fi
fi

echo "=== Done ($errors error(s)) ==="
exit "$errors"
