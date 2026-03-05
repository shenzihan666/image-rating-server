#!/usr/bin/env bash
# Run upload API tests
cd "$(dirname "$0")/../backend"
uv run pytest tests/api/v1/test_upload.py -v --tb=short "$@"
