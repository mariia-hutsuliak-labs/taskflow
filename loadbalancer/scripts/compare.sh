#!/usr/bin/env bash
# Experiment 3: the same failure with and without the balancer.
set -euo pipefail
cd "$(dirname "$0")/../.."
. loadbalancer/scripts/common.sh

N="${1:-30}"

echo "== Normal operation"
echo "  without balancer (app1 directly, $DIRECT_URL):"
probe "$DIRECT_URL" "$N"
echo "  with balancer ($LB_URL):"
probe "$LB_URL" "$N"

echo
echo "== app1 is stopped"
$COMPOSE stop app1 >/dev/null
echo "  without balancer (app1 directly):"
probe "$DIRECT_URL" "$N"
echo "  with balancer:"
probe "$LB_URL" "$N"

echo
echo "== Restoring app1"
$COMPOSE start app1 >/dev/null
wait_healthy taskflow-app1
$COMPOSE exec -T nginx nginx -s reload >/dev/null 2>&1
