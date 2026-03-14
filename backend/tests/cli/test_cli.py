"""Tests for business API CLI."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner

from app.cli import CLIError, cli


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def test_auth_login_json_output(monkeypatch: pytest.MonkeyPatch, runner: CliRunner) -> None:
    """auth login should render JSON payload when --json is enabled."""

    def fake_request(
        self: Any,
        method: str,
        path: str,
        *,
        require_auth: bool,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
        files: list[tuple[str, tuple[str, Any, str]]] | None = None,
        data: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> Any:
        assert method == "POST"
        assert path == "/auth/login"
        assert require_auth is False
        assert json_body == {"email": "demo@example.com", "password": "password123"}
        return {"access_token": "token-1", "refresh_token": "token-2"}

    monkeypatch.setattr("app.cli.ApiClient.request", fake_request)

    result = runner.invoke(
        cli,
        [
            "--json",
            "auth",
            "login",
            "--email",
            "demo@example.com",
            "--password",
            "password123",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["access_token"] == "token-1"


def test_missing_token_returns_exit_code_3(monkeypatch: pytest.MonkeyPatch, runner: CliRunner) -> None:
    """Authenticated commands should fail with exit code 3 when token is missing."""

    def fake_request(
        self: Any,
        method: str,
        path: str,
        *,
        require_auth: bool,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
        files: list[tuple[str, tuple[str, Any, str]]] | None = None,
        data: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> Any:
        if require_auth and not self.ctx.token:
            raise CLIError("Missing token. Provide --token or IMAGE_RATING_TOKEN.", 3)
        return {"ok": True}

    monkeypatch.setattr("app.cli.ApiClient.request", fake_request)

    result = runner.invoke(cli, ["images", "list"])

    assert result.exit_code == 3
    assert "Missing token" in result.output


def test_ids_file_is_supported(monkeypatch: pytest.MonkeyPatch, runner: CliRunner, tmp_path: Path) -> None:
    """Batch commands should load IDs from a file."""
    ids_file = tmp_path / "ids.txt"
    ids_file.write_text("id-1\nid-2\n", encoding="utf-8")

    called: dict[str, Any] = {}

    def fake_request(
        self: Any,
        method: str,
        path: str,
        *,
        require_auth: bool,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
        files: list[tuple[str, tuple[str, Any, str]]] | None = None,
        data: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> Any:
        called["method"] = method
        called["path"] = path
        called["json_body"] = json_body
        return {"success": True, "deleted": 2}

    monkeypatch.setattr("app.cli.ApiClient.request", fake_request)

    result = runner.invoke(
        cli,
        [
            "--token",
            "test-token",
            "images",
            "delete-batch",
            "--ids-file",
            str(ids_file),
        ],
    )

    assert result.exit_code == 0
    assert called["method"] == "POST"
    assert called["path"] == "/images/batch/delete"
    assert called["json_body"] == {"image_ids": ["id-1", "id-2"]}


def test_http_404_maps_to_exit_code_5(monkeypatch: pytest.MonkeyPatch, runner: CliRunner) -> None:
    """Command should propagate mapped API errors via CLI exit code."""

    def fake_request(
        self: Any,
        method: str,
        path: str,
        *,
        require_auth: bool,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
        files: list[tuple[str, tuple[str, Any, str]]] | None = None,
        data: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> Any:
        raise CLIError("HTTP 404: Image not found", 5)

    monkeypatch.setattr("app.cli.ApiClient.request", fake_request)

    result = runner.invoke(cli, ["--token", "t", "images", "get", "img-1"])

    assert result.exit_code == 5
    assert "HTTP 404" in result.output


def test_images_list_excludes_none_params(monkeypatch: pytest.MonkeyPatch, runner: CliRunner) -> None:
    """images list should not include None values in params."""

    captured_params: dict[str, Any] = {}

    def fake_request(
        self: Any,
        method: str,
        path: str,
        *,
        require_auth: bool,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
        files: list[tuple[str, tuple[str, Any, str]]] | None = None,
        data: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> Any:
        captured_params["params"] = params
        return {"items": [], "total": 0, "page": 1, "page_size": 20}

    monkeypatch.setattr("app.cli.ApiClient.request", fake_request)

    result = runner.invoke(cli, ["--token", "t", "images", "list"])

    assert result.exit_code == 0
    # params should only contain page and page_size, not None values
    params = captured_params["params"]
    assert params == {"page": 1, "page_size": 20}
    assert "search" not in params
    assert "date_from" not in params
    assert "date_to" not in params


def test_images_list_includes_filter_params_when_provided(monkeypatch: pytest.MonkeyPatch, runner: CliRunner) -> None:
    """images list should include filter params when values are provided."""

    captured_params: dict[str, Any] = {}

    def fake_request(
        self: Any,
        method: str,
        path: str,
        *,
        require_auth: bool,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
        files: list[tuple[str, tuple[str, Any, str]]] | None = None,
        data: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> Any:
        captured_params["params"] = params
        return {"items": [], "total": 0, "page": 1, "page_size": 20}

    monkeypatch.setattr("app.cli.ApiClient.request", fake_request)

    result = runner.invoke(
        cli,
        ["--token", "t", "images", "list", "--search", "test", "--date-from", "2024-01-01"],
    )

    assert result.exit_code == 0
    params = captured_params["params"]
    assert params["search"] == "test"
    assert params["date_from"] == "2024-01-01"
    assert "date_to" not in params


def test_ai_prompts_update_is_active_flag(monkeypatch: pytest.MonkeyPatch, runner: CliRunner) -> None:
    """ai prompts update should support bool syntax and the --inactive shortcut."""

    captured_body: dict[str, Any] = {}

    def fake_request(
        self: Any,
        method: str,
        path: str,
        *,
        require_auth: bool,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
        files: list[tuple[str, tuple[str, Any, str]]] | None = None,
        data: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> Any:
        captured_body["json_body"] = json_body
        return {"id": "prompt-1", "is_active": True}

    monkeypatch.setattr("app.cli.ApiClient.request", fake_request)

    # Backward-compatible bool syntax should keep working.
    result = runner.invoke(cli, ["ai", "prompts", "update", "prompt-1", "--is-active", "true"])
    assert result.exit_code == 0
    assert captured_body["json_body"]["is_active"] is True

    result = runner.invoke(cli, ["ai", "prompts", "update", "prompt-1", "--is-active", "false"])
    assert result.exit_code == 0
    assert captured_body["json_body"]["is_active"] is False

    # Shortcut syntax should also work.
    result = runner.invoke(cli, ["ai", "prompts", "update", "prompt-1", "--inactive"])
    assert result.exit_code == 0
    assert captured_body["json_body"]["is_active"] is False


def test_verbose_mode_outputs_request_details(monkeypatch: pytest.MonkeyPatch, runner: CliRunner) -> None:
    """Verbose mode should write diagnostics to stderr without corrupting stdout JSON."""

    import httpx

    # Mock the httpx.Client.request method to avoid making real HTTP calls
    # but still allow the verbose output code to run
    class MockResponse:
        status_code = 200
        content = b'{"items": [], "total": 0}'

        def json(self) -> dict[str, Any]:
            return {"items": [], "total": 0}

    def mock_request(self: Any, method: str, url: str, **kwargs: Any) -> MockResponse:
        return MockResponse()

    monkeypatch.setattr(httpx.Client, "request", mock_request)

    result = runner.invoke(cli, ["--json", "--verbose", "--token", "t", "images", "list"])

    assert result.exit_code == 0
    assert json.loads(result.stdout) == {"items": [], "total": 0}
    assert "[VERBOSE]" in result.stderr
    assert "GET" in result.stderr


def test_ai_prompts_update_rejects_conflicting_active_flags(
    monkeypatch: pytest.MonkeyPatch,
    runner: CliRunner,
) -> None:
    """ai prompts update should reject conflicting status flags."""

    monkeypatch.setattr("app.cli.ApiClient.request", lambda *args: {"id": "prompt-1"})

    result = runner.invoke(
        cli,
        ["ai", "prompts", "update", "prompt-1", "--is-active", "true", "--inactive"],
    )

    assert result.exit_code == 2
    assert "Use either --is-active or --inactive" in result.output


def test_mime_type_detection_for_images(monkeypatch: pytest.MonkeyPatch, runner: CliRunner, tmp_path: Path) -> None:
    """Upload should detect MIME types correctly based on file extension."""

    captured_files: dict[str, Any] = {}

    def fake_request(
        self: Any,
        method: str,
        path: str,
        *,
        require_auth: bool,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
        files: list[tuple[str, tuple[str, Any, str]]] | None = None,
        data: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> Any:
        captured_files["files"] = files
        return {"uploaded": []}

    monkeypatch.setattr("app.cli.ApiClient.request", fake_request)

    # Create test files with different extensions
    png_file = tmp_path / "test.png"
    png_file.write_bytes(b"\x89PNG\r\n\x1a\n")  # PNG magic bytes

    jpg_file = tmp_path / "test.jpg"
    jpg_file.write_bytes(b"\xff\xd8\xff")  # JPEG magic bytes

    result = runner.invoke(
        cli,
        ["--token", "t", "upload", "files", str(png_file), str(jpg_file)],
    )

    assert result.exit_code == 0
    files = captured_files["files"]
    assert len(files) == 2

    # Check MIME types
    mime_types = {f[1][0]: f[1][2] for f in files}
    assert mime_types["test.png"] == "image/png"
    assert mime_types["test.jpg"] == "image/jpeg"
