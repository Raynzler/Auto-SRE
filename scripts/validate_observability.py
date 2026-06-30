#!/usr/bin/env python3
"""Validate Grafana provisioning + dashboards and Prometheus rule structure.

Used by CI (grafana-validate job). Exits non-zero on any problem.
Run: python scripts/validate_observability.py
"""

import glob
import json
import pathlib
import sys

try:
    import yaml
except ImportError:
    print("pyyaml is required: pip install pyyaml", file=sys.stderr)
    sys.exit(2)

ROOT = pathlib.Path(__file__).resolve().parents[1]
OBS = ROOT / "observability"
errors: list[str] = []


def err(msg: str) -> None:
    errors.append(msg)


# --- Grafana provisioning ---
ds = yaml.safe_load((OBS / "grafana/provisioning/datasources/prometheus.yml").read_text())
if ds["datasources"][0]["uid"] != "prometheus":
    err("datasource uid must be 'prometheus'")

prov = yaml.safe_load((OBS / "grafana/provisioning/dashboards/dashboards.yml").read_text())
if prov["providers"][0]["options"]["path"] != "/etc/grafana/dashboards":
    err("dashboard provider path must be /etc/grafana/dashboards")

# --- Grafana dashboards ---
dashboards = sorted(glob.glob(str(OBS / "grafana/dashboards/*.json")))
if not dashboards:
    err("no dashboards found")
for path in dashboards:
    name = pathlib.Path(path).name
    try:
        d = json.loads(pathlib.Path(path).read_text())
    except json.JSONDecodeError as e:
        err(f"{name}: invalid JSON: {e}")
        continue
    if not isinstance(d.get("uid"), str):
        err(f"{name}: missing uid")
    panels = d.get("panels", [])
    ids = [p.get("id") for p in panels]
    if len(ids) != len(set(ids)):
        err(f"{name}: duplicate panel ids")
    for p in panels:
        if p.get("type") in ("row", "text"):
            continue
        if (p.get("datasource") or {}).get("uid") != "prometheus":
            err(f"{name}: panel '{p.get('title')}' missing prometheus datasource")
        for t in p.get("targets", []):
            if not t.get("expr"):
                err(f"{name}: panel '{p.get('title')}' has a target with no expr")

# --- Prometheus rule/alert structure (promtool does the deep check in CI) ---
rule_files = glob.glob(str(OBS / "prometheus/rules/*.yml")) + glob.glob(
    str(OBS / "prometheus/alerts/*.yml")
)
recorded, alerts = set(), set()
for path in rule_files:
    doc = yaml.safe_load(pathlib.Path(path).read_text())
    for group in doc.get("groups", []):
        for rule in group.get("rules", []):
            if "record" in rule:
                recorded.add(rule["record"])
            elif "alert" in rule:
                alerts.add(rule["alert"])
                ann = rule.get("annotations", {})
                if not {"summary", "description", "runbook_url"} <= set(ann):
                    err(f"alert {rule['alert']} missing required annotations")

for required in ("api:request_rate", "api:error_rate", "api:latency:p95", "api:availability"):
    if required not in recorded:
        err(f"missing recording rule: {required}")

print(f"dashboards: {len(dashboards)}  recorded rules: {len(recorded)}  alerts: {len(alerts)}")
if errors:
    print("VALIDATION FAILED:")
    for e in errors:
        print("  -", e)
    sys.exit(1)
print("observability validation OK")
