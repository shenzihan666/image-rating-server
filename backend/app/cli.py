"""Image Rating Server business API CLI."""

from __future__ import annotations

import json
import mimetypes
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import click
import httpx

DEFAULT_BASE_URL = "http://localhost:8080"
DEFAULT_TIMEOUT_SECONDS = 30.0

# Supported image MIME types for validation
SUPPORTED_IMAGE_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
    "image/bmp",
}


@dataclass(slots=True)
class CLIContext:
    """Runtime context for CLI commands."""

    base_url: str
    json_output: bool
    timeout: float
    verbose: bool


class CLIError(click.ClickException):
    """Expected CLI error mapped to an exit code."""

    def __init__(self, message: str, exit_code: int) -> None:
        super().__init__(message)
        self.exit_code = exit_code


class ApiClient:
    """Minimal API transport wrapper."""

    def __init__(self, ctx: CLIContext) -> None:
        self.ctx = ctx

    @staticmethod
    def _normalize_base_url(base_url: str) -> str:
        stripped = base_url.rstrip("/")
        if stripped.endswith("/api/v1"):
            return stripped
        if stripped.endswith("/api"):
            return f"{stripped}/v1"
        return f"{stripped}/api/v1"

    def _headers(self) -> dict[str, str]:
        return {"Accept": "application/json"}

    def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
        files: list[tuple[str, tuple[str, Any, str]]] | None = None,
        data: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> Any:
        url = f"{self._normalize_base_url(self.ctx.base_url)}{path}"
        headers = self._headers()

        # Keep verbose diagnostics off stdout so --json remains machine-readable.
        if self.ctx.verbose:
            click.echo(f"[VERBOSE] {method} {url}", err=True)
            if params:
                click.echo(f"[VERBOSE] Params: {params}", err=True)
            if json_body:
                click.echo(
                    f"[VERBOSE] Body: {json.dumps(json_body, ensure_ascii=False)}",
                    err=True,
                )
            if data:
                click.echo(f"[VERBOSE] Form data: {data}", err=True)
            if files:
                file_names = [f[1][0] for f in files]
                click.echo(f"[VERBOSE] Files: {file_names}", err=True)

        try:
            with httpx.Client(timeout=timeout or self.ctx.timeout) as client:
                response = client.request(
                    method,
                    url,
                    headers=headers,
                    params=params,
                    json=json_body,
                    files=files,
                    data=data,
                )
        except httpx.RequestError as exc:
            raise CLIError(f"Network error: {exc}", 11) from exc

        # Keep verbose diagnostics off stdout so --json remains machine-readable.
        if self.ctx.verbose:
            click.echo(f"[VERBOSE] Response: {response.status_code}", err=True)

        if response.status_code >= 400:
            detail = _extract_error_detail(response)
            raise CLIError(
                f"HTTP {response.status_code}: {detail}",
                _map_status_to_exit_code(response.status_code),
            )

        if response.status_code == 204 or not response.content:
            return {"ok": True}

        try:
            return response.json()
        except ValueError:
            return {"raw": response.text}


def _extract_error_detail(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return response.text or "Unknown error"

    detail = payload.get("detail")
    if isinstance(detail, str):
        return detail
    if detail is not None:
        return json.dumps(detail, ensure_ascii=False)
    return json.dumps(payload, ensure_ascii=False)


def _map_status_to_exit_code(status_code: int) -> int:
    if status_code == 401:
        return 3
    if status_code == 403:
        return 4
    if status_code == 404:
        return 5
    if status_code in (400, 409, 422):
        return 6
    if status_code >= 500:
        return 10
    return 11


def _emit(ctx: CLIContext, payload: Any) -> None:
    if ctx.json_output:
        click.echo(json.dumps(payload, indent=2, ensure_ascii=False, default=str))
        return

    if isinstance(payload, list):
        if not payload:
            click.echo("No data")
            return
        if all(isinstance(item, dict) for item in payload):
            _print_table(payload)
            return
        click.echo(str(payload))
        return

    if isinstance(payload, dict):
        if "items" in payload and isinstance(payload["items"], list):
            click.echo(
                f"Total: {payload.get('total', len(payload['items']))} | "
                f"Page: {payload.get('page', '-')} | "
                f"Page Size: {payload.get('page_size', '-') }"
            )
            _print_table(payload["items"])
            return
        _print_kv(payload)
        return

    click.echo(str(payload))


def _print_table(rows: list[dict[str, Any]]) -> None:
    if not rows:
        click.echo("No data")
        return

    columns: list[str] = []
    for row in rows:
        for key in row.keys():
            if key not in columns:
                columns.append(key)

    col_widths = {col: len(col) for col in columns}
    rendered_rows: list[dict[str, str]] = []
    for row in rows:
        rendered: dict[str, str] = {}
        for col in columns:
            value = row.get(col)
            cell = _stringify(value)
            rendered[col] = cell
            col_widths[col] = max(col_widths[col], len(cell))
        rendered_rows.append(rendered)

    header = " | ".join(col.ljust(col_widths[col]) for col in columns)
    separator = "-+-".join("-" * col_widths[col] for col in columns)
    click.echo(header)
    click.echo(separator)
    for row in rendered_rows:
        click.echo(" | ".join(row[col].ljust(col_widths[col]) for col in columns))


def _print_kv(payload: dict[str, Any]) -> None:
    for key, value in payload.items():
        click.echo(f"{key}: {_stringify(value)}")


def _stringify(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def _load_ids(ids: str | None, ids_file: Path | None) -> list[str]:
    values: list[str] = []
    if ids:
        values.extend([item.strip() for item in ids.split(",") if item.strip()])
    if ids_file:
        values.extend([line.strip() for line in ids_file.read_text(encoding="utf-8").splitlines() if line.strip()])
    deduped = list(dict.fromkeys(values))
    if not deduped:
        raise CLIError("No IDs provided. Use --ids or --ids-file.", 2)
    return deduped


def _build_config_from_kv(pairs: tuple[str, ...], json_file: Path | None) -> dict[str, Any]:
    config: dict[str, Any] = {}
    if json_file:
        parsed = json.loads(json_file.read_text(encoding="utf-8"))
        if not isinstance(parsed, dict):
            raise CLIError("Config JSON must be an object.", 2)
        config.update(parsed)

    for pair in pairs:
        if "=" not in pair:
            raise CLIError(f"Invalid --set value '{pair}', expected key=value", 2)
        key, value = pair.split("=", 1)
        key = key.strip()
        if not key:
            raise CLIError(f"Invalid --set value '{pair}', key is empty", 2)
        config[key] = value
    return config


def _read_prompt_value(value: str | None, file_path: Path | None, field_name: str) -> str:
    if value and file_path:
        raise CLIError(f"Use either --{field_name} or --{field_name}-file, not both.", 2)
    if file_path:
        return file_path.read_text(encoding="utf-8")
    if value:
        return value
    raise CLIError(f"Missing required option: --{field_name} or --{field_name}-file", 2)


pass_cli_context = click.make_pass_decorator(CLIContext)


@click.group()
@click.option("--base-url", envvar="IMAGE_RATING_BASE_URL", default=DEFAULT_BASE_URL, show_default=True)
@click.option("--json", "json_output", is_flag=True, help="Output in JSON format")
@click.option("--timeout", default=DEFAULT_TIMEOUT_SECONDS, show_default=True, type=float)
@click.option("--verbose", is_flag=True, help="Enable verbose debug output")
@click.pass_context
def cli(
    click_ctx: click.Context,
    base_url: str,
    json_output: bool,
    timeout: float,
    verbose: bool,
) -> None:
    """Image Rating Server CLI."""
    click_ctx.obj = CLIContext(
        base_url=base_url,
        json_output=json_output,
        timeout=timeout,
        verbose=verbose,
    )


@cli.group()
def images() -> None:
    """Image commands."""


@images.command("list")
@click.option("--page", default=1, type=int, show_default=True)
@click.option("--page-size", default=20, type=int, show_default=True)
@click.option("--search", default=None)
@click.option("--date-from", default=None)
@click.option("--date-to", default=None)
@pass_cli_context
def images_list(
    ctx: CLIContext,
    page: int,
    page_size: int,
    search: str | None,
    date_from: str | None,
    date_to: str | None,
) -> None:
    params: dict[str, Any] = {"page": page, "page_size": page_size}
    if search:
        params["search"] = search
    if date_from:
        params["date_from"] = date_from
    if date_to:
        params["date_to"] = date_to
    payload = ApiClient(ctx).request("GET", "/images/", params=params)
    _emit(ctx, payload)


@images.command("get")
@click.argument("image_id")
@pass_cli_context
def images_get(ctx: CLIContext, image_id: str) -> None:
    payload = ApiClient(ctx).request("GET", f"/images/{image_id}")
    _emit(ctx, payload)


@images.command("analysis")
@click.argument("image_id")
@pass_cli_context
def images_analysis(ctx: CLIContext, image_id: str) -> None:
    payload = ApiClient(ctx).request("GET", f"/images/{image_id}/analysis")
    _emit(ctx, payload)


@images.command("update")
@click.argument("image_id")
@click.option("--title", default=None)
@click.option("--description", default=None)
@pass_cli_context
def images_update(
    ctx: CLIContext,
    image_id: str,
    title: str | None,
    description: str | None,
) -> None:
    body = {k: v for k, v in {"title": title, "description": description}.items() if v is not None}
    if not body:
        raise CLIError("Provide at least one field: --title or --description", 2)

    payload = ApiClient(ctx).request(
        "PATCH",
        f"/images/{image_id}",
        json_body=body,
    )
    _emit(ctx, payload)


@images.command("delete")
@click.argument("image_id")
@pass_cli_context
def images_delete(ctx: CLIContext, image_id: str) -> None:
    payload = ApiClient(ctx).request("DELETE", f"/images/{image_id}")
    _emit(ctx, payload)


@images.command("delete-batch")
@click.option("--ids", default=None, help="Comma-separated image IDs")
@click.option("--ids-file", type=click.Path(exists=True, dir_okay=False, path_type=Path), default=None)
@pass_cli_context
def images_delete_batch(ctx: CLIContext, ids: str | None, ids_file: Path | None) -> None:
    image_ids = _load_ids(ids, ids_file)
    payload = ApiClient(ctx).request(
        "POST",
        "/images/batch/delete",
        json_body={"image_ids": image_ids},
    )
    _emit(ctx, payload)


@cli.group()
def upload() -> None:
    """Upload commands."""


@upload.command("files")
@click.argument("file_paths", nargs=-1, type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--hashes", default=None, help="JSON array string of hashes")
@click.option("--hashes-file", type=click.Path(exists=True, dir_okay=False, path_type=Path), default=None)
@pass_cli_context
def upload_files(
    ctx: CLIContext,
    file_paths: tuple[Path, ...],
    hashes: str | None,
    hashes_file: Path | None,
) -> None:
    if not file_paths:
        raise CLIError("Provide at least one file path.", 2)
    if hashes and hashes_file:
        raise CLIError("Use either --hashes or --hashes-file, not both.", 2)

    hashes_payload: str | None = None
    if hashes_file:
        hashes_payload = hashes_file.read_text(encoding="utf-8")
    elif hashes:
        hashes_payload = hashes

    opened_files: list[Any] = []
    try:
        multipart_files: list[tuple[str, tuple[str, Any, str]]] = []
        for file_path in file_paths:
            handle = file_path.open("rb")
            opened_files.append(handle)
            # Use mimetypes library for better detection, fallback to jpeg
            mime_type, _ = mimetypes.guess_type(str(file_path))
            if mime_type and mime_type in SUPPORTED_IMAGE_MIME_TYPES:
                mime = mime_type
            else:
                # Fallback to jpeg if detection fails or unsupported type
                mime = "image/jpeg"
            multipart_files.append(("images", (file_path.name, handle, mime)))

        form_data = {"hashes": hashes_payload} if hashes_payload else None
        payload = ApiClient(ctx).request(
            "POST",
            "/upload",
            files=multipart_files,
            data=form_data,
            timeout=max(ctx.timeout, 120.0),
        )
    finally:
        for handle in opened_files:
            handle.close()

    _emit(ctx, payload)


@cli.group()
def ai() -> None:
    """AI commands."""


@ai.group("models")
def ai_models() -> None:
    """AI model commands."""


@ai_models.command("list")
@pass_cli_context
def ai_models_list(ctx: CLIContext) -> None:
    payload = ApiClient(ctx).request("GET", "/ai/models")
    _emit(ctx, payload)


@ai_models.command("active")
@pass_cli_context
def ai_models_active(ctx: CLIContext) -> None:
    payload = ApiClient(ctx).request("GET", "/ai/models/active")
    _emit(ctx, payload)


@ai_models.command("activate")
@click.argument("model_name")
@pass_cli_context
def ai_models_activate(ctx: CLIContext, model_name: str) -> None:
    payload = ApiClient(ctx).request(
        "POST",
        "/ai/models/active",
        json_body={"model_name": model_name},
    )
    _emit(ctx, payload)


@ai_models.command("deactivate")
@pass_cli_context
def ai_models_deactivate(ctx: CLIContext) -> None:
    payload = ApiClient(ctx).request("DELETE", "/ai/models/active")
    _emit(ctx, payload)


@ai_models.command("get")
@click.argument("model_name")
@pass_cli_context
def ai_models_get(ctx: CLIContext, model_name: str) -> None:
    payload = ApiClient(ctx).request("GET", f"/ai/models/{model_name}")
    _emit(ctx, payload)


@ai_models.group("config")
def ai_models_config() -> None:
    """AI model config commands."""


@ai_models_config.command("set")
@click.argument("model_name")
@click.option("--set", "pairs", multiple=True, help="Config pair in key=value format")
@click.option("--config-json", type=click.Path(exists=True, dir_okay=False, path_type=Path), default=None)
@pass_cli_context
def ai_models_config_set(
    ctx: CLIContext,
    model_name: str,
    pairs: tuple[str, ...],
    config_json: Path | None,
) -> None:
    config = _build_config_from_kv(pairs, config_json)
    if not config:
        raise CLIError("No config supplied. Use --set or --config-json.", 2)
    payload = ApiClient(ctx).request(
        "PUT",
        f"/ai/models/{model_name}/config",
        json_body={"config": config},
    )
    _emit(ctx, payload)


@ai_models.command("test-connection")
@click.argument("model_name")
@pass_cli_context
def ai_models_test_connection(ctx: CLIContext, model_name: str) -> None:
    payload = ApiClient(ctx).request(
        "POST",
        f"/ai/models/{model_name}/test-connection",
    )
    _emit(ctx, payload)


@ai.group("analyze")
def ai_analyze() -> None:
    """AI analysis commands."""


@ai_analyze.command("run")
@click.argument("image_id")
@click.option("--force-new", is_flag=True, default=False)
@pass_cli_context
def ai_analyze_run(ctx: CLIContext, image_id: str, force_new: bool) -> None:
    payload = ApiClient(ctx).request(
        "POST",
        f"/ai/analyze/{image_id}",
        json_body={"force_new": force_new},
    )
    _emit(ctx, payload)


@ai_analyze.command("batch")
@click.option("--ids", default=None, help="Comma-separated image IDs")
@click.option("--ids-file", type=click.Path(exists=True, dir_okay=False, path_type=Path), default=None)
@click.option("--force-new", is_flag=True, default=False)
@pass_cli_context
def ai_analyze_batch(
    ctx: CLIContext,
    ids: str | None,
    ids_file: Path | None,
    force_new: bool,
) -> None:
    image_ids = _load_ids(ids, ids_file)
    payload = ApiClient(ctx).request(
        "POST",
        "/ai/analyze/batch",
        json_body={"image_ids": image_ids, "force_new": force_new},
        timeout=max(ctx.timeout, 300.0),
    )
    _emit(ctx, payload)


@ai.group("prompts")
def ai_prompts() -> None:
    """AI prompt commands."""


@ai_prompts.command("list")
@click.option("--model-name", default=None)
@pass_cli_context
def ai_prompts_list(ctx: CLIContext, model_name: str | None) -> None:
    params = {"model_name": model_name} if model_name else None
    payload = ApiClient(ctx).request("GET", "/ai/prompts", params=params)
    _emit(ctx, payload)


@ai_prompts.command("create")
@click.option("--model-name", required=True)
@click.option("--name", required=True)
@click.option("--description", default=None)
@click.option("--is-active/--inactive", default=True)
@click.option("--system-prompt", default=None)
@click.option("--system-prompt-file", type=click.Path(exists=True, dir_okay=False, path_type=Path), default=None)
@click.option("--user-prompt", default=None)
@click.option("--user-prompt-file", type=click.Path(exists=True, dir_okay=False, path_type=Path), default=None)
@click.option("--commit-message", default=None)
@click.option("--created-by", default=None)
@pass_cli_context
def ai_prompts_create(
    ctx: CLIContext,
    model_name: str,
    name: str,
    description: str | None,
    is_active: bool,
    system_prompt: str | None,
    system_prompt_file: Path | None,
    user_prompt: str | None,
    user_prompt_file: Path | None,
    commit_message: str | None,
    created_by: str | None,
) -> None:
    system_value = _read_prompt_value(system_prompt, system_prompt_file, "system-prompt")
    user_value = _read_prompt_value(user_prompt, user_prompt_file, "user-prompt")

    payload = ApiClient(ctx).request(
        "POST",
        "/ai/prompts",
        json_body={
            "model_name": model_name,
            "name": name,
            "description": description,
            "is_active": is_active,
            "system_prompt": system_value,
            "user_prompt": user_value,
            "commit_message": commit_message,
            "created_by": created_by,
        },
    )
    _emit(ctx, payload)


@ai_prompts.command("get")
@click.argument("prompt_id")
@pass_cli_context
def ai_prompts_get(ctx: CLIContext, prompt_id: str) -> None:
    payload = ApiClient(ctx).request("GET", f"/ai/prompts/{prompt_id}")
    _emit(ctx, payload)


@ai_prompts.command("update")
@click.argument("prompt_id")
@click.option("--name", default=None)
@click.option("--description", default=None)
@click.option("--is-active", type=bool, default=None, help="Set active status (true/false)")
@click.option("--inactive", is_flag=True, help="Shortcut for --is-active false")
@pass_cli_context
def ai_prompts_update(
    ctx: CLIContext,
    prompt_id: str,
    name: str | None,
    description: str | None,
    is_active: bool | None,
    inactive: bool,
) -> None:
    if inactive and is_active is not None:
        raise CLIError("Use either --is-active or --inactive, not both.", 2)
    if inactive:
        is_active = False

    body = {
        key: value
        for key, value in {
            "name": name,
            "description": description,
            "is_active": is_active,
        }.items()
        if value is not None
    }
    if not body:
        raise CLIError("No update fields supplied.", 2)

    payload = ApiClient(ctx).request(
        "PATCH",
        f"/ai/prompts/{prompt_id}",
        json_body=body,
    )
    _emit(ctx, payload)


@ai_prompts.command("delete")
@click.argument("prompt_id")
@pass_cli_context
def ai_prompts_delete(ctx: CLIContext, prompt_id: str) -> None:
    payload = ApiClient(ctx).request("DELETE", f"/ai/prompts/{prompt_id}")
    _emit(ctx, payload)


@ai_prompts.group("versions")
def ai_prompt_versions() -> None:
    """Prompt version commands."""


@ai_prompt_versions.command("list")
@click.argument("prompt_id")
@pass_cli_context
def ai_prompt_versions_list(ctx: CLIContext, prompt_id: str) -> None:
    payload = ApiClient(ctx).request(
        "GET",
        f"/ai/prompts/{prompt_id}/versions",
    )
    _emit(ctx, payload)


@ai_prompt_versions.command("create")
@click.argument("prompt_id")
@click.option("--system-prompt", default=None)
@click.option("--system-prompt-file", type=click.Path(exists=True, dir_okay=False, path_type=Path), default=None)
@click.option("--user-prompt", default=None)
@click.option("--user-prompt-file", type=click.Path(exists=True, dir_okay=False, path_type=Path), default=None)
@click.option("--commit-message", default=None)
@click.option("--created-by", default=None)
@pass_cli_context
def ai_prompt_versions_create(
    ctx: CLIContext,
    prompt_id: str,
    system_prompt: str | None,
    system_prompt_file: Path | None,
    user_prompt: str | None,
    user_prompt_file: Path | None,
    commit_message: str | None,
    created_by: str | None,
) -> None:
    system_value = _read_prompt_value(system_prompt, system_prompt_file, "system-prompt")
    user_value = _read_prompt_value(user_prompt, user_prompt_file, "user-prompt")

    payload = ApiClient(ctx).request(
        "POST",
        f"/ai/prompts/{prompt_id}/versions",
        json_body={
            "system_prompt": system_value,
            "user_prompt": user_value,
            "commit_message": commit_message,
            "created_by": created_by,
        },
    )
    _emit(ctx, payload)


@ai_prompt_versions.command("get")
@click.argument("prompt_id")
@click.argument("version_id")
@pass_cli_context
def ai_prompt_versions_get(ctx: CLIContext, prompt_id: str, version_id: str) -> None:
    payload = ApiClient(ctx).request(
        "GET",
        f"/ai/prompts/{prompt_id}/versions/{version_id}",
    )
    _emit(ctx, payload)


def main() -> None:
    """CLI entrypoint with error-to-exit-code mapping."""
    cli()


if __name__ == "__main__":
    main()
