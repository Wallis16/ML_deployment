#!/usr/bin/env bash
# Runs a headless Locust load test against the SQL agent API and writes a
# CSV + text summary + PNG chart under locust_test/results/<timestamp>/.
#
# Usage: ./run_load_test.sh [users] [spawn_rate] [duration]
# Env overrides: HOST, USERS, SPAWN_RATE, DURATION
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

HOST="${HOST:-http://127.0.0.1:8000}"
USERS="${1:-${USERS:-5}}"
SPAWN_RATE="${2:-${SPAWN_RATE:-1}}"
DURATION="${3:-${DURATION:-1m}}"

if ! curl -sf -o /dev/null "$HOST/health"; then
    echo "API at $HOST is not responding to /health — start it first (see ../app/README.md)." >&2
    exit 1
fi

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUT_DIR="results/$TIMESTAMP"
mkdir -p "$OUT_DIR"

echo "Host: $HOST | Users: $USERS | Spawn rate: $SPAWN_RATE | Duration: $DURATION"
echo "Every /query hit runs the real agent (Groq + Postgres) — this is not free traffic."

# Locust exits non-zero if any request failed during the run — that's a
# finding to report, not a script error, so don't let `set -e` swallow the
# summary step because of it.
set +e
locust -f locustfile.py \
    --host "$HOST" \
    --users "$USERS" \
    --spawn-rate "$SPAWN_RATE" \
    --run-time "$DURATION" \
    --headless \
    --csv "$OUT_DIR/stats" \
    --html "$OUT_DIR/report.html"
LOCUST_EXIT=$?
set -e

python summarize.py "$OUT_DIR"

echo
echo "Results: $OUT_DIR/{summary.txt, summary.png, report.html}"
exit $LOCUST_EXIT
