"""Shared failure-event persistence layer."""

from .failure_store import (
    FailureStore,
    FileFailureStore,
    FailureEvent,
    Source,
    get_failure_store,
    set_failure_store,
    record_event,
    router as failures_router,
)

__all__ = [
    "FailureStore",
    "FileFailureStore",
    "FailureEvent",
    "Source",
    "get_failure_store",
    "set_failure_store",
    "record_event",
    "failures_router",
]
