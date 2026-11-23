#!/usr/bin/env bash
# Shared settings for the CloudWatch monitoring scripts (LocalStack, no real AWS account).
# Run the scripts from the repository root.
ENDPOINT="${ENDPOINT:-http://localhost:4566}"
export ENDPOINT
LB_URL="${LB_URL:-http://localhost:8080}"
NAMESPACE="TaskFlow"
ALARM_ERRORS="taskflow-high-errors"
ALARM_LATENCY="taskflow-high-latency"

# alarm_state <alarm-name>: prints OK / ALARM / INSUFFICIENT_DATA
alarm_state() {
  python3 monitoring/alarms.py state "$1"
}

# wait_alarm <alarm-name> <state> <timeout-seconds>: wait until the alarm reaches the state.
wait_alarm() {
  local name="$1" want="$2" timeout="$3" waited=0 state
  while [ "$waited" -lt "$timeout" ]; do
    state=$(alarm_state "$name")
    if [ "$state" = "$want" ]; then
      echo "  $name -> $state (after ${waited}s)"
      return 0
    fi
    sleep 5
    waited=$((waited + 5))
  done
  echo "  $name did not reach $want within ${timeout}s (now: $(alarm_state "$name"))"
  return 1
}
