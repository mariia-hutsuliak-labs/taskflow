#!/usr/bin/env bash
# load.sh <path> <seconds> <requests-per-second> [base-url]
# Sends a steady load: every second it fires <rps> parallel requests.
set -uo pipefail
PATH_="${1:?path, e.g. /whoami}"
DURATION="${2:?seconds}"
RPS="${3:?requests per second}"
BASE="${4:-${LB_URL:-http://localhost:8080}}"

end=$((SECONDS + DURATION))
while [ "$SECONDS" -lt "$end" ]; do
  for _ in $(seq 1 "$RPS"); do
    curl -s -o /dev/null -m 10 "$BASE$PATH_" &
  done
  wait
  sleep 1
done
