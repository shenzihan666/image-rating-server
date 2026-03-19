# API Tests

This directory contains automated tests for the Image Rating Server API.

## Structure

```
tests/
├── conftest.py           # Shared pytest fixtures and configuration
├── api/
│   └── v1/
│       └── test_upload.py  # Upload API endpoint tests
```

## Running Tests

### Run all tests
```bash
cd backend
uv run pytest
```

### Run upload endpoint tests only
```bash
cd backend
uv run pytest tests/api/v1/test_upload.py
```

### Run with verbose output
```bash
cd backend
uv run pytest -v
```

### Run specific test
```bash
cd backend
uv run pytest tests/api/v1/test_upload.py::TestUploadEndpointSuccess::test_upload_single_image_success
```

### Run with coverage
```bash
cd backend
uv run pytest --cov=app --cov-report=html
```

## Test Coverage

The `/api/v1/upload` endpoint tests cover:

### Access Control Notes
- The current upload endpoint does not require built-in user authentication.
- If gateway or middleware auth is added later, add the matching 401/403 tests here.

### Success Scenarios (`TestUploadEndpointSuccess`)
- Single image upload success
- Multiple image upload success
- Upload with valid SHA256 hash
- Image dimension extraction

### Duplicate Detection (`TestUploadEndpointDuplicateDetection`)
- Duplicate image returns "duplicated" status
- Duplicate detection works even with wrong hash provided

### Input Validation (`TestUploadEndpointValidation`)
- Empty file list handling
- Max files per request enforcement
- Invalid file extension rejection
- Missing filename handling

### Hash Handling (`TestUploadEndpointHashHandling`)
- Correct hash is stored when provided hash mismatches
- Invalid JSON in hashes parameter doesn't break upload

### Response Format (`TestUploadEndpointResponseFormat`)
- Response contains all required fields
- Result items match UploadResult schema

### File Type Support (`TestUploadEndpointMultipleFileTypes`)
- JPEG upload
- PNG upload
- GIF upload
- WebP upload
- BMP upload

## Fixtures

Key fixtures used by the upload tests:

- `async_client` - HTTP client for testing FastAPI app
- `db_session` - Isolated database session used by upload tests
- `temp_upload_dir` - Temporary upload directory override
- `test_db_path` - Per-test SQLite path
- `test_image_path` - Writable path for the minimal JPEG sample
- `sample_image_bytes` - Raw test image content

## Test Data

Tests use the image at:
```
D:\Project\image-rating-server\1.合格.jpg
```

Ensure this file exists before running tests.

## Environment

Tests use a separate test database (`test_app.db`) and test upload directory (`test_uploads/`) to avoid affecting development data.
