"""Image Rating Server – MCP (Model Context Protocol) Server.

Exposes the backend REST API as MCP tools so that AI agents like OpenClaw
can manage images, run AI analysis, and configure prompts via natural language.

The server communicates with the backend over HTTP (same as the CLI) and does
not touch the database directly.
"""

from __future__ import annotations

import json
import mimetypes
import os
from pathlib import Path
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP

DEFAULT_BASE_URL = os.environ.get("IMAGE_RATING_BASE_URL", "http://localhost:8080")
DEFAULT_TIMEOUT = float(os.environ.get("IMAGE_RATING_TIMEOUT", "30"))

SUPPORTED_IMAGE_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
    "image/bmp",
}

mcp_server = FastMCP(
    "Image Rating Server",
    instructions=(
        "AI-powered image management platform. "
        "Upload, browse, search images and run quality analysis with NIMA or Qwen3-VL models. "
        "Manage AI models, prompts, and prompt versions."
    ),
)


# ---------------------------------------------------------------------------
# HTTP transport (reuses the same pattern as the CLI)
# ---------------------------------------------------------------------------

def _api_url(path: str) -> str:
    base = DEFAULT_BASE_URL.rstrip("/")
    if not base.endswith("/api/v1"):
        base = f"{base}/api/v1"
    return f"{base}{path}"


def _request(
    method: str,
    path: str,
    *,
    params: dict[str, Any] | None = None,
    json_body: dict[str, Any] | None = None,
    files: list[tuple[str, tuple[str, Any, str]]] | None = None,
    data: dict[str, Any] | None = None,
    timeout: float | None = None,
) -> dict[str, Any]:
    url = _api_url(path)
    with httpx.Client(timeout=timeout or DEFAULT_TIMEOUT) as client:
        resp = client.request(
            method,
            url,
            headers={"Accept": "application/json"},
            params=params,
            json=json_body,
            files=files,
            data=data,
        )

    if resp.status_code >= 400:
        try:
            detail = resp.json().get("detail", resp.text)
        except Exception:
            detail = resp.text
        return {"error": True, "status_code": resp.status_code, "detail": detail}

    if resp.status_code == 204 or not resp.content:
        return {"ok": True}

    try:
        return resp.json()
    except ValueError:
        return {"raw": resp.text}


# ===================================================================
# Image tools
# ===================================================================

@mcp_server.tool()
def list_images(
    page: int = 1,
    page_size: int = 20,
    search: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> dict[str, Any]:
    """List images with pagination, search and date filters.

    Args:
        page: Page number (1-based).
        page_size: Number of images per page.
        search: Optional keyword to filter by title/description.
        date_from: Filter images created on or after this date (YYYY-MM-DD).
        date_to: Filter images created on or before this date (YYYY-MM-DD).
    """
    params: dict[str, Any] = {"page": page, "page_size": page_size}
    if search:
        params["search"] = search
    if date_from:
        params["date_from"] = date_from
    if date_to:
        params["date_to"] = date_to
    return _request("GET", "/images/", params=params)


@mcp_server.tool()
def get_image(image_id: str) -> dict[str, Any]:
    """Get detailed information about a single image.

    Args:
        image_id: The unique identifier of the image.
    """
    return _request("GET", f"/images/{image_id}")


@mcp_server.tool()
def get_image_analysis(image_id: str) -> dict[str, Any]:
    """Get the latest AI analysis result for an image.

    Args:
        image_id: The unique identifier of the image.
    """
    return _request("GET", f"/images/{image_id}/analysis")


@mcp_server.tool()
def update_image(
    image_id: str,
    title: str | None = None,
    description: str | None = None,
) -> dict[str, Any]:
    """Update an image's title and/or description.

    Args:
        image_id: The unique identifier of the image.
        title: New title for the image.
        description: New description for the image.
    """
    body = {k: v for k, v in {"title": title, "description": description}.items() if v is not None}
    if not body:
        return {"error": True, "detail": "Provide at least one of: title, description"}
    return _request("PATCH", f"/images/{image_id}", json_body=body)


@mcp_server.tool()
def delete_image(image_id: str) -> dict[str, Any]:
    """Delete an image and its associated file.

    Args:
        image_id: The unique identifier of the image to delete.
    """
    return _request("DELETE", f"/images/{image_id}")


@mcp_server.tool()
def delete_images_batch(image_ids: list[str]) -> dict[str, Any]:
    """Delete multiple images at once.

    Args:
        image_ids: List of image IDs to delete.
    """
    return _request("POST", "/images/batch/delete", json_body={"image_ids": image_ids})


# ===================================================================
# Upload tools
# ===================================================================

@mcp_server.tool()
def upload_images(file_paths: list[str], auto_analyze: bool = False) -> dict[str, Any]:
    """Upload one or more image files to the server.

    Args:
        file_paths: List of absolute file paths of images to upload.
        auto_analyze: If true, automatically run AI analysis after upload.
    """
    opened_files: list[Any] = []
    try:
        multipart_files: list[tuple[str, tuple[str, Any, str]]] = []
        for fp in file_paths:
            path = Path(fp)
            if not path.is_file():
                return {"error": True, "detail": f"File not found: {fp}"}
            handle = path.open("rb")
            opened_files.append(handle)
            mime_type, _ = mimetypes.guess_type(str(path))
            if not mime_type or mime_type not in SUPPORTED_IMAGE_MIME_TYPES:
                mime_type = "image/jpeg"
            multipart_files.append(("images", (path.name, handle, mime_type)))

        form_data: dict[str, Any] | None = None
        if auto_analyze:
            form_data = {"auto_analyze": "true"}

        return _request(
            "POST",
            "/upload",
            files=multipart_files,
            data=form_data,
            timeout=max(DEFAULT_TIMEOUT, 120.0),
        )
    finally:
        for handle in opened_files:
            handle.close()


# ===================================================================
# AI model tools
# ===================================================================

@mcp_server.tool()
def list_ai_models() -> dict[str, Any]:
    """List all available AI models and their status."""
    return _request("GET", "/ai/models")


@mcp_server.tool()
def get_active_model() -> dict[str, Any]:
    """Get the currently active AI model."""
    return _request("GET", "/ai/models/active")


@mcp_server.tool()
def activate_model(model_name: str) -> dict[str, Any]:
    """Activate an AI model for analysis. Only one model can be active at a time.

    Args:
        model_name: Name of the model to activate (e.g. "nima", "qwen3-vl").
    """
    return _request("POST", "/ai/models/active", json_body={"model_name": model_name})


@mcp_server.tool()
def deactivate_model() -> dict[str, Any]:
    """Deactivate the currently active AI model."""
    return _request("DELETE", "/ai/models/active")


@mcp_server.tool()
def get_model_detail(model_name: str) -> dict[str, Any]:
    """Get detailed information and configuration fields for an AI model.

    Args:
        model_name: Name of the model (e.g. "nima", "qwen3-vl").
    """
    return _request("GET", f"/ai/models/{model_name}")


@mcp_server.tool()
def update_model_config(model_name: str, config: dict[str, str]) -> dict[str, Any]:
    """Update configuration for an AI model.

    Args:
        model_name: Name of the model to configure.
        config: Key-value pairs of configuration options
                (e.g. {"api_key": "sk-...", "base_url": "https://..."}).
    """
    return _request("PUT", f"/ai/models/{model_name}/config", json_body={"config": config})


@mcp_server.tool()
def test_model_connection(model_name: str) -> dict[str, Any]:
    """Test the connection to an AI model to verify configuration.

    Args:
        model_name: Name of the model to test.
    """
    return _request("POST", f"/ai/models/{model_name}/test-connection")


# ===================================================================
# AI analysis tools
# ===================================================================

@mcp_server.tool()
def analyze_image(image_id: str, force_new: bool = False) -> dict[str, Any]:
    """Run AI analysis on a single image using the currently active model.

    Args:
        image_id: The unique identifier of the image to analyze.
        force_new: If true, re-run analysis even if cached results exist.
    """
    return _request(
        "POST",
        f"/ai/analyze/{image_id}",
        json_body={"force_new": force_new},
    )


@mcp_server.tool()
def batch_analyze_images(image_ids: list[str], force_new: bool = False) -> dict[str, Any]:
    """Run AI analysis on multiple images in batch.

    Args:
        image_ids: List of image IDs to analyze.
        force_new: If true, re-run analysis even if cached results exist.
    """
    return _request(
        "POST",
        "/ai/analyze/batch",
        json_body={"image_ids": image_ids, "force_new": force_new},
        timeout=max(DEFAULT_TIMEOUT, 300.0),
    )


# ===================================================================
# AI prompt tools
# ===================================================================

@mcp_server.tool()
def list_prompts(model_name: str | None = None) -> dict[str, Any]:
    """List AI prompts, optionally filtered by model name.

    Args:
        model_name: Filter prompts for a specific model (e.g. "qwen3-vl").
    """
    params = {"model_name": model_name} if model_name else None
    return _request("GET", "/ai/prompts", params=params)


@mcp_server.tool()
def get_prompt(prompt_id: str) -> dict[str, Any]:
    """Get detailed information about an AI prompt.

    Args:
        prompt_id: The unique identifier of the prompt.
    """
    return _request("GET", f"/ai/prompts/{prompt_id}")


@mcp_server.tool()
def create_prompt(
    model_name: str,
    name: str,
    system_prompt: str,
    user_prompt: str,
    description: str | None = None,
    is_active: bool = True,
    commit_message: str | None = None,
    created_by: str | None = None,
) -> dict[str, Any]:
    """Create a new AI prompt with an initial version.

    Args:
        model_name: Target model name (e.g. "qwen3-vl").
        name: Human-readable name for the prompt.
        system_prompt: The system prompt text.
        user_prompt: The user prompt template text.
        description: Optional description of the prompt's purpose.
        is_active: Whether this prompt should be active immediately.
        commit_message: Optional message describing this version.
        created_by: Optional author name.
    """
    return _request(
        "POST",
        "/ai/prompts",
        json_body={
            "model_name": model_name,
            "name": name,
            "description": description,
            "is_active": is_active,
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "commit_message": commit_message,
            "created_by": created_by,
        },
    )


@mcp_server.tool()
def update_prompt(
    prompt_id: str,
    name: str | None = None,
    description: str | None = None,
    is_active: bool | None = None,
) -> dict[str, Any]:
    """Update an AI prompt's metadata (name, description, active status).

    Args:
        prompt_id: The unique identifier of the prompt to update.
        name: New name for the prompt.
        description: New description.
        is_active: Set to true to activate or false to deactivate.
    """
    body = {k: v for k, v in {"name": name, "description": description, "is_active": is_active}.items() if v is not None}
    if not body:
        return {"error": True, "detail": "Provide at least one field to update."}
    return _request("PATCH", f"/ai/prompts/{prompt_id}", json_body=body)


@mcp_server.tool()
def delete_prompt(prompt_id: str) -> dict[str, Any]:
    """Delete an AI prompt and all its versions.

    Args:
        prompt_id: The unique identifier of the prompt to delete.
    """
    return _request("DELETE", f"/ai/prompts/{prompt_id}")


@mcp_server.tool()
def list_prompt_versions(prompt_id: str) -> dict[str, Any]:
    """List all versions of an AI prompt.

    Args:
        prompt_id: The unique identifier of the prompt.
    """
    return _request("GET", f"/ai/prompts/{prompt_id}/versions")


@mcp_server.tool()
def get_prompt_version(prompt_id: str, version_id: str) -> dict[str, Any]:
    """Get a specific version of an AI prompt with full prompt text.

    Args:
        prompt_id: The unique identifier of the prompt.
        version_id: The unique identifier of the version.
    """
    return _request("GET", f"/ai/prompts/{prompt_id}/versions/{version_id}")


@mcp_server.tool()
def create_prompt_version(
    prompt_id: str,
    system_prompt: str,
    user_prompt: str,
    commit_message: str | None = None,
    created_by: str | None = None,
) -> dict[str, Any]:
    """Create a new version of an existing AI prompt.

    Args:
        prompt_id: The unique identifier of the prompt.
        system_prompt: The new system prompt text.
        user_prompt: The new user prompt template text.
        commit_message: Optional message describing changes in this version.
        created_by: Optional author name.
    """
    return _request(
        "POST",
        f"/ai/prompts/{prompt_id}/versions",
        json_body={
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "commit_message": commit_message,
            "created_by": created_by,
        },
    )


# ===================================================================
# Health check (useful for agents to verify the server is reachable)
# ===================================================================

@mcp_server.tool()
def health_check() -> dict[str, Any]:
    """Check if the Image Rating Server backend is running and reachable."""
    base = DEFAULT_BASE_URL.rstrip("/")
    with httpx.Client(timeout=10) as client:
        try:
            resp = client.get(f"{base}/health")
            if resp.status_code == 200:
                return {"status": "healthy", **resp.json()}
            return {"status": "unhealthy", "status_code": resp.status_code}
        except httpx.RequestError as exc:
            return {"status": "unreachable", "error": str(exc)}


# ===================================================================
# Entrypoint
# ===================================================================

def main() -> None:
    """Run the MCP server (stdio transport for local AI agent integration)."""
    mcp_server.run()


if __name__ == "__main__":
    main()
