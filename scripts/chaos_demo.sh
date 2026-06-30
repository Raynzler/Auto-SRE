#!/usr/bin/env bash
# Demo chaos scenario for `make chaos`. Injects failures across services so the
# observability stack lights up, then tells you what to watch. Reversible with
# `make chaos-reset`. AutoSRE performs no automated remediation — you reset it.
set -euo pipefail

API=${API:-http://localhost:8000}
AUTH=${AUTH:-http://localhost:8001}
WORKER=${WORKER:-http://localhost:8002}

inject() { # url json
	curl -fsS -X POST "$1" -H 'content-type: application/json' -d "$2" >/dev/null
}

echo "Injecting 1.5s latency on api ..."
inject "$API/chaos/latency" '{"enable":true,"delay_seconds":1.5}'

echo "Injecting 50% errors on auth ..."
inject "$AUTH/chaos/errors" '{"enable":true,"rate_percent":50}'

echo "Triggering a 10s CPU spike on worker ..."
inject "$WORKER/chaos/cpu" '{"duration_seconds":10}'

cat <<'EOF'

Chaos injected. Watch it land:
  Grafana     http://localhost:3000   (RED -> $job, Chaos, Incident)
  Prometheus  http://localhost:9090/alerts
              expect: ChaosModeActive, HighLatencyP95, (HighErrorRate on auth)
  Failures    curl -s "http://localhost:8000/failures?source=chaos"

Reset everything:
  make chaos-reset
EOF
