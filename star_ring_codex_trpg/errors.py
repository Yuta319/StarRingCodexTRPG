from __future__ import annotations

from typing import Dict, List


class StarRingCodexError(RuntimeError):
    pass


class AssetLoadError(StarRingCodexError):
    pass


class WorldStateError(StarRingCodexError):
    pass


class SchemaValidationError(StarRingCodexError):
    def __init__(self, errors_by_contract: Dict[str, List[str]]):
        self.errors_by_contract = errors_by_contract
        parts = []
        for contract, errors in errors_by_contract.items():
            joined = "; ".join(errors)
            parts.append(f"{contract}: {joined}")
        super().__init__("Schema validation failed: " + " | ".join(parts))


class UiRequestError(StarRingCodexError):
    pass


class IntentError(StarRingCodexError):
    pass


class FreeActionError(StarRingCodexError):
    pass
