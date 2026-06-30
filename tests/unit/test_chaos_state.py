"""Unit tests: chaos state (deterministic error spread, activity, snapshot)."""

from autosre_shared.chaos import ChaosState


def test_error_injection_disabled_by_default():
    s = ChaosState()
    assert s.should_inject_error() is False
    assert s.is_active() is False


def test_error_injection_is_deterministic_and_even():
    s = ChaosState()
    s.error_enabled = True
    s.error_rate = 0.5
    pattern = [s.should_inject_error() for _ in range(10)]
    assert pattern == [False, True] * 5
    assert pattern.count(True) == 5


def test_error_injection_full_rate():
    s = ChaosState()
    s.error_enabled = True
    s.error_rate = 1.0
    assert all(s.should_inject_error() for _ in range(5))


def test_is_active_tracks_modes():
    s = ChaosState()
    assert s.is_active() is False
    s.latency_enabled = True
    s.latency_seconds = 1.0
    assert s.is_active() is True


def test_snapshot_shape():
    s = ChaosState()
    s.error_enabled = True
    s.error_rate = 0.25
    snap = s.snapshot()
    assert snap["errors"]["enabled"] is True
    assert snap["errors"]["rate_percent"] == 25.0
    assert set(snap) == {"active", "latency", "errors", "cpu", "memory"}
