"""Domain value objects shared by the Stage 1 HTTP layer."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DomainError(Exception):
    """An expected client-facing failure, kept independent from HTTP."""

    status: int
    code: str
    message: str

    def error_body(self) -> dict[str, dict[str, str]]:
        return {"error": {"code": self.code, "message": self.message}}


@dataclass(frozen=True)
class IdempotencyReceipt:
    user_id: str
    method: str
    path: str
    key: str
    request_json: str
    status: int
    response: dict[str, Any]

    @property
    def identity(self) -> tuple[str, str, str, str]:
        return (self.user_id, self.method, self.path, self.key)

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "method": self.method,
            "path": self.path,
            "key": self.key,
            "request_json": self.request_json,
            "status": self.status,
            "response": self.response,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "IdempotencyReceipt":
        required = {"user_id", "method", "path", "key", "request_json", "status", "response"}
        if set(value) != required or not isinstance(value["response"], dict):
            raise DomainError(422, "validation_failed", "invalid idempotency receipt")
        if not all(isinstance(value[name], str) for name in required - {"status", "response"}):
            raise DomainError(422, "validation_failed", "invalid idempotency receipt")
        if not isinstance(value["status"], int):
            raise DomainError(422, "validation_failed", "invalid idempotency receipt")
        return cls(**value)
