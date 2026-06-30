"""Alert + recording-rule verification (config-level, with optional promtool)."""

import glob
import pathlib
import shutil
import subprocess

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
ALERT_FILES = sorted(glob.glob(str(ROOT / "observability/prometheus/alerts/*.yml")))
RULE_FILES = sorted(glob.glob(str(ROOT / "observability/prometheus/rules/*.yml")))


def _load():
    recorded, alerts = set(), {}
    for path in ALERT_FILES + RULE_FILES:
        doc = yaml.safe_load(open(path))
        for group in doc["groups"]:
            for rule in group["rules"]:
                if "record" in rule:
                    recorded.add(rule["record"])
                elif "alert" in rule:
                    alerts[rule["alert"]] = rule
    return recorded, alerts


def test_required_recording_rules_present():
    recorded, _ = _load()
    for name in (
        "api:request_rate",
        "api:error_rate",
        "api:latency:p95",
        "api:availability",
        "api:slo_target",
        "api:error_budget_remaining",
    ):
        assert name in recorded, f"missing recording rule: {name}"


def test_required_alerts_present():
    _, alerts = _load()
    for name in (
        "HighErrorRate",
        "HighLatencyP95",
        "ServiceDown",
        "ChaosModeActive",
        "CircuitBreakerOpen",
        "RateLimitingSpike",
    ):
        assert name in alerts, f"missing alert: {name}"


def test_every_alert_has_required_annotations():
    _, alerts = _load()
    for name, rule in alerts.items():
        labels = rule.get("labels", {}) or {}
        ann = rule.get("annotations", {}) or {}
        assert "severity" in labels, f"{name}: missing severity"
        assert "summary" in ann, f"{name}: missing summary"
        assert "description" in ann, f"{name}: missing description"
        assert "runbook_url" in ann, f"{name}: missing runbook_url"


def test_runbook_files_exist_for_alerts():
    runbooks = ROOT / "docs" / "runbooks"
    for slug in (
        "high-latency",
        "high-error-rate",
        "service-down",
        "circuit-breaker-open",
        "rate-limit-spike",
    ):
        assert (runbooks / f"{slug}.md").exists(), f"missing runbook: {slug}.md"


@pytest.mark.skipif(shutil.which("promtool") is None, reason="promtool not installed")
def test_promtool_check_rules():
    result = subprocess.run(
        ["promtool", "check", "rules", *RULE_FILES, *ALERT_FILES],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
