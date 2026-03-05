@echo off
REM Run upload API tests
cd /d "%~dp0..\backend"
uv run pytest tests/api/v1/test_upload.py -v --tb=short %*
