from __future__ import annotations

from typing import Any, Dict, List

from .errors import SchemaValidationError


def _validator_class():
    try:
        from jsonschema import Draft202012Validator
    except ModuleNotFoundError as exc:
        raise RuntimeError("jsonschema is required. Install dependencies with `py -3 -m pip install -r requirements.txt`.") from exc
    return Draft202012Validator


def validate_instance(instance: Any, schema: Dict[str, Any]) -> List[str]:
    validator_class = _validator_class()
    validator = validator_class(schema)
    errors = sorted(validator.iter_errors(instance), key=lambda err: list(err.absolute_path))
    return [f"{'/'.join(map(str, err.absolute_path)) or '<root>'}: {err.message}" for err in errors]


def validate_contracts(
    scene_packet: Dict[str, Any],
    shell_snapshot: Dict[str, Any],
    ui_event: Dict[str, Any],
    schemas: Dict[str, Dict[str, Any]],
) -> Dict[str, List[str]]:
    return {
        "scene_packet": validate_instance(scene_packet, schemas["scene_packet"]),
        "shell_snapshot": validate_instance(shell_snapshot, schemas["shell_snapshot"]),
        "ui_event": validate_instance(ui_event, schemas["ui_event"]),
    }


def ensure_contracts_valid(validation_errors: Dict[str, List[str]]) -> None:
    failing = {contract: errors for contract, errors in validation_errors.items() if errors}
    if failing:
        raise SchemaValidationError(failing)
