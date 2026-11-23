#!/usr/bin/env bash
# Shared helpers for the load balancing experiments.
LB_URL="${LB_URL:-http://localhost:8080}"
DIRECT_URL="${DIRECT_URL:-http://localhost:8081}"
COMPOSE="docker compose -f docker-compose.lb.yml"

# probe <base-url> <count>: send <count> requests to /whoami and print how many
# answers each instance gave (FAIL = no 200 response).
probe() {
  local url="$1" n="$2" i code
  for i in $(seq 1 "$n"); do
    code=$(curl -s -m 3 -o /tmp/lb_probe.out -w '%{http_code}' "$url/whoami" || true)
    if [ "$code" = "200" ]; then
      sed -E 's/.*"instance": "([^"]+)".*/\1/' /tmp/lb_probe.out
      echo
    else
      echo FAIL
    fi
  done | sort | uniq -c | sed 's/^/    /'
}

# wait_healthy <container>: wait until docker reports the container as healthy.
wait_healthy() {
  local name="$1" i
  for i in $(seq 1 30); do
    [ "$(docker inspect -f '{{.State.Health.Status}}' "$name" 2>/dev/null)" = "healthy" ] && return 0
    sleep 1
  done
  echo "container $name did not become healthy" >&2
  return 1
}
