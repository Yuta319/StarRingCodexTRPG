from __future__ import annotations

import re
from typing import Iterable


FORBIDDEN_LITERALS = (
    "distortion",
    "breach_risk",
    "sealIntegrity",
    "cycleDistortion",
    "apotheosisFlux",
    "successionPressure",
    "divineWarPressure",
    "partial_success",
    "world state",
    "scene packet",
    "play cycle",
    "named cast",
)

_SUSPICIOUS_NOUN_CHAIN_RE = re.compile(r"[一-龥ァ-ヶ]{12,}")
_TERMINAL_RE = re.compile(r"[。！？]$")


def _normalize(text: object) -> str:
    return str(text or "").strip()


def collect_copy_issues(text: object, kind: str = "general") -> list[str]:
    normalized = _normalize(text)
    if not normalized:
        return ["empty_text"]

    issues: list[str] = []
    lowered = normalized.lower()
    for literal in FORBIDDEN_LITERALS:
        if literal.lower() in lowered:
            issues.append(f"forbidden_literal:{literal}")

    if kind == "status" and len(normalized) > 24:
        issues.append("status_too_long")
    if kind == "ui" and len(normalized) > 42:
        issues.append("ui_text_too_long")
    if kind in {"explanation", "afterglow"} and len(normalized) > 70 and not _TERMINAL_RE.search(normalized):
        issues.append("long_sentence_without_terminal")
    if _SUSPICIOUS_NOUN_CHAIN_RE.search(normalized) and not re.search(r"[はがをにでとへも、。]", normalized):
        issues.append("suspicious_noun_chain")
    return issues


def ensure_copy_quality(text: object, kind: str = "general") -> str:
    normalized = _normalize(text)
    issues = collect_copy_issues(normalized, kind=kind)
    if issues:
        issue_text = ", ".join(issues)
        raise ValueError(f"Copy quality check failed for {kind}: {issue_text}: {normalized}")
    return normalized


def first_copy_issue(texts: Iterable[object], kind: str = "general") -> str | None:
    for text in texts:
        issues = collect_copy_issues(text, kind=kind)
        if issues:
            return ", ".join(issues)
    return None
