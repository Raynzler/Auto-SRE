"""Failure event persistence abstraction (shared).

Services record failure events via record_event(); the concrete backend is
hidden behind FailureStore. Today: JSONL on local disk. Future: Postgres/Redis
by swapping the factory — no business-logic change.
"""

import json
import logging
import os
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter

logger = logging.getLogger("autosre.storage")


class Source:
    CHAOS = "chaos"
    CIRCUIT_BREAKER = "circuit_breaker"
    RATE_LIMIT = "rate_limit"
    WORKER = "worker"
    AUTH = "auth"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class FailureEvent:
    source: str
    event: str
    details: dict = field(default_factory=dict)
    timestamp: str = field(default_factory=_utc_now_iso)

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "source": self.source,
            "event": self.event,
            "details": self.details,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "FailureEvent":
        return cls(
            source=d.get("source", "unknown"),
            event=d.get("event", "unknown"),
            details=d.get("details", {}),
            timestamp=d.get("timestamp", ""),
        )


class FailureStore(ABC):
    @abstractmethod
    def write_event(self, event: FailureEvent) -> None: ...

    @abstractmethod
    def read_events(
        self, limit: Optional[int] = None, source: Optional[str] = None
    ) -> List[FailureEvent]: ...

    @abstractmethod
    def clear_events(self) -> None: ...


class FileFailureStore(FailureStore):
    def __init__(self, path: str):
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def write_event(self, event: FailureEvent) -> None:
        line = json.dumps(event.to_dict(), separators=(",", ":"))
        with self._lock, self._path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    def read_events(
        self, limit: Optional[int] = None, source: Optional[str] = None
    ) -> List[FailureEvent]:
        if not self._path.exists():
            return []
        events: List[FailureEvent] = []
        with self._lock, self._path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if source is not None and d.get("source") != source:
                    continue
                events.append(FailureEvent.from_dict(d))
        return events[-limit:] if limit is not None else events

    def clear_events(self) -> None:
        with self._lock:
            if self._path.exists():
                self._path.write_text("", encoding="utf-8")


_store: Optional[FailureStore] = None
_store_lock = threading.Lock()


def _default_path() -> str:
    return os.getenv(
        "FAILURE_LOG_PATH", os.path.join(os.getenv("DATA_DIR", "data"), "failures.jsonl")
    )


def get_failure_store() -> FailureStore:
    global _store
    if _store is None:
        with _store_lock:
            if _store is None:
                _store = FileFailureStore(_default_path())
    return _store


def set_failure_store(store: FailureStore) -> None:
    global _store
    _store = store


def record_event(source: str, event: str, **details) -> None:
    """Best-effort persistence. Never raises (must not break the request path)."""
    try:
        get_failure_store().write_event(FailureEvent(source=source, event=event, details=details))
    except Exception:
        logger.exception("failed to persist failure event source=%s event=%s", source, event)


router = APIRouter(prefix="/failures", tags=["storage"])


@router.get("")
async def list_failures(limit: int = 100, source: Optional[str] = None):
    events = get_failure_store().read_events(limit=limit, source=source)
    return {"count": len(events), "events": [e.to_dict() for e in events]}


@router.delete("")
async def clear_failures():
    get_failure_store().clear_events()
    return {"status": "cleared"}
