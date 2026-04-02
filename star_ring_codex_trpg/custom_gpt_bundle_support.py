from __future__ import annotations

from dataclasses import asdict, dataclass
from html import escape
from pathlib import Path
import json
import re
import shutil
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
    live_smoke_report = json.loads(_read_optional_text(packet_root / "live_smoke_report.json") or "{}")
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
    actions_operations = fragments_manifest.get("operations_found") or []
    actions_operations_html = "".join(
        f"<span class=\"chip chip--operation\">{escape(str(item))}</span>" for item in actions_operations
    ) or "<span class='field__meta'>operation 情報なし</span>"

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
        "seed": seed,
        "smoke_retries": smoke_retries,
        "smoke_retry_delay_seconds": smoke_retry_delay_seconds,
        "validation": validation.to_dict(),
        "packet": packet.to_dict(),
    }
    manifest_file.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

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
