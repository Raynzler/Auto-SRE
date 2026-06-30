"""Unit tests: failure store (JSONL persistence, filters, replaceability)."""

from autosre_shared.storage.failure_store import (
    FileFailureStore,
    FailureStore,
    FailureEvent,
    Source,
    get_failure_store,
    set_failure_store,
    record_event,
)


def test_write_read_filter_limit_clear(tmp_path):
    s = FileFailureStore(str(tmp_path / "f.jsonl"))
    s.write_event(FailureEvent(source=Source.CHAOS, event="latency_enable", details={"s": 1.5}))
    s.write_event(FailureEvent(source=Source.RATE_LIMIT, event="rejected"))
    s.write_event(FailureEvent(source=Source.CHAOS, event="reset"))

    assert len(s.read_events()) == 3
    assert [e.event for e in s.read_events(source=Source.CHAOS)] == ["latency_enable", "reset"]
    assert len(s.read_events(limit=1)) == 1
    assert s.read_events(limit=1)[0].event == "reset"  # last N

    s.clear_events()
    assert s.read_events() == []


def test_read_missing_file_returns_empty(tmp_path):
    s = FileFailureStore(str(tmp_path / "missing.jsonl"))
    assert s.read_events() == []


def test_record_event_is_best_effort(tmp_path):
    set_failure_store(FileFailureStore(str(tmp_path / "r.jsonl")))
    record_event(Source.WORKER, "job_failed", service="worker")
    events = get_failure_store().read_events()
    assert events and events[-1].source == "worker"


def test_store_is_replaceable():
    class MemStore(FailureStore):
        def __init__(self):
            self.events = []

        def write_event(self, e):
            self.events.append(e)

        def read_events(self, limit=None, source=None):
            return self.events

        def clear_events(self):
            self.events.clear()

    set_failure_store(MemStore())
    record_event(Source.CHAOS, "swapped")
    assert isinstance(get_failure_store(), MemStore)
    assert len(get_failure_store().read_events()) == 1
