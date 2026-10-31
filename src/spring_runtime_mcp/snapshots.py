"""Bounded in-memory cursor store; callers supply sanitized envelopes only."""

from __future__ import annotations

import hashlib
import json
import secrets
import time
from collections import OrderedDict
from collections.abc import Callable
from copy import deepcopy
from dataclasses import asdict, dataclass
from typing import Any

from .models.common import NormalizationError
from .models.queries import InspectBeansQuery
from .policy.output_guard import ensure_safe_output
from .policy.sanitization import SanitizerPipeline


@dataclass(frozen=True)
class _Entry:
    data: bytes
    query_digest: bytes
    expires_at: float


@dataclass
class _PagedSnapshot:
    header: bytes
    items: tuple[bytes, ...]
    query_digest: bytes
    expires_at: float
    size: int
    policy: tuple[object, bytes] | None
    references: int = 0


@dataclass(frozen=True)
class _PageEntry:
    snapshot: _PagedSnapshot
    offset: int

    @property
    def expires_at(self) -> float:
        return self.snapshot.expires_at


def page_envelope(envelope: dict[str, Any], items: list[Any]) -> dict[str, Any]:
    """Copy only page metadata and selected records, never the unsent tail."""
    result = {key: deepcopy(value) for key, value in envelope.items() if key != "data"}
    result["data"] = {
        key: deepcopy(value)
        for key, value in envelope["data"].items()
        if key != "items"
    }
    result["data"]["items"] = deepcopy(items)
    return result


class SnapshotStore:
    """Opaque cursor handles bind a frozen result to all non-cursor arguments."""

    def __init__(
        self,
        clock: Callable[[], float] = time.monotonic,
        *,
        ttl: float = 60.0,
        max_bytes: int = 32 * 1024 * 1024,
    ) -> None:
        if not 0 < ttl <= 60 or not 0 < max_bytes <= 32 * 1024 * 1024:
            raise ValueError("INVALID_SNAPSHOT_LIMITS")
        self._clock = clock
        self._ttl = ttl
        self._max_bytes = max_bytes
        self._size = 0
        self._entries: OrderedDict[str, _Entry | _PageEntry] = OrderedDict()

    @staticmethod
    def _digest(query: InspectBeansQuery) -> bytes:
        values = asdict(query)
        values.pop("cursor", None)
        encoded = json.dumps(
            values,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
        return hashlib.sha256(encoded).digest()

    def _remove(self, token: str) -> None:
        entry = self._entries.pop(token)
        if isinstance(entry, _Entry):
            self._size -= len(entry.data)
        else:
            self._size -= 256
            entry.snapshot.references -= 1
            if entry.snapshot.references == 0:
                self._size -= entry.snapshot.size

    def _prune(self) -> None:
        now = self._clock()
        for token in tuple(self._entries):
            if self._entries[token].expires_at <= now:
                self._remove(token)

    def _token(self, sanitizer: SanitizerPipeline | None) -> str:
        for _ in range(16):
            token = secrets.token_urlsafe(32)
            if token in self._entries:
                continue
            try:
                ensure_safe_output({"nextCursor": token}, sanitizer=sanitizer)
            except NormalizationError as exc:
                if exc.code not in {"UNSAFE_OUTPUT", "UNTRUSTED_OUTPUT"}:
                    raise
                continue
            return token
        raise NormalizationError("UNSAFE_OUTPUT")

    def put(
        self,
        envelope: dict[str, Any],
        query: InspectBeansQuery,
        *,
        sanitizer: SanitizerPipeline | None = None,
        expires_at: float | None = None,
    ) -> str:
        self._prune()
        deadline = self._clock() + self._ttl
        if expires_at is not None:
            deadline = min(deadline, expires_at)
        if deadline <= self._clock():
            raise NormalizationError("CURSOR_EXPIRED")
        ensure_safe_output(envelope, sanitizer=sanitizer)
        try:
            data = json.dumps(
                envelope,
                sort_keys=True,
                ensure_ascii=False,
                separators=(",", ":"),
                allow_nan=False,
            ).encode("utf-8")
        except (TypeError, ValueError, UnicodeError):
            raise NormalizationError("INVALID_RESPONSE") from None
        if len(data) > self._max_bytes:
            raise NormalizationError("SNAPSHOT_TOO_LARGE")
        token = self._token(sanitizer)
        while self._entries and self._size + len(data) > self._max_bytes:
            self._remove(next(iter(self._entries)))
        self._entries[token] = _Entry(data, self._digest(query), deadline)
        self._size += len(data)
        return token

    def deadline(self, token: str, query: InspectBeansQuery) -> float:
        """Continuations inherit the original observation's absolute expiry."""
        self._prune()
        entry = self._entries.get(token)
        if entry is None:
            raise NormalizationError("CURSOR_EXPIRED")
        digest = (
            entry.query_digest
            if isinstance(entry, _Entry)
            else entry.snapshot.query_digest
        )
        if not secrets.compare_digest(digest, self._digest(query)):
            raise NormalizationError("CURSOR_QUERY_MISMATCH")
        return entry.expires_at

    def get(
        self,
        token: str,
        query: InspectBeansQuery,
        *,
        sanitizer: SanitizerPipeline | None = None,
    ) -> dict[str, Any]:
        self._prune()
        entry = self._entries.get(token)
        if entry is None:
            raise NormalizationError("CURSOR_EXPIRED")
        digest = (
            entry.query_digest
            if isinstance(entry, _Entry)
            else entry.snapshot.query_digest
        )
        if not secrets.compare_digest(digest, self._digest(query)):
            raise NormalizationError("CURSOR_QUERY_MISMATCH")
        self._entries.move_to_end(token)
        if isinstance(entry, _PageEntry):
            self._review(entry.snapshot, sanitizer)
            paged = self._decode_page(entry, len(entry.snapshot.items))
            ensure_safe_output(paged, sanitizer=sanitizer)
            return paged
        # Decoding produces a fresh mutable copy; callers cannot alter cached facts.
        value: dict[str, Any] = json.loads(entry.data)
        try:
            ensure_safe_output(value, sanitizer=sanitizer)
        except NormalizationError:
            # A newly registered credential/policy may invalidate old facts.
            # Evict rather than retaining a now-recognized secret in the cache.
            self._remove(token)
            raise
        return value

    def put_paged(
        self,
        envelope: dict[str, Any],
        query: Any,
        *,
        offset: int,
        sanitizer: SanitizerPipeline | None = None,
        expires_at: float | None = None,
    ) -> str:
        """Freeze sanitized evidence once; continuations share encoded records."""
        self._prune()
        deadline = self._clock() + self._ttl
        if expires_at is not None:
            deadline = min(deadline, expires_at)
        if deadline <= self._clock():
            raise NormalizationError("CURSOR_EXPIRED")
        ensure_safe_output(envelope, sanitizer=sanitizer)
        items = envelope["data"]["items"]
        if not 0 <= offset < len(items):
            raise ValueError("INVALID_PAGE_OFFSET")

        def encode(value: Any) -> bytes:
            return json.dumps(
                value,
                sort_keys=True,
                ensure_ascii=False,
                separators=(",", ":"),
                allow_nan=False,
            ).encode("utf-8")

        header = encode(page_envelope(envelope, []))
        records = tuple(encode(item) for item in items)
        size = len(header) + sum(len(item) + 32 for item in records) + 128
        snapshot = _PagedSnapshot(
            header,
            records,
            self._digest(query),
            deadline,
            size,
            sanitizer.cache_revision if sanitizer is not None else None,
        )
        return self._register_page(snapshot, offset, sanitizer)

    def _register_page(
        self, snapshot: _PagedSnapshot, offset: int, sanitizer: SanitizerPipeline | None
    ) -> str:
        if snapshot.size + 256 > self._max_bytes:
            raise NormalizationError("SNAPSHOT_TOO_LARGE")
        token = self._token(sanitizer)
        # Eviction may remove the last handle for this snapshot. Recompute its
        # storage charge each iteration so continuation accounting stays exact.
        while (
            self._size + 256 + (snapshot.size if snapshot.references == 0 else 0)
            > self._max_bytes
        ):
            self._remove(next(iter(self._entries)))
        if snapshot.expires_at <= self._clock():
            raise NormalizationError("CURSOR_EXPIRED")
        if snapshot.references == 0:
            self._size += snapshot.size
        snapshot.references += 1
        self._size += 256
        self._entries[token] = _PageEntry(snapshot, offset)
        return token

    def _review(
        self, snapshot: _PagedSnapshot, sanitizer: SanitizerPipeline | None
    ) -> None:
        # Replacement policies or changed credential variants must recheck ALL
        # cached facts, including unrequested records. Cache only an opaque stamp.
        revision = sanitizer.cache_revision if sanitizer is not None else None
        if snapshot.policy == revision:
            return
        try:
            ensure_safe_output(json.loads(snapshot.header), sanitizer=sanitizer)
            for item in snapshot.items:
                ensure_safe_output(json.loads(item), sanitizer=sanitizer)
        except NormalizationError:
            for token, entry in tuple(self._entries.items()):
                if isinstance(entry, _PageEntry) and entry.snapshot is snapshot:
                    self._remove(token)
            raise
        snapshot.policy = revision

    @staticmethod
    def _decode_page(entry: _PageEntry, limit: int) -> dict[str, Any]:
        result: dict[str, Any] = json.loads(entry.snapshot.header)
        result["data"]["items"] = [
            json.loads(item)
            for item in entry.snapshot.items[entry.offset : entry.offset + limit]
        ]
        return result

    def get_page(
        self, token: str, query: Any, *, sanitizer: SanitizerPipeline | None = None
    ) -> tuple[dict[str, Any], bool]:
        self.deadline(token, query)
        entry = self._entries[token]
        self._entries.move_to_end(token)
        if isinstance(entry, _Entry):
            result = self.get(token, query, sanitizer=sanitizer)
            items = result["data"]["items"]
            return page_envelope(result, items[: query.max_results]), len(
                items
            ) > query.max_results
        self._review(entry.snapshot, sanitizer)
        result = self._decode_page(entry, query.max_results)
        ensure_safe_output(result, sanitizer=sanitizer)
        return result, entry.offset + query.max_results < len(entry.snapshot.items)

    def advance(
        self,
        token: str,
        query: Any,
        consumed: int,
        *,
        sanitizer: SanitizerPipeline | None = None,
    ) -> str:
        self.deadline(token, query)
        entry = self._entries[token]
        if not 0 < consumed <= query.max_results:
            raise ValueError("INVALID_PAGE_OFFSET")
        if isinstance(entry, _Entry):
            return self.put_paged(
                self.get(token, query, sanitizer=sanitizer),
                query,
                offset=consumed,
                sanitizer=sanitizer,
                expires_at=entry.expires_at,
            )
        self._review(entry.snapshot, sanitizer)
        offset = entry.offset + consumed
        if offset >= len(entry.snapshot.items):
            raise ValueError("INVALID_PAGE_OFFSET")
        return self._register_page(entry.snapshot, offset, sanitizer)
