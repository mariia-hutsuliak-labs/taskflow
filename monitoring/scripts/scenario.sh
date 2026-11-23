#!/usr/bin/env bash
# Full monitoring experiment: normal load, a burst of errors, a burst of slow
# requests, with recovery in between. Alarm states are printed after each phase.
set -euo pipefail
cd "$(dirname "$0")/../.."
. monitoring/scripts/common.sh

T="${PHASE_SECONDS:-60}"        # normal and recovery phases
B="${BURST_SECONDS:-90}"        # error and latency phases

state() { echo "  alarms: errors=$(alarm_state "$ALARM_ERRORS"), latency=$(alarm_state "$ALARM_LATENCY")"; }

echo "== Phase 1: normal load (${T}s, 5 req/s to /whoami)"
monitoring/scripts/load.sh /whoami "$T" 5
state

echo "== Phase 2: errors (${B}s, 5 req/s /whoami + 3 req/s /boom)"
monitoring/scripts/load.sh /whoami "$B" 5 &
monitoring/scripts/load.sh /boom "$B" 3 &
wait
wait_alarm "$ALARM_ERRORS" ALARM 150 || true
state

echo "== Phase 3: recovery (${T}s, normal load)"
monitoring/scripts/load.sh /whoami "$T" 5
wait_alarm "$ALARM_ERRORS" OK 150 || true
state

echo "== Phase 4: high latency (${B}s, 4 req/s /work?delay_ms=600 + 1 req/s /whoami)"
monitoring/scripts/load.sh "/work?delay_ms=600" "$B" 4 &
monitoring/scripts/load.sh /whoami "$B" 1 &
wait
wait_alarm "$ALARM_LATENCY" ALARM 150 || true
state

echo "== Phase 5: recovery (${T}s, normal load)"
monitoring/scripts/load.sh /whoami "$T" 5
wait_alarm "$ALARM_LATENCY" OK 150 || true
state

echo
echo "Done. Metrics and charts: python3 monitoring/analyze.py"
