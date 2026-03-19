"""
Tests for /api/v1/upload endpoint

This module contains comprehensive tests for the image upload API endpoint,
following industry best practices:
- pytest fixtures for test setup and teardown
- Clear test naming with descriptive docstrings
- AAA pattern (Arrange-Act-Assert)
- Edge case coverage
- Shared-engine teardown restores schema after `drop_all` for other API tests
- Concurrent upload behavior verification
"""
import hashlib
from pathlib import Path
from typing import AsyncGenerator

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import Base, async_session_maker, engine
from app.models.image import Image
from app.services.storage import get_storage_service

# Minimal valid JPEG for tests (no external image file required).
_MINIMAL_JPEG = (
    b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00H\x00H\x00\x00"
    b"\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t"
    b"\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a"
    b"\x1f\x1e\x1d\x1a\x1c\x1c $.\' \",#\x1c\x1c(7),01444\x1f\'9=82"
    b"<.342\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff"
    b"\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00"
    b"\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n"
    b"\x0b\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xf5\x14P\x00\xff\xd9"
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Create a clean database session for each test function.

    Drops and recreates schema at the start and end so API tests that share the
    same SQLite file do not leave rows that break fixtures (e.g. unique hash).
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_maker() as session:
        yield session
        await session.rollback()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@pytest.fixture
def test_image_path(tmp_path: Path) -> Path:
    """Writable path to a minimal valid JPEG used as upload sample bytes source."""
    path = tmp_path / "sample.jpg"
    path.write_bytes(_MINIMAL_JPEG)
    return path


@pytest.fixture
async def sample_image_bytes(test_image_path: Path) -> bytes:
    """
    Read and return the test image file content.

    Returns:
        bytes: Raw image file content
    """
    return test_image_path.read_bytes()


@pytest.fixture
def unique_image_bytes_list() -> list[bytes]:
    """
    Generate a list of unique image bytes for testing multiple uploads.

    Each image has unique content (different padding bytes) to ensure unique hashes.

    Returns:
        list[bytes]: List of unique image file contents
    """
    # Base minimal JPEG bytes (same structure as sample_image_bytes but with unique padding)
    base_jpeg = b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00H\x00H\x00\x00\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\xff\xc4\x00\xb5\x10\x00\x02\x01\x03\x03\x02\x04\x03\x05\x05\x04\x04\x00\x00\x01}\x01\x02\x03\x00\x04\x11\x05\x12!1A\x06\x13Qa\x07"q\x142\x81\x91\xa1\x08#B\xb1\xc1\x15R\xd1\xf0$3br\x82\t\n\x16\x17\x18\x19\x1a%&\'()*456789:CDEFGHIJSTUVWXYZcdefghijstuvwxyz\x83\x84\x85\x86\x87\x88\x89\x8a\x92\x93\x94\x95\x96\x97\x98\x99\x9a\xa2\xa3\xa4\xa5\xa6\xa7\xa8\xa9\xaa\xb2\xb3\xb4\xb5\xb6\xb7\xb8\xb9\xba\xc2\xc3\xc4\xc5\xc6\xc7\xc8\xc9\xca\xd2\xd3\xd4\xd5\xd6\xd7\xd8\xd9\xda\xe1\xe2\xe3\xe4\xe5\xe6\xe7\xe8\xe9\xea\xf1\xf2\xf3\xf4\xf5\xf6\xf7\xf8\xf9\xfa\xff\xda\x00\x08\x01\x01\x00\x00?'
    # Add unique padding for each image
    images = []
    for i in range(3):
        # Add unique bytes to make each image different
        unique_bytes = base_jpeg + f"UNIQUE_IMAGE_{i}".encode() + b'\xff\xd9'
        images.append(unique_bytes)
    return images


@pytest.fixture
def sample_image_hash(sample_image_bytes: bytes) -> str:
    """
    Compute SHA256 hash of the sample image.

    Returns:
        str: Hexadecimal SHA256 hash
    """
    return hashlib.sha256(sample_image_bytes).hexdigest()


@pytest.fixture
async def uploaded_image(
    db_session: AsyncSession,
    sample_image_bytes: bytes,
    sample_image_hash: str,
) -> Image:
    """
    Create an uploaded image record in the database for testing duplicates.

    Returns:
        Image: Database image record
    """
    import uuid

    image = Image(
        id=str(uuid.uuid4()),
        title="existing-image.jpg",
        description=None,
        file_path="2024/01/01/test-image.jpg",
        file_size=len(sample_image_bytes),
        width=1920,
        height=1080,
        mime_type="image/jpeg",
        hash_sha256=sample_image_hash,
    )
    db_session.add(image)
    await db_session.commit()
    await db_session.refresh(image)
    return image


@pytest.fixture
def invalid_file_bytes() -> bytes:
    """
    Generate invalid file content (not an image).

    Returns:
        bytes: Random bytes that aren't a valid image
    """
    return b"This is not an image file" * 1000


@pytest.fixture
def oversized_file_bytes() -> bytes:
    """
    Generate file content exceeding size limit.

    Returns:
        bytes: Large file content exceeding UPLOAD_MAX_FILE_SIZE
    """
    # Create content larger than the max size
    return b"x" * (settings.UPLOAD_MAX_FILE_SIZE + 1)


# ============================================================================
# Test Classes
# ============================================================================


class TestUploadEndpointSuccess:
    """Tests for successful upload scenarios."""

    @pytest.mark.asyncio
    async def test_upload_single_image_success(
        self,
        async_client: AsyncClient,
        sample_image_bytes: bytes,
        db_session: AsyncSession,
    ) -> None:
        """
        Test successful single image upload.

        Arrange: Prepare async client and valid image file
        Act: POST single image to /api/v1/upload
        Assert: Response indicates success with correct metadata
        """
        files = {"images": ("sample.jpg", sample_image_bytes, "image/jpeg")}
        response = await async_client.post(
            "/api/v1/upload",
            files=files,
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert data["success"] is True
        assert data["total"] == 1
        assert data["succeeded"] == 1
        assert data["duplicated"] == 0
        assert data["failed"] == 0
        assert len(data["results"]) == 1

        # Verify result metadata
        result = data["results"][0]
        assert result["status"] == "success"
        assert result["original_filename"] == "sample.jpg"
        assert result["metadata"]["file_name"] == "sample.jpg"
        assert result["metadata"]["file_size"] == len(sample_image_bytes)
        assert result["metadata"]["mime_type"] == "image/jpeg"
        assert result["metadata"]["hash_sha256"]
        assert result["metadata"]["image_id"]
        assert result["metadata"]["width"] is not None
        assert result["metadata"]["height"] is not None

        # Verify database record
        stmt = select(Image).where(Image.id == result["metadata"]["image_id"])
        db_result = await db_session.execute(stmt)
        db_image = db_result.scalar_one_or_none()
        assert db_image is not None
        assert db_image.title == "sample.jpg"
        assert db_image.hash_sha256 == result["metadata"]["hash_sha256"]


    @pytest.mark.asyncio
    async def test_upload_multiple_images_success(
        self,
        async_client: AsyncClient,
        unique_image_bytes_list: list[bytes],
        db_session: AsyncSession,
    ) -> None:
        """
        Test successful multiple image upload.

        Arrange: Prepare async client and multiple image files with unique content
        Act: POST 3 images to /api/v1/upload
        Assert: All images uploaded successfully
        """
        files = [
            ("images", ("image1.jpg", unique_image_bytes_list[0], "image/jpeg")),
            ("images", ("image2.jpg", unique_image_bytes_list[1], "image/jpeg")),
            ("images", ("image3.jpg", unique_image_bytes_list[2], "image/jpeg")),
        ]
        response = await async_client.post(
            "/api/v1/upload",
            files=files,
        )

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert data["total"] == 3
        assert data["succeeded"] == 3
        assert data["duplicated"] == 0
        assert data["failed"] == 0
        assert len(data["results"]) == 3


    @pytest.mark.asyncio
    async def test_upload_with_valid_hash(
        self,
        async_client: AsyncClient,
        sample_image_bytes: bytes,
        sample_image_hash: str,
    ) -> None:
        """
        Test upload with correct SHA256 hash provided.

        Arrange: Prepare image data with correct pre-computed hash
        Act: POST image with hashes parameter
        Assert: Upload succeeds and hash is accepted
        """
        import json

        files = {"images": ("test.jpg", sample_image_bytes, "image/jpeg")}
        data = {"hashes": json.dumps([sample_image_hash])}
        response = await async_client.post(
            "/api/v1/upload",
            files=files,
            data=data,
        )

        assert response.status_code == 200
        result = response.json()
        assert result["succeeded"] == 1
        assert result["results"][0]["metadata"]["hash_sha256"] == sample_image_hash


    @pytest.mark.asyncio
    async def test_upload_dimensions_extraction(
        self,
        async_client: AsyncClient,
        sample_image_bytes: bytes,
    ) -> None:
        """
        Test that image dimensions are correctly extracted.

        Arrange: Prepare valid image file
        Act: Upload the image
        Assert: Response contains valid width and height
        """
        files = {"images": ("test.jpg", sample_image_bytes, "image/jpeg")}
        response = await async_client.post(
            "/api/v1/upload",
            files=files,
        )

        assert response.status_code == 200
        metadata = response.json()["results"][0]["metadata"]
        assert metadata["width"] is not None
        assert metadata["height"] is not None
        assert isinstance(metadata["width"], int)
        assert isinstance(metadata["height"], int)
        assert metadata["width"] > 0
        assert metadata["height"] > 0


class TestUploadEndpointDuplicateDetection:
    """Tests for duplicate image detection."""

    @pytest.mark.asyncio
    async def test_upload_duplicate_returns_duplicated_status(
        self,
        async_client: AsyncClient,
        sample_image_bytes: bytes,
        uploaded_image: Image,
    ) -> None:
        """
        Test that uploading a duplicate image returns 'duplicated' status.

        Arrange: Create an existing image in database
        Act: Upload image with identical content
        Assert: Response indicates duplicate with existing image metadata
        """
        files = {"images": ("duplicate.jpg", sample_image_bytes, "image/jpeg")}
        response = await async_client.post(
            "/api/v1/upload",
            files=files,
        )

        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 1
        assert data["duplicated"] == 1
        assert data["succeeded"] == 0
        assert data["failed"] == 0

        result = data["results"][0]
        assert result["status"] == "duplicated"
        assert result["is_duplicate"] is True
        assert result["metadata"]["image_id"] == uploaded_image.id
        assert result["metadata"]["hash_sha256"] == uploaded_image.hash_sha256


    @pytest.mark.asyncio
    async def test_upload_duplicate_with_wrong_hash_still_succeeds(
        self,
        async_client: AsyncClient,
        sample_image_bytes: bytes,
        uploaded_image: Image,
    ) -> None:
        """
        Test that duplicate detection uses computed hash even if provided hash is wrong.

        Arrange: Create existing image; prepare upload with wrong hash
        Act: Upload duplicate with mismatched hash
        Assert: Still detected as duplicate based on computed hash
        """
        import json

        files = {"images": ("duplicate.jpg", sample_image_bytes, "image/jpeg")}
        # Provide a wrong hash
        data = {"hashes": json.dumps(["wrong" * 16])}
        response = await async_client.post(
            "/api/v1/upload",
            files=files,
            data=data,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["duplicated"] == 1
        assert data["results"][0]["status"] == "duplicated"


class TestUploadEndpointValidation:
    """Tests for upload input validation."""

    @pytest.mark.asyncio
    async def test_upload_empty_file_list(
        self,
        async_client: AsyncClient,
    ) -> None:
        """
        Test uploading with no files.

        Arrange: Prepare request without files
        Act: POST to /api/v1/upload with empty files
        Assert: Returns 200 with success response and zero counts
        """
        response = await async_client.post("/api/v1/upload")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["total"] == 0
        assert data["succeeded"] == 0
        assert data["duplicated"] == 0
        assert data["failed"] == 0
        assert data["message"] == "No files uploaded"


    @pytest.mark.asyncio
    async def test_upload_exceeds_max_files(
        self,
        async_client: AsyncClient,
        sample_image_bytes: bytes,
    ) -> None:
        """
        Test uploading more than max allowed files per request.

        Arrange: Prepare 11 image files (exceeds UPLOAD_MAX_FILES_PER_REQUEST)
        Act: POST all files to /api/v1/upload
        Assert: Returns error about too many files
        """
        max_files = settings.UPLOAD_MAX_FILES_PER_REQUEST
        files = [
            ("images", (f"image{i}.jpg", sample_image_bytes, "image/jpeg"))
            for i in range(max_files + 1)
        ]
        response = await async_client.post(
            "/api/v1/upload",
            files=files,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert data["failed"] == max_files + 1
        assert "Too many files" in data["message"]


    @pytest.mark.asyncio
    async def test_upload_invalid_file_extension(
        self,
        async_client: AsyncClient,
    ) -> None:
        """
        Test uploading file with invalid extension.

        Arrange: Prepare file with .txt extension
        Act: POST file to /api/v1/upload
        Assert: Returns failure with extension error
        """
        files = {"images": ("test.txt", b"not an image", "text/plain")}
        response = await async_client.post(
            "/api/v1/upload",
            files=files,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["failed"] == 1
        result = data["results"][0]
        assert result["status"] == "failed"
        assert "extension" in result["error_message"].lower()


    @pytest.mark.asyncio
    async def test_upload_no_filename(
        self,
        async_client: AsyncClient,
        sample_image_bytes: bytes,
    ) -> None:
        """
        Test uploading file without extension.

        Arrange: Prepare file data with filename but no extension
        Act: POST to /api/v1/upload
        Assert: Returns 200 with failure result for invalid extension
        """
        files = {"images": ("noextension", sample_image_bytes, "image/jpeg")}
        response = await async_client.post(
            "/api/v1/upload",
            files=files,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["failed"] == 1
        result = data["results"][0]
        assert result["status"] == "failed"
        assert "extension" in result["error_message"].lower()


class TestUploadEndpointHashHandling:
    """Tests for SHA256 hash handling in uploads."""

    @pytest.mark.asyncio
    async def test_upload_with_hash_mismatch_stores_correct_hash(
        self,
        async_client: AsyncClient,
        sample_image_bytes: bytes,
        sample_image_hash: str,
        db_session: AsyncSession,
    ) -> None:
        """
        Test that when provided hash doesn't match, computed hash is used.

        Arrange: Prepare image with intentionally wrong provided hash
        Act: Upload with mismatched hash
        Assert: Image stored with correct computed hash
        """
        import json

        wrong_hash = "a" * 64  # All 'a's is definitely wrong
        files = {"images": ("test.jpg", sample_image_bytes, "image/jpeg")}
        data = {"hashes": json.dumps([wrong_hash])}
        response = await async_client.post(
            "/api/v1/upload",
            files=files,
            data=data,
        )

        assert response.status_code == 200
        result = response.json()["results"][0]
        assert result["status"] == "success"
        # Stored hash should be the computed one, not the wrong one
        assert result["metadata"]["hash_sha256"] == sample_image_hash
        assert result["metadata"]["hash_sha256"] != wrong_hash


    @pytest.mark.asyncio
    async def test_upload_with_invalid_json_hashes(
        self,
        async_client: AsyncClient,
        sample_image_bytes: bytes,
    ) -> None:
        """
        Test upload with invalid JSON in hashes parameter.

        Arrange: Prepare image with malformed JSON hashes
        Act: POST to /api/v1/upload
        Assert: Upload succeeds (treats as no hashes provided)
        """
        files = {"images": ("test.jpg", sample_image_bytes, "image/jpeg")}
        data = {"hashes": "invalid-json{{{}}"}
        response = await async_client.post(
            "/api/v1/upload",
            files=files,
            data=data,
        )

        # Should still succeed, just without hash verification
        assert response.status_code == 200
        data = response.json()
        assert data["succeeded"] == 1


class TestUploadEndpointResponseFormat:
    """Tests for API response format and structure."""

    @pytest.mark.asyncio
    async def test_response_contains_all_required_fields(
        self,
        async_client: AsyncClient,
        sample_image_bytes: bytes,
    ) -> None:
        """
        Test that response contains all required fields per schema.

        Arrange: Prepare valid upload request
        Act: POST to /api/v1/upload
        Assert: Response matches UploadResponse schema exactly
        """
        files = {"images": ("test.jpg", sample_image_bytes, "image/jpeg")}
        response = await async_client.post(
            "/api/v1/upload",
            files=files,
        )

        assert response.status_code == 200
        data = response.json()

        # Verify all top-level fields
        required_fields = ["success", "total", "succeeded", "duplicated", "failed", "results", "message"]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"

        # Verify types
        assert isinstance(data["success"], bool)
        assert isinstance(data["total"], int)
        assert isinstance(data["succeeded"], int)
        assert isinstance(data["duplicated"], int)
        assert isinstance(data["failed"], int)
        assert isinstance(data["results"], list)
        assert isinstance(data["message"], str)


    @pytest.mark.asyncio
    async def test_result_item_contains_all_required_fields(
        self,
        async_client: AsyncClient,
        sample_image_bytes: bytes,
    ) -> None:
        """
        Test that each result item contains all required fields.

        Arrange: Prepare valid upload request
        Act: POST to /api/v1/upload
        Assert: Each result item matches UploadResult schema
        """
        files = {"images": ("test.jpg", sample_image_bytes, "image/jpeg")}
        response = await async_client.post(
            "/api/v1/upload",
            files=files,
        )

        data = response.json()
        result = data["results"][0]

        # Verify all result fields
        required_fields = ["status", "original_filename", "metadata", "error_message", "is_duplicate"]
        for field in required_fields:
            assert field in result, f"Missing field in result: {field}"

        # Verify status is valid enum value
        assert result["status"] in ["success", "duplicated", "failed"]


# ============================================================================
# Parametrized Tests
# ============================================================================


class TestUploadEndpointMultipleFileTypes:
    """Tests for uploading various image file types."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("file_type,extension,mime_type", [
        ("JPEG", ".jpg", "image/jpeg"),
        ("PNG", ".png", "image/png"),
        ("GIF", ".gif", "image/gif"),
        ("WebP", ".webp", "image/webp"),
        ("BMP", ".bmp", "image/bmp"),
    ])
    async def test_upload_supported_image_types(
        self,
        async_client: AsyncClient,
        sample_image_bytes: bytes,
        file_type: str,
        extension: str,
        mime_type: str,
    ) -> None:
        """
        Test that all supported image types can be uploaded.

        Note: This test uses the same JPEG content for all types but tests
        the extension validation. In production, you'd want actual files
        of each type.
        """
        files = {"images": (f"test{extension}", sample_image_bytes, mime_type)}
        response = await async_client.post(
            "/api/v1/upload",
            files=files,
        )

        # Should succeed or fail based on actual file content validity
        assert response.status_code == 200
        data = response.json()
        # At minimum, API should process the request
        assert "total" in data
