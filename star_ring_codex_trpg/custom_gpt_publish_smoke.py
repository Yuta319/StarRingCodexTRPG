from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import json
import socket
import time
import urllib.error
import urllib.parse
import urllib.request

from .custom_gpt_bundle_support import validate_custom_gpt_bundle


@dataclass
class PublishTargetSet:
    bundle_root: str
    builder_website: str
    privacy_policy_url: str
    api_server_url: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class PublishCheckResult:
    name: str
    ok: bool
    status: int | None
    url: str
    detail: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class CustomGptPublishSmokeReport:
    bundle_root: str
    ok: bool
    seed: int
    targets: dict
    checks: list[dict]
    errors: list[str]

    def to_dict(self) -> dict:
        return asdict(self)


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_custom_gpt_publish_targets(bundle_root: Path) -> PublishTargetSet:
    root = Path(bundle_root)
    report = validate_custom_gpt_bundle(root)
    if not report.ok:
        raise ValueError("bundle validation failed: " + "; ".join(report.errors))
    builder_fields = json.loads(_read_text(root / "03_custom_gpt_builder_fields_v1.json"))
    openapi_text = _read_text(root / "04_openapi_pbw_actions_v1.yaml")
    api_server_url = ""
    for line in openapi_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("- url:"):
            api_server_url = stripped.split(":", 1)[1].strip()
            break
    if not api_server_url:
        raise ValueError("OpenAPI servers.url is missing")
    return PublishTargetSet(
        bundle_root=str(root),
        builder_website=str(builder_fields.get("builder_profile_website") or "").strip(),
        privacy_policy_url=str(builder_fields.get("privacy_policy_url_candidate") or "").strip(),
        api_server_url=api_server_url,
    )


def _http_request(url: str, *, method: str = "GET", body: dict | None = None, timeout_seconds: float = 20.0) -> tuple[int | None, str, object]:
    data = None
    headers = {}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            raw = response.read().decode("utf-8", errors="replace")
            content_type = response.headers.get("Content-Type", "")
            if "application/json" in content_type:
                try:
                    return response.status, raw, json.loads(raw)
                except json.JSONDecodeError:
                    return response.status, raw, raw
            return response.status, raw, raw
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            payload = raw
        return exc.code, raw, payload
    except (urllib.error.URLError, TimeoutError, socket.timeout) as exc:
        return None, str(exc), {"error": str(exc)}


def _json_detail(payload: object, *keys: str) -> str:
    current = payload
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return ""
        current = current[key]
    if isinstance(current, (str, int, float, bool)) or current is None:
        return str(current)
    return json.dumps(current, ensure_ascii=False)


def _status_ok(status: int | None) -> bool:
    return isinstance(status, int) and 200 <= status < 300


def _is_retryable_status(status: int | None) -> bool:
    return status is None or status in {502, 503, 504}


def _http_request_with_retries(
    url: str,
    *,
    method: str = "GET",
    body: dict | None = None,
    timeout_seconds: float = 20.0,
    retries: int = 2,
    retry_delay_seconds: float = 1.0,
) -> tuple[int | None, str, object]:
    attempts = max(0, retries) + 1
    last_result: tuple[int | None, str, object] = (None, "", {"error": "request not attempted"})
    for attempt in range(attempts):
        last_result = _http_request(url, method=method, body=body, timeout_seconds=timeout_seconds)
        status, _raw, _payload = last_result
        if not _is_retryable_status(status) or attempt == attempts - 1:
            return last_result
        if retry_delay_seconds > 0:
            time.sleep(retry_delay_seconds)
    return last_result


def run_custom_gpt_publish_smoke(
    bundle_root: Path,
    *,
    seed: int = 1729,
    timeout_seconds: float = 20.0,
    retries: int = 2,
    retry_delay_seconds: float = 1.0,
) -> CustomGptPublishSmokeReport:
    targets = load_custom_gpt_publish_targets(bundle_root)
    checks: list[PublishCheckResult] = []
    errors: list[str] = []

    website_status, website_raw, _website_payload = _http_request_with_retries(
        targets.builder_website,
        timeout_seconds=timeout_seconds,
        retries=retries,
        retry_delay_seconds=retry_delay_seconds,
    )
    checks.append(
        PublishCheckResult(
            name="builder_website",
            ok=_status_ok(website_status) and "<html" in website_raw.lower(),
            status=website_status,
            url=targets.builder_website,
            detail="html ok" if "<html" in website_raw.lower() else website_raw or "non-html response",
        )
    )

    privacy_status, privacy_raw, _privacy_payload = _http_request_with_retries(
        targets.privacy_policy_url,
        timeout_seconds=timeout_seconds,
        retries=retries,
        retry_delay_seconds=retry_delay_seconds,
    )
    checks.append(
        PublishCheckResult(
            name="privacy_policy",
            ok=_status_ok(privacy_status) and "<html" in privacy_raw.lower(),
            status=privacy_status,
            url=targets.privacy_policy_url,
            detail="html ok" if "<html" in privacy_raw.lower() else privacy_raw or "non-html response",
        )
    )

    api_base = targets.api_server_url.rstrip("/")
    health_status, _health_raw, health_payload = _http_request_with_retries(
        f"{api_base}/health",
        timeout_seconds=timeout_seconds,
        retries=retries,
        retry_delay_seconds=retry_delay_seconds,
    )
    checks.append(
        PublishCheckResult(
            name="api_health",
            ok=_status_ok(health_status) and bool(_json_detail(health_payload, "ok") == "True" or _json_detail(health_payload, "ok") == "true"),
            status=health_status,
            url=f"{api_base}/health",
            detail=_json_detail(health_payload, "ok") or _health_raw or "missing ok flag",
        )
    )

    snapshot_url = f"{api_base}/api/front/snapshot?{urllib.parse.urlencode({'seed': seed})}"
    snapshot_status, _snapshot_raw, snapshot_payload = _http_request_with_retries(
        snapshot_url,
        timeout_seconds=timeout_seconds,
        retries=retries,
        retry_delay_seconds=retry_delay_seconds,
    )
    world_json = _json_detail(snapshot_payload, "playSource", "world_json")
    checks.append(
        PublishCheckResult(
            name="front_snapshot",
            ok=_status_ok(snapshot_status) and bool(world_json),
            status=snapshot_status,
            url=snapshot_url,
            detail="world_json returned" if world_json else (_snapshot_raw or "playSource.world_json missing"),
        )
    )

    read_model_url = f"{api_base}/api/gpt-read-model?{urllib.parse.urlencode({'seed': seed})}"
    read_status, _read_raw, read_payload = _http_request_with_retries(
        read_model_url,
        timeout_seconds=timeout_seconds,
        retries=retries,
        retry_delay_seconds=retry_delay_seconds,
    )
    opening_package_hint = _json_detail(read_payload, "readModel", "guidance", "openingPackage", "promptHint")
    checks.append(
        PublishCheckResult(
            name="gpt_read_model",
            ok=_status_ok(read_status) and bool(opening_package_hint),
            status=read_status,
            url=read_model_url,
            detail="openingPackage.promptHint present" if opening_package_hint else (_read_raw or "openingPackage.promptHint missing"),
        )
    )

    finalize_url = f"{api_base}/api/gpt/finalize-character"
    finalize_body = {
        "world_json": world_json,
        "proposal": {
            "openingHeadline": "公開前確認の導入",
            "openingLines": ["公開前の疎通確認として、開始導入を短く整える。"],
        },
    }
    finalize_status, _finalize_raw, finalize_payload = _http_request_with_retries(
        finalize_url,
        method="POST",
        body=finalize_body,
        timeout_seconds=timeout_seconds,
        retries=retries,
        retry_delay_seconds=retry_delay_seconds,
    )
    finalize_hint = _json_detail(finalize_payload, "readModel", "guidance", "openingPackage", "promptHint")
    checks.append(
        PublishCheckResult(
            name="gpt_finalize_character",
            ok=_status_ok(finalize_status) and bool(finalize_hint),
            status=finalize_status,
            url=finalize_url,
            detail="readModel updated" if finalize_hint else (_finalize_raw or "readModel/openingPackage missing after finalize"),
        )
    )

    for check in checks:
        if not check.ok:
            errors.append(f"{check.name} failed: {check.detail}")

    return CustomGptPublishSmokeReport(
        bundle_root=str(bundle_root),
        ok=not errors,
        seed=seed,
        targets=targets.to_dict(),
        checks=[item.to_dict() for item in checks],
        errors=errors,
    )
