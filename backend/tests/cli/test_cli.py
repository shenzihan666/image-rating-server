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
