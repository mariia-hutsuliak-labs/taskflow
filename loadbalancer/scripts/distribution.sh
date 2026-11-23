#!/usr/bin/env bash
# Experiment 1: how requests are distributed between the instances.
set -euo pipefail
cd "$(dirname "$0")/../.."
. loadbalancer/scripts/common.sh

N="${1:-30}"
echo "== $N requests through the balancer ($LB_URL)"
probe "$LB_URL" "$N"
