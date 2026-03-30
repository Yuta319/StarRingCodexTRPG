from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Dict, List

from .errors import IntentError


@dataclass(frozen=True)
class PlayerIntent:
    choice_id: str
    intent_type: str
    skill_keys: List[str]
    tendency_keys: List[str]
    pressure_bias: float
    impact_scale: float
    label: str

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


INTENT_MAP = {
    "observe": PlayerIntent(
        choice_id="observe",
        intent_type="observe",
        skill_keys=["stealth", "stewardship"],
        tendency_keys=["prudence"],
        pressure_bias=-8.0,
        impact_scale=0.85,
        label="現場観察",
    ),
    "speak": PlayerIntent(
        choice_id="speak",
        intent_type="speak",
        skill_keys=["diplomacy", "authority"],
        tendency_keys=["mercy"],
        pressure_bias=-4.0,
        impact_scale=1.0,
        label="対話介入",
    ),
    "speak_issuer": PlayerIntent(
        choice_id="speak_issuer",
        intent_type="speak",
        skill_keys=["diplomacy", "authority"],
        tendency_keys=["mercy"],
        pressure_bias=-4.0,
        impact_scale=1.0,
        label="代表対話",
    ),
    "inspect": PlayerIntent(
        choice_id="inspect",
        intent_type="inspect",
        skill_keys=["ritual", "stewardship"],
        tendency_keys=["prudence"],
        pressure_bias=-1.5,
        impact_scale=1.05,
        label="精査",
    ),
    "inspect_terms": PlayerIntent(
        choice_id="inspect_terms",
        intent_type="inspect",
        skill_keys=["ritual", "stewardship"],
        tendency_keys=["prudence"],
        pressure_bias=-1.5,
        impact_scale=1.05,
        label="条文精査",
    ),
    "intervene": PlayerIntent(
        choice_id="intervene",
        intent_type="intervene",
        skill_keys=["combat", "ritual", "authority"],
        tendency_keys=["ambition"],
        pressure_bias=6.0,
        impact_scale=1.3,
        label="介入",
    ),
    "trace_pressure": PlayerIntent(
        choice_id="trace_pressure",
        intent_type="intervene",
        skill_keys=["stealth", "ritual", "authority"],
        tendency_keys=["ambition"],
        pressure_bias=7.5,
        impact_scale=1.4,
        label="圧力追跡",
    ),
}


def choice_to_intent(choice_id: str) -> PlayerIntent:
    if choice_id not in INTENT_MAP:
        raise IntentError(f"Unknown choiceId: {choice_id}")
    return INTENT_MAP[choice_id]
