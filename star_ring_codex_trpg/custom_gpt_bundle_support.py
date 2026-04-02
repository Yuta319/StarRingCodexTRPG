from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from html import escape
from pathlib import Path
import json
import re
import shutil
import subprocess
from typing import Iterable


EXPECTED_OPERATIONS = {
    "getGptReadModel",
    "playChoice",
    "playFreeAction",
    "saveSession",
    "loadSession",
    "nextSession",
    "finalizeCharacter",
}


@dataclass
class CustomGptBundleReport:
    bundle_root: str
    ok: bool
    checked_files: list[str]
    operations_found: list[str]
    errors: list[str]
    warnings: list[str]

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class CustomGptEditorPastePack:
    bundle_root: str
    output_path: str
    markdown: str
    operations_found: list[str]
    starters_count: int

    def to_dict(self) -> dict:
        data = asdict(self)
        data["markdown_preview"] = self.markdown[:400]
        del data["markdown"]
        return data


@dataclass
class CustomGptEditorFieldFragments:
    bundle_root: str
    output_dir: str
    files: dict[str, str]

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class CustomGptPublishPacket:
    bundle_root: str
    output_dir: str
    files: dict[str, str]
    smoke_ok: bool | None
    archive_path: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class CustomGptPublishRelease:
    bundle_root: str
    validation: CustomGptBundleReport
    packet: CustomGptPublishPacket
    manifest_path: str

    def to_dict(self) -> dict:
        return {
            "bundle_root": self.bundle_root,
            "validation": self.validation.to_dict(),
            "packet": self.packet.to_dict(),
            "manifest_path": self.manifest_path,
        }


@dataclass
class CustomGptPublishWorkspace:
    bundle_root: str
    packet_dir: str
    local_paths: dict[str, str]
    urls: dict[str, str]
    missing: list[str]

    def to_dict(self) -> dict:
        return asdict(self)


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _read_optional_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _git_head_commit(root: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            capture_output=True,
            check=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    value = (result.stdout or "").strip()
    return value or None


def _git_is_dirty(root: Path) -> bool | None:
    try:
        result = subprocess.run(
            [
                "git",
                "-C",
                str(root),
                "status",
                "--short",
                "--",
                ".",
                ":(exclude).tmp_custom_gpt_actions_bundle/custom_gpt_actions_bundle_v1/12_gpt_publish_packet_v1",
                ":(exclude).tmp_custom_gpt_actions_bundle/custom_gpt_actions_bundle_v1/12_gpt_publish_packet_v1.zip",
            ],
            capture_output=True,
            check=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return bool((result.stdout or "").strip())


def _git_head_descriptor(root: Path) -> str | None:
    commit = _git_head_commit(root)
    if not commit:
        return None
    dirty = _git_is_dirty(root)
    if dirty:
        return f"{commit}-dirty"
    return commit


def _relative_href(base_dir: Path, target: Path) -> str:
    try:
        return target.relative_to(base_dir).as_posix()
    except ValueError:
        return target.resolve().as_uri()


def _find_operation_ids(openapi_text: str) -> list[str]:
    return re.findall(r"^\s*operationId:\s*([A-Za-z0-9_]+)\s*$", openapi_text, flags=re.MULTILINE)


def _find_first_code_fence_after_heading(markdown_text: str, heading: str) -> str:
    escaped = re.escape(heading)
    pattern = rf"^##\s+{escaped}\s*$([\s\S]*?)```(?:text)?\s*(.*?)```"
    match = re.search(pattern, markdown_text, flags=re.MULTILINE)
    return (match.group(2).strip() if match else "")


def _markdown_bullets(markdown_text: str) -> list[str]:
    return [line[2:].strip() for line in markdown_text.splitlines() if line.startswith("- ")]


def _existing_files(root: Path, relative_paths: Iterable[str]) -> list[str]:
    found = []
    for relative in relative_paths:
        candidate = root / relative
        if candidate.exists():
            found.append(relative)
    return found


def _load_bundle_parts(root: Path) -> tuple[dict, str, str, str, str]:
    builder_fields_path = root / "03_custom_gpt_builder_fields_v1.json"
    system_prompt_path = root / "01_custom_gpt_system_prompt_v1.md"
    starters_path = root / "02_custom_gpt_conversation_starters_v1.md"
    openapi_path = root / "04_openapi_pbw_actions_v1.yaml"
    input_pack_path = root / "08_gpt_editor_final_input_pack_v1.md"
    return (
        json.loads(_read_text(builder_fields_path)),
        _read_text(system_prompt_path),
        _read_text(starters_path),
        _read_text(openapi_path),
        _read_text(input_pack_path),
    )


def validate_custom_gpt_bundle(bundle_root: Path) -> CustomGptBundleReport:
    root = Path(bundle_root)
    errors: list[str] = []
    warnings: list[str] = []

    builder_fields_path = root / "03_custom_gpt_builder_fields_v1.json"
    system_prompt_path = root / "01_custom_gpt_system_prompt_v1.md"
    starters_path = root / "02_custom_gpt_conversation_starters_v1.md"
    openapi_path = root / "04_openapi_pbw_actions_v1.yaml"
    input_pack_path = root / "08_gpt_editor_final_input_pack_v1.md"

    required_files = [
        "01_custom_gpt_system_prompt_v1.md",
        "02_custom_gpt_conversation_starters_v1.md",
        "03_custom_gpt_builder_fields_v1.json",
        "04_openapi_pbw_actions_v1.yaml",
        "08_gpt_editor_final_input_pack_v1.md",
    ]
    checked_files = _existing_files(root, required_files)
    for relative in required_files:
        if not (root / relative).exists():
            errors.append(f"required file missing: {relative}")

    if errors:
        return CustomGptBundleReport(
            bundle_root=str(root),
            ok=False,
            checked_files=checked_files,
            operations_found=[],
            errors=errors,
            warnings=warnings,
        )

    builder_fields, system_prompt, starters_text, openapi_text, input_pack = _load_bundle_parts(root)

    operations_found = sorted(set(_find_operation_ids(openapi_text)))
    missing_operations = sorted(EXPECTED_OPERATIONS - set(operations_found))
    if missing_operations:
        errors.append(f"missing OpenAPI operations: {', '.join(missing_operations)}")

    server_match = re.search(r"^\s*-\s+url:\s*(\S+)\s*$", openapi_text, flags=re.MULTILINE)
    server_url = server_match.group(1).strip() if server_match else ""
    if not server_url:
        errors.append("OpenAPI servers.url is missing")
    elif "starringcodextrpg.onrender.com" not in server_url:
        warnings.append(f"OpenAPI server host is unexpected: {server_url}")

    if "guidance.openingPackage" not in system_prompt:
        errors.append("system prompt does not mention guidance.openingPackage")
    if "finalizeCharacter" not in system_prompt:
        errors.append("system prompt does not mention finalizeCharacter")
    if "guidance.characterGenesis.constraints" not in system_prompt:
        errors.append("system prompt does not mention guidance.characterGenesis.constraints")

    starters = _markdown_bullets(starters_text)
    if len(starters) < 6:
        errors.append(f"conversation starters are too few: {len(starters)}")
    starter_blob = "\n".join(starters)
    if "転生" not in starter_blob:
        warnings.append("conversation starters do not include a reincarnation prompt")
    if "自由行動" not in starter_blob:
        warnings.append("conversation starters do not include a free action prompt")
    if "再開" not in starter_blob and "続き" not in starter_blob:
        warnings.append("conversation starters do not include a resume prompt")

    instructions_file = builder_fields.get("instructions_file")
    starters_file = builder_fields.get("conversation_starters_file")
    openapi_file = builder_fields.get("actions_openapi_file")
    if instructions_file != system_prompt_path.name:
        errors.append("builder fields instructions_file does not match bundled system prompt")
    if starters_file != starters_path.name:
        errors.append("builder fields conversation_starters_file does not match bundled starters")
    if openapi_file != openapi_path.name:
        errors.append("builder fields actions_openapi_file does not match bundled OpenAPI file")

    builder_website = str(builder_fields.get("builder_profile_website") or "").strip()
    privacy_url = str(builder_fields.get("privacy_policy_url_candidate") or "").strip()
    if not builder_website.startswith("https://"):
        errors.append("builder_profile_website must be https")
    if not privacy_url.startswith("https://"):
        errors.append("privacy_policy_url_candidate must be https")

    description_block = _find_first_code_fence_after_heading(input_pack, "2. Description")
    if description_block and description_block != str(builder_fields.get("description") or "").strip():
        errors.append("builder fields description does not match input pack description")

    operations_section = _find_first_code_fence_after_heading(input_pack, "5. Actions")
    if operations_section and operations_section != server_url:
        warnings.append("input pack server URL does not match OpenAPI servers.url")

    if "guidance.openingPackage" not in input_pack:
        warnings.append("input pack does not mention guidance.openingPackage")
    if "finalizeCharacter" not in input_pack:
        errors.append("input pack does not mention finalizeCharacter")

    return CustomGptBundleReport(
        bundle_root=str(root),
        ok=not errors,
        checked_files=checked_files,
        operations_found=operations_found,
        errors=errors,
        warnings=warnings,
    )


def build_custom_gpt_editor_paste_pack(bundle_root: Path, *, output_path: Path | None = None) -> CustomGptEditorPastePack:
    root = Path(bundle_root)
    report = validate_custom_gpt_bundle(root)
    if not report.ok:
        raise ValueError("bundle validation failed: " + "; ".join(report.errors))

    builder_fields, system_prompt, starters_text, openapi_text, _input_pack = _load_bundle_parts(root)
    starters = _markdown_bullets(starters_text)
    server_match = re.search(r"^\s*-\s+url:\s*(\S+)\s*$", openapi_text, flags=re.MULTILINE)
    server_url = server_match.group(1).strip() if server_match else ""
    out_path = output_path or (root / "09_gpt_editor_paste_ready_pack_v1.md")

    markdown = "\n".join(
        [
            "# GPT Editor Paste-Ready Pack v1",
            "",
            "このファイルは GPT editor へ順番に貼るための展開済みパックです。",
            "",
            "## Name",
            "",
            "```text",
            str(builder_fields.get("name") or "").strip(),
            "```",
            "",
            "## Description",
            "",
            "```text",
            str(builder_fields.get("description") or "").strip(),
            "```",
            "",
            "## Instructions",
            "",
            "```text",
            system_prompt.strip(),
            "```",
            "",
            "## Conversation Starters",
            "",
            *(["```text", *starters, "```"] if starters else ["```text", "", "```"]),
            "",
            "## Actions",
            "",
            f"- Import file: `{(root / '04_openapi_pbw_actions_v1.yaml').resolve()}`",
            f"- Current servers.url: `{server_url}`",
            f"- Expected operations: {', '.join(report.operations_found)}",
            "",
            "## Website / Privacy",
            "",
            "```text",
            f"Builder website: {str(builder_fields.get('builder_profile_website') or '').strip()}",
            f"Privacy Policy URL: {str(builder_fields.get('privacy_policy_url_candidate') or '').strip()}",
            "```",
            "",
            "## Validation",
            "",
            "```powershell",
            "py -3 scripts\\validate_custom_gpt_bundle.py",
            "```",
            "",
            "## Notes",
            "",
            "- 新規開始では `guidance.openingPackage` を開始演出の核として優先する。",
            "- プレイヤー同意後に `finalizeCharacter` を呼ぶ。",
            "- 進行開始後は `world_json` を優先して follow-up する。",
        ]
    ).strip() + "\n"

    out_path.write_text(markdown, encoding="utf-8")
    return CustomGptEditorPastePack(
        bundle_root=str(root),
        output_path=str(out_path),
        markdown=markdown,
        operations_found=report.operations_found,
        starters_count=len(starters),
    )


def export_custom_gpt_editor_field_fragments(
    bundle_root: Path, *, output_dir: Path | None = None
) -> CustomGptEditorFieldFragments:
    root = Path(bundle_root)
    report = validate_custom_gpt_bundle(root)
    if not report.ok:
        raise ValueError("bundle validation failed: " + "; ".join(report.errors))

    builder_fields, system_prompt, starters_text, openapi_text, _input_pack = _load_bundle_parts(root)
    starters = _markdown_bullets(starters_text)
    server_match = re.search(r"^\s*-\s+url:\s*(\S+)\s*$", openapi_text, flags=re.MULTILINE)
    server_url = server_match.group(1).strip() if server_match else ""
    out_dir = output_dir or (root / "10_gpt_editor_field_fragments_v1")
    out_dir.mkdir(parents=True, exist_ok=True)

    file_map = {
        "name": out_dir / "name.txt",
        "description": out_dir / "description.txt",
        "instructions": out_dir / "instructions.txt",
        "conversation_starters": out_dir / "conversation_starters.txt",
        "builder_website": out_dir / "builder_website.txt",
        "privacy_policy_url": out_dir / "privacy_policy_url.txt",
        "actions_import_path": out_dir / "actions_import_path.txt",
        "actions_server_url": out_dir / "actions_server_url.txt",
        "manifest": out_dir / "manifest.json",
    }

    file_map["name"].write_text(str(builder_fields.get("name") or "").strip() + "\n", encoding="utf-8")
    file_map["description"].write_text(str(builder_fields.get("description") or "").strip() + "\n", encoding="utf-8")
    file_map["instructions"].write_text(system_prompt.strip() + "\n", encoding="utf-8")
    file_map["conversation_starters"].write_text("\n".join(starters).strip() + "\n", encoding="utf-8")
    file_map["builder_website"].write_text(str(builder_fields.get("builder_profile_website") or "").strip() + "\n", encoding="utf-8")
    file_map["privacy_policy_url"].write_text(str(builder_fields.get("privacy_policy_url_candidate") or "").strip() + "\n", encoding="utf-8")
    file_map["actions_import_path"].write_text(str((root / "04_openapi_pbw_actions_v1.yaml").resolve()) + "\n", encoding="utf-8")
    file_map["actions_server_url"].write_text(server_url + "\n", encoding="utf-8")

    manifest = {
        "name": str(builder_fields.get("name") or "").strip(),
        "description_file": str(file_map["description"]),
        "instructions_file": str(file_map["instructions"]),
        "conversation_starters_file": str(file_map["conversation_starters"]),
        "builder_website_file": str(file_map["builder_website"]),
        "privacy_policy_url_file": str(file_map["privacy_policy_url"]),
        "actions_import_path_file": str(file_map["actions_import_path"]),
        "actions_server_url_file": str(file_map["actions_server_url"]),
        "operations_found": report.operations_found,
    }
    file_map["manifest"].write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return CustomGptEditorFieldFragments(
        bundle_root=str(root),
        output_dir=str(out_dir),
        files={key: str(path) for key, path in file_map.items()},
    )


def export_custom_gpt_publish_dashboard(
    bundle_root: Path,
    *,
    packet_dir: Path | None = None,
    output_path: Path | None = None,
) -> Path:
    root = Path(bundle_root)
    packet_root = packet_dir or (root / "12_gpt_publish_packet_v1")
    workspace = build_custom_gpt_publish_workspace(root, packet_dir=packet_root)
    fragments_dir = Path(workspace.local_paths["field_fragments_dir"])
    dashboard_path = output_path or (packet_root / "15_gpt_publish_dashboard_v1.html")

    fields = {
        "Name": _read_optional_text(Path(fragments_dir / "name.txt")).strip(),
        "Description": _read_optional_text(Path(fragments_dir / "description.txt")).strip(),
        "Instructions": _read_optional_text(Path(fragments_dir / "instructions.txt")).strip(),
        "Conversation Starters": _read_optional_text(Path(fragments_dir / "conversation_starters.txt")).strip(),
        "Builder Website": _read_optional_text(Path(fragments_dir / "builder_website.txt")).strip(),
        "Privacy Policy URL": _read_optional_text(Path(fragments_dir / "privacy_policy_url.txt")).strip(),
        "Actions Import Path": _read_optional_text(Path(fragments_dir / "actions_import_path.txt")).strip(),
        "Actions Server URL": _read_optional_text(Path(fragments_dir / "actions_server_url.txt")).strip(),
    }
    field_items = list(fields.items())
    field_index_by_label = {label: index for index, (label, _value) in enumerate(field_items, start=1)}
    summary = _read_optional_text(Path(workspace.local_paths["summary"])).strip()
    scorecard = _read_optional_text(Path(workspace.local_paths["preview_scorecard"])).strip()
    fragments_manifest = json.loads(_read_optional_text(Path(workspace.local_paths["field_fragments_manifest"])) or "{}")
    release_manifest = json.loads(_read_optional_text(Path(workspace.local_paths["release_manifest"])) or "{}")
    live_smoke_report = json.loads(_read_optional_text(packet_root / "live_smoke_report.json") or "{}")
    initial_fixture = json.loads(_read_optional_text(Path(workspace.local_paths["packet_dir"]) / "13_gpt_preview_fixtures_v1" / "initial_gpt_read_model.json") or "{}")
    finalize_fixture = json.loads(_read_optional_text(Path(workspace.local_paths["packet_dir"]) / "13_gpt_preview_fixtures_v1" / "finalize_character_response.json") or "{}")
    choice_fixture = json.loads(_read_optional_text(Path(workspace.local_paths["packet_dir"]) / "13_gpt_preview_fixtures_v1" / "play_choice_response.json") or "{}")
    free_action_fixture = json.loads(_read_optional_text(Path(workspace.local_paths["packet_dir"]) / "13_gpt_preview_fixtures_v1" / "free_action_response.json") or "{}")
    smoke_checks = live_smoke_report.get("checks") or []
    smoke_check_rows = "".join(
        f"""
            <div class="smoke-row">
              <span>{escape(str(check.get("name") or ""))}</span>
              <strong class="smoke-row__status {'is-ok' if check.get('ok') else 'is-bad'}">
                {escape('OK' if check.get('ok') else 'NG')}
              </strong>
            </div>
        """
        for check in smoke_checks
    ) or "<p class='field__meta'>live smoke の記録はまだありません。</p>"
    smoke_detail_html = "".join(
        f"""
          <article class="smoke-detail-card">
            <div class="field__head">
              <div>
                <h3>{escape(str(check.get("name") or ""))}</h3>
                <p class="field__meta">status: {escape(str(check.get("status") if check.get("status") is not None else "none"))}</p>
              </div>
              <div class="checklist-step__actions">
                <span class="smoke-detail-card__status {'is-ok' if check.get('ok') else 'is-bad'}">{'OK' if check.get('ok') else 'NG'}</span>
                <button type="button" data-copy-target="smoke-url-{index}">Copy URL</button>
                <button type="button" data-open-url="{escape(str(check.get('url') or ''))}">Open</button>
              </div>
            </div>
            <pre id="smoke-url-{index}">{escape(str(check.get("url") or ""))}</pre>
            <pre>{escape(str(check.get("detail") or ""))}</pre>
          </article>
        """
        for index, check in enumerate(smoke_checks, start=1)
    ) or "<p class='field__meta'>live smoke の詳細はまだありません。</p>"
    actions_operations = fragments_manifest.get("operations_found") or []
    actions_operations_html = "".join(
        f"<span class=\"chip chip--operation\">{escape(str(item))}</span>" for item in actions_operations
    ) or "<span class='field__meta'>operation 情報なし</span>"
    action_examples = [
        {
            "title": "getGptReadModel",
            "note": "新規開始時に最初に読む read model",
            "summary": f"scene: {initial_fixture.get('readModel', {}).get('scene', {}).get('title', 'n/a')} / phase: {initial_fixture.get('readModel', {}).get('source', {}).get('phaseLabel', 'n/a')}",
            "href": _relative_href(packet_root, Path(workspace.local_paths["preview_initial_read_model"])),
            "copy_target": "action-example-1",
        },
        {
            "title": "finalizeCharacter",
            "note": "導入・初期装備・恩恵案を確定した後の返り値",
            "summary": f"world_json updated: {'yes' if finalize_fixture.get('playSource', {}).get('world_json') else 'no'} / promptHint: {'yes' if finalize_fixture.get('readModel', {}).get('guidance', {}).get('openingPackage', {}).get('promptHint') else 'no'}",
            "href": _relative_href(packet_root, Path(workspace.local_paths["preview_finalize_response"])),
            "copy_target": "action-example-2",
        },
        {
            "title": "playChoice",
            "note": "通常 choice 実行後の返り値",
            "summary": f"turn: {choice_fixture.get('readModel', {}).get('source', {}).get('turnInSession', 'n/a')} / scene: {choice_fixture.get('readModel', {}).get('scene', {}).get('title', 'n/a')}",
            "href": _relative_href(packet_root, Path(workspace.local_paths["preview_choice_response"])),
            "copy_target": "action-example-3",
        },
        {
            "title": "playFreeAction",
            "note": "自由行動の narrative surface を確認する返り値",
            "summary": f"turn: {free_action_fixture.get('readModel', {}).get('source', {}).get('turnInSession', 'n/a')} / scene: {free_action_fixture.get('readModel', {}).get('scene', {}).get('title', 'n/a')}",
            "href": _relative_href(packet_root, Path(workspace.local_paths["preview_free_action_response"])),
            "copy_target": "action-example-4",
        },
    ]
    action_examples_html = "".join(
        f"""
          <article class="action-card">
            <div class="field__head">
              <div>
                <h3>{escape(item["title"])}</h3>
                <p class="field__meta">{escape(item["note"])}</p>
              </div>
              <div class="checklist-step__actions">
                <button type="button" data-copy-target="{escape(item['copy_target'])}">Copy</button>
                <button type="button" data-open-url="{escape(item['href'])}">Open</button>
              </div>
            </div>
            <pre id="{escape(item['copy_target'])}">{escape(item["summary"])}</pre>
          </article>
        """
        for item in action_examples
    )
    initial_world_json = str(initial_fixture.get("playSource", {}).get("world_json") or "")
    finalized_world_json = str(finalize_fixture.get("playSource", {}).get("world_json") or initial_world_json)
    play_world_json = str(choice_fixture.get("playSource", {}).get("world_json") or finalized_world_json)
    action_request_templates = [
        {
            "title": "getGptReadModel / initial",
            "note": "新規開始の最初の read",
            "body": f"GET /api/gpt-read-model?seed={release_manifest.get('seed') or 1729}",
        },
        {
            "title": "getGptReadModel / follow-up",
            "note": "world_json を持った後の再読",
            "body": f"GET /api/gpt-read-model?world_json={finalized_world_json or '<world_json>'}",
        },
        {
            "title": "finalizeCharacter",
            "note": "導入と開始装備の案を backend へ確定させる",
            "body": json.dumps(
                {
                    "world_json": initial_world_json or "<world_json>",
                    "proposal": {
                        "openingHeadline": "公開前確認の導入",
                        "openingLines": [
                            "公開前の疎通確認として、開始導入を短く整える。"
                        ],
                    },
                },
                ensure_ascii=False,
                indent=2,
            ),
        },
        {
            "title": "playChoice",
            "note": "通常 choice を進める最小 request",
            "body": json.dumps(
                {
                    "choiceId": "observe",
                    "world_json": play_world_json or "<world_json>",
                },
                ensure_ascii=False,
                indent=2,
            ),
        },
        {
            "title": "playFreeAction",
            "note": "自由行動を進める最小 request",
            "body": json.dumps(
                {
                    "actionText": "夜中に裏帳面を盗み見たい。",
                    "world_json": play_world_json or "<world_json>",
                },
                ensure_ascii=False,
                indent=2,
            ),
        },
        {
            "title": "saveSession",
            "note": "現在の world を保存する request",
            "body": json.dumps(
                {
                    "world_json": play_world_json or "<world_json>",
                },
                ensure_ascii=False,
                indent=2,
            ),
        },
        {
            "title": "loadSession",
            "note": "saveSession 後に戻す request",
            "body": json.dumps(
                {
                    "saveId": "<saveId from saveSession>",
                },
                ensure_ascii=False,
                indent=2,
            ),
        },
        {
            "title": "nextSession",
            "note": "次のセッションへ進める request",
            "body": json.dumps(
                {
                    "world_json": play_world_json or "<world_json>",
                },
                ensure_ascii=False,
                indent=2,
            ),
        },
    ]
    action_request_templates_html = "".join(
        f"""
          <article class="action-card">
            <div class="field__head">
              <div>
                <h3>{escape(item["title"])}</h3>
                <p class="field__meta">{escape(item["note"])}</p>
              </div>
              <button type="button" data-copy-target="action-request-{index}">Copy</button>
            </div>
            <pre id="action-request-{index}">{escape(item["body"])}</pre>
          </article>
        """
        for index, item in enumerate(action_request_templates, start=1)
    )
    troubleshooting_items = [
        {
            "title": "Action import が失敗する",
            "detail": "OpenAPI の servers.url が live API を指し、Actions Setup の Server URL と一致しているか確認する。",
            "command": "py -3 scripts\\open_gpt_publish_workspace.py --copy actions_server_url",
            "copy_target": "troubleshooting-command-1",
        },
        {
            "title": "Privacy / Builder URL が弾かれる",
            "detail": "live URL が実際に開けるかを smoke で確認してから editor に貼り直す。",
            "command": "py -3 scripts\\run_custom_gpt_publish_smoke.py --retries 2 --retry-delay-seconds 1.0",
            "copy_target": "troubleshooting-command-2",
        },
        {
            "title": "Preview の新規開始が弱い",
            "detail": "`guidance.openingPackage` を使っているか、確定前の内容を『案』として扱っているかを見直す。",
            "command": "py -3 scripts\\open_gpt_publish_workspace.py --open",
            "copy_target": "troubleshooting-command-3",
        },
        {
            "title": "finalizeCharacter が失敗する",
            "detail": "request に `world_json` が入っているか、Action Examples の finalize fixture と見比べる。",
            "command": "py -3 scripts\\prepare_gpt_publish_release.py --retries 2 --retry-delay-seconds 1.0",
            "copy_target": "troubleshooting-command-4",
        },
    ]
    troubleshooting_html = "".join(
        f"""
          <article class="trouble-card">
            <div class="field__head">
              <div>
                <h3>{escape(item["title"])}</h3>
                <p class="field__meta">{escape(item["detail"])}</p>
              </div>
              <button type="button" data-copy-target="{escape(item['copy_target'])}">Copy</button>
            </div>
            <pre id="{escape(item['copy_target'])}">{escape(item["command"])}</pre>
          </article>
        """
        for item in troubleshooting_items
    )

    resource_links = [
        ("Publish Summary", Path(workspace.local_paths["summary"])),
        ("Handoff", Path(workspace.local_paths["handoff"])),
        ("Paste-Ready Pack", Path(workspace.local_paths["paste_pack"])),
        ("Field Fragments Manifest", Path(workspace.local_paths["field_fragments_manifest"])),
        ("OpenAPI Import", Path(workspace.local_paths["openapi_import"])),
        ("Preview Scorecard", Path(workspace.local_paths["preview_scorecard"])),
        ("Release Manifest", Path(workspace.local_paths["release_manifest"])),
    ]
    checklist_steps = [
        {
            "id": "open-editor",
            "title": "GPT editor を開く",
            "note": "まず editor の Configure 画面を開く",
            "copy_target": None,
            "open_url": workspace.urls["gpt_editor_url"],
        },
        {
            "id": "name",
            "title": "Name を貼る",
            "note": "短い名前だけ先に埋める",
            "copy_target": f"field-{field_index_by_label['Name']}",
            "open_url": None,
        },
        {
            "id": "description",
            "title": "Description を貼る",
            "note": "editor の説明欄を埋める",
            "copy_target": f"field-{field_index_by_label['Description']}",
            "open_url": None,
        },
        {
            "id": "instructions",
            "title": "Instructions を貼る",
            "note": "最重要。全文をそのまま使う",
            "copy_target": f"field-{field_index_by_label['Instructions']}",
            "open_url": None,
        },
        {
            "id": "starters",
            "title": "Conversation Starters を貼る",
            "note": "改行ごとに starter を登録する",
            "copy_target": f"field-{field_index_by_label['Conversation Starters']}",
            "open_url": None,
        },
        {
            "id": "import-openapi",
            "title": "OpenAPI を import する",
            "note": "Actions へ YAML を読み込む",
            "copy_target": f"field-{field_index_by_label['Actions Import Path']}",
            "open_url": _relative_href(packet_root, Path(workspace.local_paths["openapi_import"])),
        },
        {
            "id": "builder-website",
            "title": "Builder Website を貼る",
            "note": "公開プロフィール用の live URL",
            "copy_target": f"field-{field_index_by_label['Builder Website']}",
            "open_url": workspace.urls["builder_website"],
        },
        {
            "id": "privacy",
            "title": "Privacy Policy URL を貼る",
            "note": "公開前に実際に開けるか確認する",
            "copy_target": f"field-{field_index_by_label['Privacy Policy URL']}",
            "open_url": workspace.urls["privacy_policy_url"],
        },
        {
            "id": "preview",
            "title": "Preview を確認する",
            "note": "scorecard を見ながら新規開始と通常進行を試す",
            "copy_target": "scorecard-block",
            "open_url": _relative_href(packet_root, Path(workspace.local_paths["preview_scorecard"])),
        },
    ]
    checklist_steps_html = "".join(
        f"""
            <label class="checklist-step" for="check-{escape(step['id'])}">
              <div class="checklist-step__toggle">
                <input id="check-{escape(step['id'])}" type="checkbox" data-checklist-id="{escape(step['id'])}" />
              </div>
              <div class="checklist-step__body">
                <strong>{escape(step['title'])}</strong>
                <p>{escape(step['note'])}</p>
                <div class="checklist-step__actions">
                  {f'<button type="button" data-copy-target="{escape(step["copy_target"])}">Copy</button>' if step["copy_target"] else ""}
                  {f'<button type="button" data-open-url="{escape(step["open_url"])}">Open</button>' if step["open_url"] else ""}
                </div>
              </div>
            </label>
        """
        for step in checklist_steps
    )
    preview_prompt_groups = [
        {
            "title": "新規開始",
            "note": "キャラ相談から導入確定までの確認用",
            "prompts": [
                "既存キャラをこの世界へ転生させたい。導入と初期装備から一緒に決めて。",
                "見える恩恵と眠る恩寵も含めて、開始案を仕上げて。",
                "その内容で確定して。",
            ],
        },
        {
            "title": "通常進行",
            "note": "状況説明、通常行動、自由行動の確認用",
            "prompts": [
                "現在の場面で何が起きているか、まず短く説明して。",
                "この場面で選べる通常行動を比較して。",
                "自由行動として、夜中に裏帳面を盗み見たい。",
            ],
        },
        {
            "title": "保存と再開",
            "note": "セッション系 action の確認用",
            "prompts": [
                "このセッションを保存して。",
                "前回の続きから再開して。",
                "次のセッションへ進めて。",
            ],
        },
    ]
    preview_prompt_groups_html = "".join(
        f"""
          <section class="prompt-group">
            <div class="field__head">
              <div>
                <h3>{escape(group["title"])}</h3>
                <p class="field__meta">{escape(group["note"])}</p>
              </div>
            </div>
            <div class="prompt-list">
              {
                "".join(
                    f'''
                    <article class="prompt-card">
                      <pre id="preview-prompt-{group_index}-{prompt_index}">{escape(prompt)}</pre>
                      <div class="prompt-card__actions">
                        <button type="button" data-copy-target="preview-prompt-{group_index}-{prompt_index}">Copy</button>
                      </div>
                    </article>
                    '''
                    for prompt_index, prompt in enumerate(group["prompts"], start=1)
                )
              }
            </div>
          </section>
        """
        for group_index, group in enumerate(preview_prompt_groups, start=1)
    )
    troubleshooting_items = [
        {
            "title": "Action import が失敗する",
            "detail": "OpenAPI の servers.url が live API を指し、Actions Setup の Server URL と一致しているか確認する。",
            "command": "py -3 scripts\\open_gpt_publish_workspace.py --copy actions_server_url",
            "copy_target": "trouble-command-1",
        },
        {
            "title": "Privacy URL が通らない",
            "detail": "Builder Website と Privacy Policy URL が両方ともブラウザで 200 で開くことを確認する。",
            "command": "py -3 scripts\\run_custom_gpt_publish_smoke.py --retries 2 --retry-delay-seconds 1.0",
            "copy_target": "trouble-command-2",
        },
        {
            "title": "新規開始の導入が弱い",
            "detail": "`guidance.openingPackage` を使い、確定前の内容を案として扱っているか確認する。",
            "command": "py -3 scripts\\open_gpt_publish_workspace.py --open",
            "copy_target": "trouble-command-3",
        },
        {
            "title": "finalizeCharacter が失敗する",
            "detail": "request に `world_json` が入っているかを確認し、Preview Test Pack の新規開始フローから再試行する。",
            "command": "py -3 scripts\\prepare_gpt_publish_release.py --retries 2 --retry-delay-seconds 1.0",
            "copy_target": "trouble-command-4",
        },
    ]
    troubleshooting_html = "".join(
        f"""
          <article class="trouble-card">
            <div class="field__head">
              <div>
                <strong>{escape(item["title"])}</strong>
                <p>{escape(item["detail"])}</p>
              </div>
              <button type="button" data-copy-target="{escape(item['copy_target'])}">Copy</button>
            </div>
            <pre id="{escape(item['copy_target'])}">{escape(item["command"])}</pre>
          </article>
        """
        for item in troubleshooting_items
    )
    quick_commands = [
        {
            "title": "publish packet を再生成",
            "command": "py -3 scripts\\prepare_gpt_publish_release.py --retries 2 --retry-delay-seconds 1.0",
        },
        {
            "title": "workspace を開く",
            "command": "py -3 scripts\\open_gpt_publish_workspace.py --open",
        },
        {
            "title": "live smoke だけ再実行",
            "command": "py -3 scripts\\run_custom_gpt_publish_smoke.py --retries 2 --retry-delay-seconds 1.0",
        },
        {
            "title": "Instructions を clipboard へ送る",
            "command": "py -3 scripts\\open_gpt_publish_workspace.py --copy instructions",
        },
        {
            "title": "Actions import path を clipboard へ送る",
            "command": "py -3 scripts\\open_gpt_publish_workspace.py --copy actions_import_path",
        },
    ]
    quick_commands_html = "".join(
        f"""
          <article class="command-card">
            <div class="field__head">
              <div>
                <h3>{escape(item["title"])}</h3>
              </div>
              <button type="button" data-copy-target="quick-command-{index}">Copy</button>
            </div>
            <pre id="quick-command-{index}">{escape(item["command"])}</pre>
          </article>
        """
        for index, item in enumerate(quick_commands, start=1)
    )
    manifest_packet = release_manifest.get("packet") or {}
    snapshot_items = [
        ("Generated (UTC)", str(release_manifest.get("generated_at_utc") or "not written yet")),
        ("Git Commit", str(release_manifest.get("git_commit") or "unknown")),
        ("Seed", str(release_manifest.get("seed") or "1729")),
        ("Smoke Retries", str(release_manifest.get("smoke_retries") or "n/a")),
        ("Retry Delay", f"{release_manifest.get('smoke_retry_delay_seconds') or 'n/a'}s"),
        ("Smoke OK", "true" if manifest_packet.get("smoke_ok") else "false"),
        ("Packet Dir", str(manifest_packet.get("output_dir") or workspace.local_paths["packet_dir"])),
        ("Zip Archive", str(manifest_packet.get("archive_path") or workspace.local_paths["zip_archive"])),
    ]
    release_snapshot_html = "".join(
        f"""
          <div class="snapshot-row">
            <span>{escape(label)}</span>
            <strong>{escape(value)}</strong>
          </div>
        """
        for label, value in snapshot_items
    )
    validation_report = release_manifest.get("validation") or {}
    release_commit = str(release_manifest.get("git_commit") or "")
    operations_found = list(validation_report.get("operations_found") or actions_operations)
    readiness_checks = [
        {
            "title": "Bundle Validation",
            "detail": f"errors: {len(validation_report.get('errors') or [])} / warnings: {len(validation_report.get('warnings') or [])}",
            "ok": bool(validation_report.get("ok")),
            "tone": "ok" if validation_report.get("ok") else "bad",
        },
        {
            "title": "Live Smoke",
            "detail": f"latest smoke: {'OK' if live_smoke_report.get('ok') else 'NG'} / checks: {len(smoke_checks)}",
            "ok": bool(live_smoke_report.get("ok")),
            "tone": "ok" if live_smoke_report.get("ok") else "bad",
        },
        {
            "title": "Builder / Privacy URLs",
            "detail": "builder website と privacy policy URL が https で埋まっている",
            "ok": fields["Builder Website"].startswith("https://") and fields["Privacy Policy URL"].startswith("https://"),
            "tone": "ok" if fields["Builder Website"].startswith("https://") and fields["Privacy Policy URL"].startswith("https://") else "bad",
        },
        {
            "title": "Expected Operations",
            "detail": f"{len(operations_found)} / {len(EXPECTED_OPERATIONS)} operations found",
            "ok": set(operations_found) == EXPECTED_OPERATIONS,
            "tone": "ok" if set(operations_found) == EXPECTED_OPERATIONS else "bad",
        },
        {
            "title": "Git State",
            "detail": release_commit or "unknown",
            "ok": bool(release_commit and not release_commit.endswith("-dirty")),
            "tone": "ok" if release_commit and not release_commit.endswith("-dirty") else "warn",
        },
    ]
    readiness_html = "".join(
        f"""
          <article class="readiness-row">
            <span class="readiness-row__status is-{escape(item['tone'])}">{'PASS' if item['ok'] else 'CHECK' if item['tone'] == 'warn' else 'FAIL'}</span>
            <div class="readiness-row__body">
              <strong>{escape(item['title'])}</strong>
              <p>{escape(item['detail'])}</p>
            </div>
          </article>
        """
        for item in readiness_checks
    )

    html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>GPT Publish Dashboard v1</title>
  <style>
    :root {{
      color-scheme: dark;
      --bg: #120f0d;
      --panel: #1d1713;
      --panel-2: #241d18;
      --text: #f4eadc;
      --muted: #c8b69d;
      --line: rgba(223, 187, 130, 0.22);
      --accent: #dfbb82;
      --accent-2: #8bb39a;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Segoe UI", "Hiragino Sans", "Yu Gothic UI", sans-serif;
      background: radial-gradient(circle at top, #2b2119 0%, var(--bg) 48%);
      color: var(--text);
    }}
    main {{
      max-width: 1280px;
      margin: 0 auto;
      padding: 28px;
    }}
    h1, h2, h3, p {{ margin: 0; }}
    .hero, .panel {{
      background: linear-gradient(180deg, rgba(36,29,24,0.94), rgba(24,18,14,0.94));
      border: 1px solid var(--line);
      border-radius: 20px;
      padding: 20px;
      box-shadow: 0 18px 48px rgba(0,0,0,0.22);
    }}
    .hero {{
      display: grid;
      gap: 14px;
      margin-bottom: 18px;
    }}
    .hero__meta, .url-list, .resource-list {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
    }}
    .chip, .resource-link, .url-link, button {{
      border-radius: 999px;
      border: 1px solid var(--line);
      background: rgba(255,255,255,0.03);
      color: var(--text);
      padding: 8px 14px;
      text-decoration: none;
      cursor: pointer;
    }}
    .grid {{
      display: grid;
      grid-template-columns: 1.3fr 0.9fr;
      gap: 18px;
      align-items: start;
    }}
    .stack {{
      display: grid;
      gap: 18px;
    }}
    .field {{
      display: grid;
      gap: 10px;
      margin-bottom: 16px;
    }}
    .field:last-child {{ margin-bottom: 0; }}
    .field__head {{
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: center;
    }}
    .field__meta {{
      color: var(--muted);
      font-size: 13px;
    }}
    textarea {{
      width: 100%;
      min-height: 92px;
      resize: vertical;
      border-radius: 14px;
      border: 1px solid var(--line);
      background: rgba(0,0,0,0.18);
      color: var(--text);
      padding: 14px;
      font: inherit;
      line-height: 1.55;
    }}
    textarea.is-tall {{ min-height: 240px; }}
    pre {{
      white-space: pre-wrap;
      word-break: break-word;
      background: rgba(0,0,0,0.18);
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 14px;
      color: var(--text);
      line-height: 1.6;
      max-height: 320px;
      overflow: auto;
    }}
    .status {{
      color: var(--accent-2);
      font-size: 14px;
      min-height: 1.4em;
    }}
    .checklist {{
      display: grid;
      gap: 12px;
    }}
    .checklist__head {{
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: center;
      margin-bottom: 12px;
    }}
    .checklist-step {{
      display: grid;
      grid-template-columns: auto 1fr;
      gap: 12px;
      align-items: start;
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 14px;
      background: rgba(0, 0, 0, 0.12);
    }}
    .checklist-step__toggle {{
      padding-top: 2px;
    }}
    .checklist-step__toggle input {{
      width: 18px;
      height: 18px;
      accent-color: var(--accent-2);
    }}
    .checklist-step__body {{
      display: grid;
      gap: 8px;
    }}
    .checklist-step__body p {{
      color: var(--muted);
      font-size: 13px;
      line-height: 1.5;
    }}
    .checklist-step__actions {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }}
    .status-row {{
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: center;
      color: var(--muted);
      font-size: 13px;
    }}
    .actions-box {{
      display: grid;
      gap: 12px;
    }}
    .actions-box__grid {{
      display: grid;
      gap: 12px;
    }}
    .actions-box__ops {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }}
    .chip--operation {{
      background: rgba(139, 179, 154, 0.08);
      border-color: rgba(139, 179, 154, 0.28);
    }}
    .smoke-list {{
      display: grid;
      gap: 8px;
    }}
    .smoke-row {{
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: center;
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 10px 12px;
      background: rgba(0, 0, 0, 0.12);
    }}
    .smoke-row__status.is-ok {{
      color: var(--accent-2);
    }}
    .smoke-row__status.is-bad {{
      color: #d98272;
    }}
    .smoke-detail-list {{
      display: grid;
      gap: 10px;
    }}
    .smoke-detail-card {{
      display: grid;
      gap: 10px;
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 12px;
      background: rgba(0, 0, 0, 0.12);
    }}
    .smoke-detail-card__status {{
      min-width: 70px;
      text-align: center;
      border-radius: 999px;
      border: 1px solid var(--line);
      padding: 4px 10px;
      font-size: 12px;
      font-weight: 700;
    }}
    .smoke-detail-card__status.is-ok {{
      color: var(--accent-2);
      border-color: rgba(139, 179, 154, 0.32);
      background: rgba(139, 179, 154, 0.08);
    }}
    .smoke-detail-card__status.is-bad {{
      color: #d98272;
      border-color: rgba(217, 130, 114, 0.32);
      background: rgba(217, 130, 114, 0.08);
    }}
    .snapshot-list {{
      display: grid;
      gap: 8px;
    }}
    .snapshot-row {{
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: center;
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 10px 12px;
      background: rgba(0, 0, 0, 0.12);
    }}
    .snapshot-row span {{
      color: var(--muted);
      font-size: 13px;
    }}
    .snapshot-row strong {{
      text-align: right;
      font-size: 13px;
      word-break: break-word;
    }}
    .readiness-list {{
      display: grid;
      gap: 8px;
    }}
    .readiness-row {{
      display: grid;
      grid-template-columns: auto 1fr;
      gap: 12px;
      align-items: start;
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 10px 12px;
      background: rgba(0, 0, 0, 0.12);
    }}
    .readiness-row__status {{
      min-width: 52px;
      text-align: center;
      border-radius: 999px;
      border: 1px solid var(--line);
      padding: 4px 10px;
      font-size: 12px;
      font-weight: 700;
    }}
    .readiness-row__status.is-ok {{
      color: var(--accent-2);
      border-color: rgba(139, 179, 154, 0.32);
      background: rgba(139, 179, 154, 0.08);
    }}
    .readiness-row__status.is-bad {{
      color: #d98272;
      border-color: rgba(217, 130, 114, 0.32);
      background: rgba(217, 130, 114, 0.08);
    }}
    .readiness-row__status.is-warn {{
      color: #dfbb82;
      border-color: rgba(223, 187, 130, 0.32);
      background: rgba(223, 187, 130, 0.08);
    }}
    .readiness-row__body {{
      display: grid;
      gap: 4px;
    }}
    .readiness-row__body p {{
      color: var(--muted);
      font-size: 13px;
      line-height: 1.5;
    }}
    .prompt-stack {{
      display: grid;
      gap: 14px;
    }}
    .prompt-group {{
      display: grid;
      gap: 10px;
    }}
    .prompt-list {{
      display: grid;
      gap: 10px;
    }}
    .prompt-card {{
      display: grid;
      gap: 8px;
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 12px;
      background: rgba(0, 0, 0, 0.12);
    }}
    .prompt-card pre {{
      margin: 0;
      max-height: none;
    }}
    .prompt-card__actions {{
      display: flex;
      justify-content: flex-end;
    }}
    .action-stack {{
      display: grid;
      gap: 10px;
    }}
    .action-card {{
      display: grid;
      gap: 10px;
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 12px;
      background: rgba(0, 0, 0, 0.12);
    }}
    .action-card pre {{
      margin: 0;
      max-height: none;
    }}
    .trouble-list {{
      display: grid;
      gap: 10px;
    }}
    .trouble-card {{
      display: grid;
      gap: 8px;
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 12px;
      background: rgba(0, 0, 0, 0.12);
    }}
    .trouble-card p {{
      color: var(--muted);
      font-size: 13px;
      line-height: 1.5;
    }}
    .trouble-card pre {{
      margin: 0;
      max-height: none;
    }}
    .command-stack {{
      display: grid;
      gap: 10px;
    }}
    .command-card {{
      display: grid;
      gap: 8px;
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 12px;
      background: rgba(0, 0, 0, 0.12);
    }}
    .command-card pre {{
      margin: 0;
      max-height: none;
    }}
    @media (max-width: 980px) {{
      .grid {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <main>
    <section class="hero">
      <div>
        <p class="field__meta">GPT Editor Registration</p>
        <h1>{escape(fields["Name"] or "Star Ring Codex TRPG")}</h1>
      </div>
      <p>公開用 packet の断片、live URL、Preview の確認表を一枚にまとめた dashboard です。必要なテキストをその場でコピーできます。</p>
      <div class="hero__meta">
        <span class="chip">Packet: {escape(packet_root.name)}</span>
        <span class="chip">Missing: {escape(str(len(workspace.missing)))}</span>
        <span class="chip">Server: {escape(workspace.urls["actions_server_url"])}</span>
      </div>
      <div class="url-list">
        <a class="url-link" href="{escape(workspace.urls['gpt_editor_url'])}" target="_blank" rel="noreferrer">Open GPT Editor</a>
        <a class="url-link" href="{escape(workspace.urls['gpt_create_help_url'])}" target="_blank" rel="noreferrer">Create Help</a>
        <a class="url-link" href="{escape(workspace.urls['gpt_publish_help_url'])}" target="_blank" rel="noreferrer">Publish Help</a>
        <a class="url-link" href="{escape(workspace.urls['gpt_actions_help_url'])}" target="_blank" rel="noreferrer">Actions Help</a>
        <a class="url-link" href="{escape(workspace.urls['builder_website'])}" target="_blank" rel="noreferrer">Builder Website</a>
        <a class="url-link" href="{escape(workspace.urls['privacy_policy_url'])}" target="_blank" rel="noreferrer">Privacy Policy</a>
      </div>
      <div class="resource-list">
        {"".join(f'<a class="resource-link" href="{escape(_relative_href(packet_root, target))}" target="_blank" rel="noreferrer">{escape(label)}</a>' for label, target in resource_links)}
      </div>
    </section>
    <div class="grid">
      <section class="panel">
        <div class="field">
          <div class="field__head">
            <div>
              <h2>Editor Fields</h2>
              <p class="field__meta">Name / Description / Instructions / Conversation Starters / URLs</p>
            </div>
            <div class="status" id="copy-status"></div>
          </div>
        </div>
        {"".join(
            f'''
            <div class="field">
              <div class="field__head">
                <div>
                  <h3>{escape(label)}</h3>
                  <p class="field__meta">{escape(str(len(value)))} chars</p>
                </div>
                <button type="button" data-copy-target="field-{index}">Copy</button>
              </div>
              <textarea id="field-{index}" class="{'is-tall' if label in ('Instructions', 'Conversation Starters') else ''}">{escape(value)}</textarea>
            </div>
            '''
            for index, (label, value) in enumerate(fields.items(), start=1)
        )}
      </section>
      <section class="stack">
        <section class="panel">
          <div class="field">
            <div class="field__head">
              <div>
                <h2>Release Snapshot</h2>
                <p class="field__meta">この packet がどの状態から出たかを確認する</p>
              </div>
              <div class="checklist-step__actions">
                <button type="button" data-copy-target="release-snapshot-block">Copy</button>
                <button type="button" data-open-url="{escape(_relative_href(packet_root, Path(workspace.local_paths["release_manifest"])))}">Open Manifest</button>
              </div>
            </div>
            <div class="snapshot-list">
              {release_snapshot_html}
            </div>
            <pre id="release-snapshot-block">{escape(json.dumps(release_manifest, ensure_ascii=False, indent=2) if release_manifest else 'release manifest not written yet')}</pre>
          </div>
        </section>
        <section class="panel">
          <div class="field">
            <div class="field__head">
              <div>
                <h2>Readiness Checks</h2>
                <p class="field__meta">editor へ入る前の合否だけ先に見る</p>
              </div>
            </div>
            <div class="readiness-list">
              {readiness_html}
            </div>
          </div>
        </section>
        <section class="panel">
          <div class="field">
            <div class="field__head">
              <div>
                <h2>Smoke Drilldown</h2>
                <p class="field__meta">URL / status / detail を確認する</p>
              </div>
            </div>
            <div class="smoke-detail-list">
              {smoke_detail_html}
            </div>
          </div>
        </section>
        <section class="panel">
          <div class="field">
            <div class="field__head">
              <div>
                <h2>Actions Setup</h2>
                <p class="field__meta">import / server / operations / smoke</p>
              </div>
              <div class="status">{escape('live smoke: OK' if live_smoke_report.get('ok') else 'live smoke: not ready')}</div>
            </div>
          </div>
          <div class="actions-box">
            <div class="actions-box__grid">
              <div class="field">
                <div class="field__head">
                  <div>
                    <h3>Import Path</h3>
                    <p class="field__meta">Actions へ読み込む YAML</p>
                  </div>
                  <button type="button" data-copy-target="field-{field_index_by_label['Actions Import Path']}">Copy</button>
                </div>
                <textarea id="actions-import-path" rows="2">{escape(fields["Actions Import Path"])}</textarea>
              </div>
              <div class="field">
                <div class="field__head">
                  <div>
                    <h3>Server URL</h3>
                    <p class="field__meta">OpenAPI の servers.url と一致させる</p>
                  </div>
                  <button type="button" data-copy-target="field-{field_index_by_label['Actions Server URL']}">Copy</button>
                </div>
                <textarea id="actions-server-url" rows="2">{escape(fields["Actions Server URL"])}</textarea>
              </div>
            </div>
            <div class="field">
              <div class="field__head">
                <div>
                  <h3>Expected Operations</h3>
                  <p class="field__meta">import 後に揃っているか確認する</p>
                </div>
                <button type="button" data-copy-target="actions-operations-block">Copy</button>
              </div>
              <div id="actions-operations-block" class="actions-box__ops">{actions_operations_html}</div>
            </div>
            <div class="field">
              <div class="field__head">
                <div>
                  <h3>Latest Smoke</h3>
                  <p class="field__meta">直近の live smoke 状態</p>
                </div>
                <button type="button" data-copy-target="actions-smoke-block">Copy</button>
              </div>
              <div id="actions-smoke-block" class="smoke-list">{smoke_check_rows}</div>
            </div>
          </div>
          <div class="field">
            <div class="field__head">
              <div>
                <h3>Action Examples</h3>
                <p class="field__meta">fixture と見比べる時の入口</p>
              </div>
            </div>
            <div class="action-stack">
              {action_examples_html}
            </div>
          </div>
        </section>
        <section class="panel">
          <div class="field">
            <div class="field__head">
              <div>
                <h2>Action Request Templates</h2>
                <p class="field__meta">operation ごとの最小 request 例</p>
              </div>
            </div>
            <div class="action-stack">
              {action_request_templates_html}
            </div>
          </div>
        </section>
        <section class="panel">
          <div class="checklist__head">
            <div>
              <h2>Registration Checklist</h2>
              <p class="field__meta">この画面で進捗を保持します</p>
            </div>
            <button type="button" id="reset-checklist">Reset</button>
          </div>
          <div class="status-row">
            <span>進捗</span>
            <strong id="checklist-progress">0 / {len(checklist_steps)}</strong>
          </div>
          <div class="checklist">
            {checklist_steps_html}
          </div>
        </section>
        <section class="panel">
          <div class="field">
            <div class="field__head">
              <div>
                <h2>Preview Test Pack</h2>
                <p class="field__meta">登録後にそのまま打つ確認文</p>
              </div>
            </div>
            <div class="prompt-stack">
              {preview_prompt_groups_html}
            </div>
          </div>
        </section>
        <section class="panel">
          <div class="field">
            <div class="field__head">
              <div>
                <h2>Editor Troubleshooting</h2>
                <p class="field__meta">よくある失敗だけを先に見る</p>
              </div>
            </div>
            <div class="trouble-list">
              {troubleshooting_html}
            </div>
          </div>
        </section>
        <section class="panel">
          <div class="field">
            <div class="field__head">
              <div>
                <h2>Quick Commands</h2>
                <p class="field__meta">terminal 側でよく使うコマンド</p>
              </div>
            </div>
            <div class="command-stack">
              {quick_commands_html}
            </div>
          </div>
        </section>
        <section class="panel">
          <div class="field">
            <div class="field__head">
              <div>
                <h2>Publish Summary</h2>
                <p class="field__meta">packet 全体の入口</p>
              </div>
              <button type="button" data-copy-target="summary-block">Copy</button>
            </div>
            <pre id="summary-block">{escape(summary)}</pre>
          </div>
        </section>
        <section class="panel">
          <div class="field">
            <div class="field__head">
              <div>
                <h2>Preview Scorecard</h2>
                <p class="field__meta">Preview の合格ライン</p>
              </div>
              <button type="button" data-copy-target="scorecard-block">Copy</button>
            </div>
            <pre id="scorecard-block">{escape(scorecard)}</pre>
          </div>
        </section>
      </section>
    </div>
  </main>
  <script>
    const status = document.getElementById("copy-status");
    const checklistKey = "src-gpt-publish-checklist-v1::{escape(packet_root.name)}";
    async function copyFromElement(id) {{
      const element = document.getElementById(id);
      const value = element?.value ?? element?.textContent ?? "";
      await navigator.clipboard.writeText(value);
      status.textContent = "Copied: " + id;
      window.setTimeout(() => {{
        if (status.textContent === "Copied: " + id) {{
          status.textContent = "";
        }}
      }}, 1600);
    }}
    document.querySelectorAll("[data-copy-target]").forEach((button) => {{
      button.addEventListener("click", () => copyFromElement(button.dataset.copyTarget));
    }});
    document.querySelectorAll("[data-open-url]").forEach((button) => {{
      button.addEventListener("click", () => window.open(button.dataset.openUrl, "_blank", "noopener,noreferrer"));
    }});
    function loadChecklistState() {{
      try {{
        return JSON.parse(localStorage.getItem(checklistKey) || "{{}}");
      }} catch (_error) {{
        return {{}};
      }}
    }}
    function saveChecklistState(state) {{
      localStorage.setItem(checklistKey, JSON.stringify(state));
    }}
    function refreshChecklistProgress() {{
      const boxes = [...document.querySelectorAll("[data-checklist-id]")];
      const completed = boxes.filter((box) => box.checked).length;
      const progress = document.getElementById("checklist-progress");
      if (progress) {{
        progress.textContent = completed + " / " + boxes.length;
      }}
    }}
    const checklistState = loadChecklistState();
    document.querySelectorAll("[data-checklist-id]").forEach((box) => {{
      box.checked = Boolean(checklistState[box.dataset.checklistId]);
      box.addEventListener("change", () => {{
        checklistState[box.dataset.checklistId] = box.checked;
        saveChecklistState(checklistState);
        refreshChecklistProgress();
      }});
    }});
    document.getElementById("reset-checklist")?.addEventListener("click", () => {{
      document.querySelectorAll("[data-checklist-id]").forEach((box) => {{
        box.checked = false;
      }});
      saveChecklistState({{}});
      refreshChecklistProgress();
    }});
    refreshChecklistProgress();
  </script>
</body>
</html>
"""
    dashboard_path.write_text(html, encoding="utf-8")
    return dashboard_path


def export_custom_gpt_publish_packet(
    bundle_root: Path,
    *,
    output_dir: Path | None = None,
    seed: int = 1729,
    timeout_seconds: float = 20.0,
    smoke_retries: int = 2,
    smoke_retry_delay_seconds: float = 1.0,
    include_live_smoke: bool = True,
    create_zip: bool = False,
) -> CustomGptPublishPacket:
    root = Path(bundle_root)
    report = validate_custom_gpt_bundle(root)
    if not report.ok:
        raise ValueError("bundle validation failed: " + "; ".join(report.errors))

    builder_fields, _system_prompt, _starters_text, openapi_text, _input_pack = _load_bundle_parts(root)
    server_match = re.search(r"^\s*-\s+url:\s*(\S+)\s*$", openapi_text, flags=re.MULTILINE)
    server_url = server_match.group(1).strip() if server_match else ""

    out_dir = output_dir or (root / "12_gpt_publish_packet_v1")
    out_dir.mkdir(parents=True, exist_ok=True)

    paste_pack_path = out_dir / "09_gpt_editor_paste_ready_pack_v1.md"
    paste_pack = build_custom_gpt_editor_paste_pack(root, output_path=paste_pack_path)

    fragments_dir = out_dir / "10_gpt_editor_field_fragments_v1"
    fragments = export_custom_gpt_editor_field_fragments(root, output_dir=fragments_dir)

    preview_dir = out_dir / "13_gpt_preview_fixtures_v1"
    from .custom_gpt_preview_fixtures import export_custom_gpt_preview_fixtures

    preview_fixtures = export_custom_gpt_preview_fixtures(root, seed=seed, output_dir=preview_dir)

    copied_files = {
        "openapi": out_dir / "04_openapi_pbw_actions_v1.yaml",
        "builder_fields": out_dir / "03_custom_gpt_builder_fields_v1.json",
        "handoff": out_dir / "11_gpt_publish_ready_handoff_v1.md",
    }
    shutil.copy2(root / "04_openapi_pbw_actions_v1.yaml", copied_files["openapi"])
    shutil.copy2(root / "03_custom_gpt_builder_fields_v1.json", copied_files["builder_fields"])
    shutil.copy2(root / "11_gpt_publish_ready_handoff_v1.md", copied_files["handoff"])

    smoke_ok: bool | None = None
    smoke_report_path = out_dir / "live_smoke_report.json"
    if include_live_smoke:
        from .custom_gpt_publish_smoke import run_custom_gpt_publish_smoke

        smoke_report = run_custom_gpt_publish_smoke(
            root,
            seed=seed,
            timeout_seconds=timeout_seconds,
            retries=smoke_retries,
            retry_delay_seconds=smoke_retry_delay_seconds,
        )
        smoke_ok = smoke_report.ok
        smoke_report_path.write_text(json.dumps(smoke_report.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    summary_lines = [
        "# GPT Publish Packet v1",
        "",
        "このフォルダは、GPT editor へ登録する時にそのまま使う最終パケットです。",
        "",
        "## Live URLs",
        "",
        f"- Builder website: {str(builder_fields.get('builder_profile_website') or '').strip()}",
        f"- Privacy Policy URL: {str(builder_fields.get('privacy_policy_url_candidate') or '').strip()}",
        f"- Actions server: {server_url}",
        "",
        "## Official Help",
        "",
        "- Create a GPT: https://help.openai.com/en/articles/8554397-create-a-gpt",
        "- Building and publishing a GPT: https://help.openai.com/en/articles/8798878-building-and-publishing-a-gpt",
        "- Configuring actions in GPTs: https://help.openai.com/en/articles/9442513-configuring-actions-in-gpts",
        "",
        "## Included Files",
        "",
        f"- Paste-ready pack: `{paste_pack_path.name}`",
        f"- Dashboard: `15_gpt_publish_dashboard_v1.html`",
        f"- Field fragments: `{fragments_dir.name}`",
        f"- Preview fixtures: `{preview_dir.name}`",
        f"- OpenAPI import: `{copied_files['openapi'].name}`",
        f"- Builder fields: `{copied_files['builder_fields'].name}`",
        f"- Handoff note: `{copied_files['handoff'].name}`",
    ]
    if include_live_smoke:
        summary_lines.extend(
            [
                f"- Live smoke report: `{smoke_report_path.name}`",
                "",
                "## Live Smoke Status",
                "",
                f"- ok: `{str(smoke_ok).lower()}`",
                f"- seed: `{seed}`",
            ]
        )
        summary_lines.extend(
        [
            "",
            "## Recommended Start",
            "",
            "1. `11_gpt_publish_ready_handoff_v1.md` を開く",
            "2. `15_gpt_publish_dashboard_v1.html` か `09_gpt_editor_paste_ready_pack_v1.md` を開く",
            "3. `04_openapi_pbw_actions_v1.yaml` を Actions へ import する",
            "4. `13_gpt_preview_fixtures_v1` を見ながら Preview で新規開始と通常進行を確認する",
        ]
    )
    if create_zip:
        summary_lines.extend(
            [
                "",
                "## Archive",
                "",
                f"- Zip archive: `{out_dir.name}.zip`",
            ]
        )
    summary_path = out_dir / "00_publish_summary.md"
    summary_path.write_text("\n".join(summary_lines).strip() + "\n", encoding="utf-8")
    dashboard_path = export_custom_gpt_publish_dashboard(root, packet_dir=out_dir)

    files = {
        "summary": str(summary_path),
        "dashboard": str(dashboard_path),
        "paste_pack": str(paste_pack_path),
        "field_fragments_dir": str(fragments_dir),
        "preview_fixtures_dir": str(preview_dir),
        "openapi": str(copied_files["openapi"]),
        "builder_fields": str(copied_files["builder_fields"]),
        "handoff": str(copied_files["handoff"]),
    }
    if include_live_smoke:
        files["live_smoke_report"] = str(smoke_report_path)
    files.update({f"fragment_{key}": value for key, value in fragments.files.items()})
    files.update({f"preview_{key}": value for key, value in preview_fixtures.files.items()})

    archive_path: str | None = None
    if create_zip:
        archive_file = shutil.make_archive(
            base_name=str(out_dir.parent / f"{out_dir.name}"),
            format="zip",
            root_dir=str(out_dir.parent),
            base_dir=out_dir.name,
        )
        archive_path = archive_file
        files["archive_zip"] = archive_file

    return CustomGptPublishPacket(
        bundle_root=str(root),
        output_dir=str(out_dir),
        files=files,
        smoke_ok=smoke_ok,
        archive_path=archive_path,
    )


def prepare_custom_gpt_publish_release(
    bundle_root: Path,
    *,
    output_dir: Path | None = None,
    manifest_path: Path | None = None,
    seed: int = 1729,
    timeout_seconds: float = 20.0,
    smoke_retries: int = 2,
    smoke_retry_delay_seconds: float = 1.0,
    include_live_smoke: bool = True,
    create_zip: bool = True,
) -> CustomGptPublishRelease:
    root = Path(bundle_root)
    validation = validate_custom_gpt_bundle(root)
    if not validation.ok:
        raise ValueError("bundle validation failed: " + "; ".join(validation.errors))

    packet = export_custom_gpt_publish_packet(
        root,
        output_dir=output_dir,
        seed=seed,
        timeout_seconds=timeout_seconds,
        smoke_retries=smoke_retries,
        smoke_retry_delay_seconds=smoke_retry_delay_seconds,
        include_live_smoke=include_live_smoke,
        create_zip=create_zip,
    )

    builder_fields, _system_prompt, _starters_text, openapi_text, _input_pack = _load_bundle_parts(root)
    server_match = re.search(r"^\s*-\s+url:\s*(\S+)\s*$", openapi_text, flags=re.MULTILINE)
    server_url = server_match.group(1).strip() if server_match else ""
    manifest_file = manifest_path or (Path(packet.output_dir) / "14_publish_release_manifest_v1.json")
    packet.files["release_manifest"] = str(manifest_file)
    manifest = {
        "bundle_root": str(root),
        "builder_website": str(builder_fields.get("builder_profile_website") or "").strip(),
        "privacy_policy_url": str(builder_fields.get("privacy_policy_url_candidate") or "").strip(),
        "actions_server_url": server_url,
        "generated_at_utc": _utc_now_iso(),
        "git_commit": _git_head_descriptor(root),
        "seed": seed,
        "smoke_retries": smoke_retries,
        "smoke_retry_delay_seconds": smoke_retry_delay_seconds,
        "validation": validation.to_dict(),
        "packet": packet.to_dict(),
    }
    manifest_file.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    export_custom_gpt_publish_dashboard(root, packet_dir=Path(packet.output_dir))

    return CustomGptPublishRelease(
        bundle_root=str(root),
        validation=validation,
        packet=packet,
        manifest_path=str(manifest_file),
    )


def build_custom_gpt_publish_workspace(
    bundle_root: Path,
    *,
    packet_dir: Path | None = None,
) -> CustomGptPublishWorkspace:
    root = Path(bundle_root)
    builder_fields, _system_prompt, _starters_text, openapi_text, _input_pack = _load_bundle_parts(root)
    server_match = re.search(r"^\s*-\s+url:\s*(\S+)\s*$", openapi_text, flags=re.MULTILINE)
    server_url = server_match.group(1).strip() if server_match else ""
    packet_root = packet_dir or (root / "12_gpt_publish_packet_v1")

    local_paths = {
        "packet_dir": str(packet_root),
        "zip_archive": str(root / "12_gpt_publish_packet_v1.zip"),
        "summary": str(packet_root / "00_publish_summary.md"),
        "dashboard": str(packet_root / "15_gpt_publish_dashboard_v1.html"),
        "handoff": str(packet_root / "11_gpt_publish_ready_handoff_v1.md"),
        "paste_pack": str(packet_root / "09_gpt_editor_paste_ready_pack_v1.md"),
        "field_fragments_dir": str(packet_root / "10_gpt_editor_field_fragments_v1"),
        "field_fragments_manifest": str(packet_root / "10_gpt_editor_field_fragments_v1" / "manifest.json"),
        "openapi_import": str(packet_root / "04_openapi_pbw_actions_v1.yaml"),
        "preview_initial_read_model": str(packet_root / "13_gpt_preview_fixtures_v1" / "initial_gpt_read_model.json"),
        "preview_opening_package": str(packet_root / "13_gpt_preview_fixtures_v1" / "opening_package_excerpt.json"),
        "preview_finalize_response": str(packet_root / "13_gpt_preview_fixtures_v1" / "finalize_character_response.json"),
        "preview_choice_response": str(packet_root / "13_gpt_preview_fixtures_v1" / "play_choice_response.json"),
        "preview_free_action_response": str(packet_root / "13_gpt_preview_fixtures_v1" / "free_action_response.json"),
        "preview_summary": str(packet_root / "13_gpt_preview_fixtures_v1" / "00_preview_summary.md"),
        "preview_scorecard": str(packet_root / "13_gpt_preview_fixtures_v1" / "01_preview_scorecard.md"),
        "release_manifest": str(packet_root / "14_publish_release_manifest_v1.json"),
    }
    urls = {
        "gpt_editor_url": "https://chatgpt.com/gpts/editor",
        "gpt_create_help_url": "https://help.openai.com/en/articles/8554397-create-a-gpt",
        "gpt_publish_help_url": "https://help.openai.com/en/articles/8798878-building-and-publishing-a-gpt",
        "gpt_actions_help_url": "https://help.openai.com/en/articles/9442513-configuring-actions-in-gpts",
        "builder_website": str(builder_fields.get("builder_profile_website") or "").strip(),
        "privacy_policy_url": str(builder_fields.get("privacy_policy_url_candidate") or "").strip(),
        "actions_server_url": server_url,
    }
    missing = [label for label, target in local_paths.items() if label != "zip_archive" and not Path(target).exists()]

    return CustomGptPublishWorkspace(
        bundle_root=str(root),
        packet_dir=str(packet_root),
        local_paths=local_paths,
        urls=urls,
        missing=missing,
    )
