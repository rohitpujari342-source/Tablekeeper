"""Small, strict parsing helpers used at the API boundary."""

from __future__ import annotations

import json
from typing import Any

from .domain import DomainError


def malformed(message: str = "malformed request") -> DomainError:
    return DomainError(400, "malformed_request", message)


def validation(message: str = "validation failed") -> DomainError:
    return DomainError(422, "validation_failed", message)


def canonical_json(value: Any) -> str:
    """Stable parsed-JSON identity; whitespace and input key order never matter."""
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise malformed() from exc


def object_body(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise malformed("request body must be a JSON object")
    return value


def required_string(value: dict[str, Any], name: str) -> str:
    field = value.get(name)
    if not isinstance(field, str):
        raise malformed(f"{name} must be a string")
    return field


def optional_string(value: dict[str, Any], name: str) -> str | None:
    if name not in value:
        return None
    field = value[name]
    if not isinstance(field, str):
        raise malformed(f"{name} must be a string")
    return field
