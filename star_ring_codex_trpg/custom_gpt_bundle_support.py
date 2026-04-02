from __future__ import annotations

from dataclasses import asdict, dataclass
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


def export_custom_gpt_publish_packet(
    bundle_root: Path,
    *,
    output_dir: Path | None = None,
    seed: int = 1729,
    timeout_seconds: float = 20.0,
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

        smoke_report = run_custom_gpt_publish_smoke(root, seed=seed, timeout_seconds=timeout_seconds)
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
        "## Included Files",
        "",
        f"- Paste-ready pack: `{paste_pack_path.name}`",
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
            "2. `09_gpt_editor_paste_ready_pack_v1.md` か `10_gpt_editor_field_fragments_v1` を使って GPT editor に貼る",
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

    files = {
        "summary": str(summary_path),
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
        "handoff": str(packet_root / "11_gpt_publish_ready_handoff_v1.md"),
        "paste_pack": str(packet_root / "09_gpt_editor_paste_ready_pack_v1.md"),
        "field_fragments_dir": str(packet_root / "10_gpt_editor_field_fragments_v1"),
        "field_fragments_manifest": str(packet_root / "10_gpt_editor_field_fragments_v1" / "manifest.json"),
        "openapi_import": str(packet_root / "04_openapi_pbw_actions_v1.yaml"),
        "preview_scorecard": str(packet_root / "13_gpt_preview_fixtures_v1" / "01_preview_scorecard.md"),
        "release_manifest": str(packet_root / "14_publish_release_manifest_v1.json"),
    }
    urls = {
        "builder_website": str(builder_fields.get("builder_profile_website") or "").strip(),
        "privacy_policy_url": str(builder_fields.get("privacy_policy_url_candidate") or "").strip(),
        "actions_server_url": server_url,
    }
    missing = [label for label, target in local_paths.items() if not Path(target).exists()]

    return CustomGptPublishWorkspace(
        bundle_root=str(root),
        packet_dir=str(packet_root),
        local_paths=local_paths,
        urls=urls,
        missing=missing,
    )
