#!/usr/bin/env python3
"""Creates and inspects the CloudWatch alarms of the TaskFlow experiment.

  python3 monitoring/alarms.py setup        create both alarms
  python3 monitoring/alarms.py list         show all alarms and their state
  python3 monitoring/alarms.py state NAME   print only the state (OK / ALARM / INSUFFICIENT_DATA)

boto3 is pinned below 1.42: newer versions talk to CloudWatch with a protocol
that LocalStack 3.8 does not understand (the AWS CLI v2 has the same problem).
"""
import os
import sys

import boto3

NAMESPACE = "TaskFlow"
ALARMS = [
    dict(
        AlarmName="taskflow-high-errors",
        AlarmDescription="10 or more HTTP 5xx responses per minute",
        Namespace=NAMESPACE, MetricName="ErrorCount",
        Statistic="Sum", Period=60, EvaluationPeriods=1,
        Threshold=10.0, ComparisonOperator="GreaterThanOrEqualToThreshold",
        TreatMissingData="notBreaching",
    ),
    dict(
        AlarmName="taskflow-high-latency",
        AlarmDescription="Average request latency above 200 ms for one minute",
        Namespace=NAMESPACE, MetricName="Latency", Unit="Milliseconds",
        Statistic="Average", Period=60, EvaluationPeriods=1,
        Threshold=200.0, ComparisonOperator="GreaterThanThreshold",
        TreatMissingData="notBreaching",
    ),
]


def client():
    return boto3.client(
        "cloudwatch", endpoint_url=os.getenv("ENDPOINT", "http://localhost:4566"),
        region_name="us-east-1", aws_access_key_id="test", aws_secret_access_key="test",
    )


def setup(cw):
    for alarm in ALARMS:
        print(f"==> Alarm {alarm['AlarmName']}: {alarm['AlarmDescription']}")
        cw.put_metric_alarm(**alarm)
    show(cw)


def show(cw):
    print(f"{'alarm':<24} {'metric':<12} {'stat':<8} {'threshold':>9}  state")
    for a in cw.describe_alarms()["MetricAlarms"]:
        print(f"{a['AlarmName']:<24} {a['MetricName']:<12} {a['Statistic']:<8} "
              f"{a['Threshold']:>9.0f}  {a['StateValue']}")


def state(cw, name):
    alarms = cw.describe_alarms(AlarmNames=[name])["MetricAlarms"]
    print(alarms[0]["StateValue"] if alarms else "MISSING")


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "list"
    cw = client()
    if cmd == "setup":
        setup(cw)
    elif cmd == "list":
        show(cw)
    elif cmd == "state" and len(sys.argv) > 2:
        state(cw, sys.argv[2])
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
