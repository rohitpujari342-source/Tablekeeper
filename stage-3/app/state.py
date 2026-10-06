"""Single-process, lock-protected transactional state for Stage 1."""

from __future__ import annotations

import asyncio
import copy
import inspect
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, TypeVar

from .domain import DomainError, IdempotencyReceipt
from .validation import canonical_json


T = TypeVar("T")
Mutation = Callable[["ServiceState"], T | Awaitable[T]]


@dataclass
class ServiceState:
    users: dict[str, dict[str, Any]] = field(default_factory=dict)
    tokens: dict[str, str] = field(default_factory=dict)
    restaurants: dict[str, dict[str, Any]] = field(default_factory=dict)
    reservations: dict[str, dict[str, Any]] = field(default_factory=dict)
    receipts: dict[tuple[str, str, str, str], IdempotencyReceipt] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "users": copy.deepcopy(self.users),
            "tokens": copy.deepcopy(self.tokens),
            "restaurants": copy.deepcopy(self.restaurants),
            "reservations": copy.deepcopy(self.reservations),
            "receipts": [receipt.to_dict() for receipt in self.receipts.values()],
        }

    @classmethod
    def from_dict(cls, value: Any) -> "ServiceState":
        if not isinstance(value, dict) or set(value) != {"users", "tokens", "restaurants", "reservations", "receipts"}:
            raise DomainError(422, "validation_failed", "invalid state")
        for name in ("users", "tokens", "restaurants", "reservations"):
            if not isinstance(value[name], dict):
                raise DomainError(422, "validation_failed", "invalid state")
        if not isinstance(value["receipts"], list):
            raise DomainError(422, "validation_failed", "invalid state")
        receipts: dict[tuple[str, str, str, str], IdempotencyReceipt] = {}
        for item in value["receipts"]:
            receipt = IdempotencyReceipt.from_dict(item)
            if receipt.identity in receipts:
                raise DomainError(422, "validation_failed", "duplicate idempotency receipt")
            receipts[receipt.identity] = receipt
        return cls(
            users=copy.deepcopy(value["users"]),
            tokens=copy.deepcopy(value["tokens"]),
            restaurants=copy.deepcopy(value["restaurants"]),
            reservations=copy.deepcopy(value["reservations"]),
            receipts=receipts,
        )


class StateStore:
    """All mutation paths enter one lock and swap a fully validated candidate state."""

    def __init__(self, initial: ServiceState | None = None) -> None:
        self._state = copy.deepcopy(initial) if initial is not None else ServiceState()
        self._lock = asyncio.Lock()

    async def snapshot(self) -> ServiceState:
        async with self._lock:
            return copy.deepcopy(self._state)

    async def transaction(self, mutation: Mutation[T]) -> T:
        async with self._lock:
            candidate = copy.deepcopy(self._state)
            result = mutation(candidate)
            if inspect.isawaitable(result):
                result = await result
            self._state = candidate
            return result

    async def replace(self, candidate: ServiceState) -> None:
        async with self._lock:
            self._state = copy.deepcopy(candidate)

    async def reset(self, fixture: ServiceState) -> None:
        await self.replace(fixture)

    async def export(self) -> dict[str, Any]:
        async with self._lock:
            return {"track": "tablekeeper", "format_version": 1, "state": self._state.to_dict()}

    async def import_snapshot(self, envelope: Any) -> None:
        if not isinstance(envelope, dict) or set(envelope) != {"track", "format_version", "state"}:
            raise DomainError(422, "validation_failed", "invalid export envelope")
        if envelope["track"] != "tablekeeper" or envelope["format_version"] != 1:
            raise DomainError(422, "validation_failed", "unsupported export envelope")
        candidate = ServiceState.from_dict(envelope["state"])
        await self.replace(candidate)

    async def idempotent_write(
        self,
        *,
        user_id: str,
        method: str,
        path: str,
        key: str,
        request_body: Any,
        mutation: Mutation[tuple[int, dict[str, Any]]],
    ) -> tuple[int, dict[str, Any], bool]:
        """Commit the mutation and receipt together, or leave both absent on failure."""
        request_json = canonical_json(request_body)
        identity = (user_id, method, path, key)
        async with self._lock:
            existing = self._state.receipts.get(identity)
            if existing is not None:
                if existing.request_json != request_json:
                    raise DomainError(409, "idempotency_key_reuse", "idempotency key was used with another request")
                return 200, copy.deepcopy(existing.response), True

            candidate = copy.deepcopy(self._state)
            result = mutation(candidate)
            if inspect.isawaitable(result):
                status, response = await result
            else:
                status, response = result
            if not isinstance(status, int) or not isinstance(response, dict):
                raise RuntimeError("idempotent mutation must return (status, JSON object)")
            receipt = IdempotencyReceipt(user_id, method, path, key, request_json, status, copy.deepcopy(response))
            candidate.receipts[identity] = receipt
            self._state = candidate
            return status, copy.deepcopy(response), False
