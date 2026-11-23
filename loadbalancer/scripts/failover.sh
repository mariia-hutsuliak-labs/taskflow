#!/usr/bin/env bash
# Experiment 2: stop one instance, check the balancer, restore the instance.
set -euo pipefail
cd "$(dirname "$0")/../.."
. loadbalancer/scripts/common.sh

N="${1:-30}"
TARGET="${2:-app2}"

echo "== 1. All instances running"
probe "$LB_URL" "$N"

echo "== 2. Stopping $TARGET"
$COMPOSE stop "$TARGET" >/dev/null
probe "$LB_URL" "$N"

echo "== 3. Starting $TARGET again"
$COMPOSE start "$TARGET" >/dev/null
wait_healthy "taskflow-$TARGET"
$COMPOSE exec -T nginx nginx -s reload >/dev/null 2>&1
sleep 2
probe "$LB_URL" "$N"
