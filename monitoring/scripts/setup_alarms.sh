#!/usr/bin/env bash
# Creates two CloudWatch alarms on the custom TaskFlow metrics.
set -euo pipefail
cd "$(dirname "$0")/../.."
. monitoring/scripts/common.sh

echo "==> Alarm $ALARM_ERRORS: 10 or more errors in one minute"
aws_ cloudwatch put-metric-alarm \
  --alarm-name "$ALARM_ERRORS" \
  --alarm-description "More than 9 HTTP 5xx responses per minute" \
  --namespace "$NAMESPACE" --metric-name ErrorCount \
  --statistic Sum --period 60 --evaluation-periods 1 \
  --threshold 10 --comparison-operator GreaterThanOrEqualToThreshold \
  --treat-missing-data notBreaching

echo "==> Alarm $ALARM_LATENCY: average latency above 200 ms"
aws_ cloudwatch put-metric-alarm \
  --alarm-name "$ALARM_LATENCY" \
  --alarm-description "Average request latency above 200 ms for one minute" \
  --namespace "$NAMESPACE" --metric-name Latency \
  --statistic Average --unit Milliseconds --period 60 --evaluation-periods 1 \
  --threshold 200 --comparison-operator GreaterThanThreshold \
  --treat-missing-data notBreaching

aws_ cloudwatch describe-alarms \
  --query 'MetricAlarms[].[AlarmName,MetricName,Threshold,StateValue]' --output table
