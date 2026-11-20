"""Application services shared by all tools, with one target read coordinator."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import ParamSpec, Protocol, TypeVar

from .models.common import NormalizationError, ParsedObservation, remaining_seconds
from .models.source_catalog import SourceCatalog
from .policy.configuration import ConfigReadPolicy
from .policy.sanitization import SanitizerPipeline
from .snapshots import SnapshotStore

_P = ParamSpec("_P")
_T = TypeVar("_T")
_ACTIVE_CALLS = 4
_QUEUED_CALLS = 16


class RuntimeReader(Protocol):
    async def read(
        self, target_id: str, endpoint_id: str, *, snapshot_id: str
    ) -> ParsedObservation: ...


@dataclass
class Services:
    reader: RuntimeReader
    catalog: SourceCatalog
    sanitizer: SanitizerPipeline
    snapshots: SnapshotStore
    targets: frozenset[str] = frozenset({"local"})
    config_policy: ConfigReadPolicy | None = None
    _read_slots: dict[str, asyncio.Semaphore] = field(default_factory=dict, init=False)
    _call_slots: asyncio.Semaphore = field(
        default_factory=lambda: asyncio.Semaphore(_ACTIVE_CALLS), init=False
    )
    _analysis_slot: asyncio.Semaphore = field(
        default_factory=lambda: asyncio.Semaphore(1), init=False
    )
    _admitted: int = field(default=0, init=False)

    @asynccontextmanager
    async def admit_call(self) -> AsyncIterator[None]:
        if self._admitted >= _ACTIVE_CALLS + _QUEUED_CALLS:
            raise NormalizationError("SERVER_BUSY")
        self._admitted += 1
        try:
            async with self._call_slots:
                yield
        finally:
            self._admitted -= 1

    async def analyze(
        self, function: Callable[_P, _T], /, *args: _P.args, **kwargs: _P.kwargs
    ) -> _T:
        await self._analysis_slot.acquire()
        worker = asyncio.create_task(asyncio.to_thread(function, *args, **kwargs))

        def release(task: asyncio.Task[_T]) -> None:
            self._analysis_slot.release()
            if not task.cancelled():
                task.exception()

        worker.add_done_callback(release)
        return await asyncio.shield(worker)

    async def read(
        self, target_id: str, endpoint_id: str, *, snapshot_id: str
    ) -> ParsedObservation:
        if target_id not in self.targets or self.catalog.target_id != target_id:
            raise NormalizationError("TARGET_NOT_REGISTERED")
        slot = self._read_slots.setdefault(target_id, asyncio.Semaphore(2))
        # The outer tool deadline also includes waiting for this shared slot.
        async with asyncio.timeout(remaining_seconds()):
            async with slot:
                return await asyncio.wait_for(
                    self.reader.read(target_id, endpoint_id, snapshot_id=snapshot_id),
                    timeout=remaining_seconds(5.0),
                )
