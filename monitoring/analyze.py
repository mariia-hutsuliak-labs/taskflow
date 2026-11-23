#!/usr/bin/env python3
"""Reads the TaskFlow metrics back from CloudWatch (GetMetricStatistics),
computes request count, error rate and average latency, prints a table and
draws charts into monitoring/charts/.

Usage: python3 monitoring/analyze.py [--minutes 20] [--endpoint http://localhost:4566]
"""
import argparse
import os
from datetime import datetime, timedelta, timezone

import boto3

NAMESPACE = "TaskFlow"
INSTANCES = ("app1", "app2", "app3")
ERROR_THRESHOLD = 10
LATENCY_THRESHOLD = 200


def points(cw, metric, stat, start, end, dims=None):
    """One value per minute: {minute: value}."""
    resp = cw.get_metric_statistics(
        Namespace=NAMESPACE, MetricName=metric, Dimensions=dims or [],
        StartTime=start, EndTime=end, Period=60, Statistics=[stat],
    )
    return {p["Timestamp"].replace(second=0, microsecond=0): p[stat] for p in resp["Datapoints"]}


def collect(cw, minutes):
    end = datetime.now(timezone.utc) + timedelta(minutes=1)
    start = end - timedelta(minutes=minutes + 1)
    req = points(cw, "RequestCount", "Sum", start, end)
    err = points(cw, "ErrorCount", "Sum", start, end)
    lat_sum = points(cw, "Latency", "Sum", start, end)
    lat_cnt = points(cw, "Latency", "SampleCount", start, end)
    lat_max = points(cw, "Latency", "Maximum", start, end)
    rows = []
    for minute in sorted(req):
        n = req[minute]
        e = err.get(minute, 0.0)
        cnt = lat_cnt.get(minute, 0.0)
        rows.append({
            "minute": minute,
            "requests": n,
            "errors": e,
            "error_rate": 100.0 * e / n if n else 0.0,
            "avg_ms": lat_sum.get(minute, 0.0) / cnt if cnt else 0.0,
            "max_ms": lat_max.get(minute, 0.0),
        })
    per_instance = {
        name: points(cw, "RequestCount", "Sum", start, end, [{"Name": "Instance", "Value": name}])
        for name in INSTANCES
    }
    return rows, per_instance


def print_table(rows):
    print(f"{'time (UTC)':<10} {'requests':>9} {'errors':>7} {'error %':>8} {'avg ms':>8} {'max ms':>8}")
    for r in rows:
        print(f"{r['minute']:%H:%M:00}  {r['requests']:>9.0f} {r['errors']:>7.0f} "
              f"{r['error_rate']:>8.1f} {r['avg_ms']:>8.1f} {r['max_ms']:>8.1f}")
    total = sum(r["requests"] for r in rows)
    errors = sum(r["errors"] for r in rows)
    weighted = sum(r["avg_ms"] * r["requests"] for r in rows)
    print("-" * 56)
    print(f"Total requests: {total:.0f}")
    print(f"Errors: {errors:.0f} ({100.0 * errors / total:.1f}% of requests)" if total else "Errors: 0")
    print(f"Average response time: {weighted / total:.1f} ms" if total else "")


def print_alarms(cw):
    print("\nAlarms:")
    for a in cw.describe_alarms()["MetricAlarms"]:
        print(f"  {a['AlarmName']}: {a['StateValue']} ({a.get('StateReason', '')})")
    print("\nAlarm state changes:")
    try:
        history = cw.describe_alarm_history(HistoryItemType="StateUpdate", MaxRecords=50)["AlarmHistoryItems"]
    except Exception as exc:  # not every emulator implements the history API
        print(f"  (history is not available: {type(exc).__name__})")
        return
    for h in sorted(history, key=lambda x: x["Timestamp"]):
        print(f"  {h['Timestamp']:%H:%M:%S}  {h['AlarmName']}: {h['HistorySummary']}")


def draw(rows, per_instance, outdir):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    os.makedirs(outdir, exist_ok=True)
    x = [r["minute"] for r in rows]

    def style(ax, title, ylabel):
        ax.set_title(title)
        ax.set_ylabel(ylabel)
        ax.grid(alpha=0.3)
        ax.figure.autofmt_xdate()

    fig, ax = plt.subplots(figsize=(9, 4))
    ax.bar(x, [r["requests"] for r in rows], width=0.0006, color="#2F6DB5")
    style(ax, "Requests per minute", "requests")
    fig.tight_layout(); fig.savefig(f"{outdir}/requests.png", dpi=130); plt.close(fig)

    fig, ax = plt.subplots(figsize=(9, 4))
    ax.plot(x, [r["error_rate"] for r in rows], marker="o", color="#C0392B")
    style(ax, "Error rate (5xx responses, % of requests)", "%")
    fig.tight_layout(); fig.savefig(f"{outdir}/error_rate.png", dpi=130); plt.close(fig)

    fig, ax = plt.subplots(figsize=(9, 4))
    ax.plot(x, [r["avg_ms"] for r in rows], marker="o", label="average", color="#2F6DB5")
    ax.plot(x, [r["max_ms"] for r in rows], marker=".", linestyle="--", label="maximum", color="#999999")
    ax.axhline(LATENCY_THRESHOLD, color="#C0392B", linestyle=":", label=f"alarm threshold {LATENCY_THRESHOLD} ms")
    ax.legend()
    style(ax, "Response time per minute", "ms")
    fig.tight_layout(); fig.savefig(f"{outdir}/latency.png", dpi=130); plt.close(fig)

    fig, ax = plt.subplots(figsize=(9, 4))
    ax.bar(x, [r["errors"] for r in rows], width=0.0006, color="#C0392B")
    ax.axhline(ERROR_THRESHOLD, color="#333333", linestyle=":", label=f"alarm threshold {ERROR_THRESHOLD}")
    ax.legend()
    style(ax, "Errors per minute", "errors")
    fig.tight_layout(); fig.savefig(f"{outdir}/errors.png", dpi=130); plt.close(fig)

    fig, ax = plt.subplots(figsize=(9, 4))
    for name, data in per_instance.items():
        ax.plot(sorted(data), [data[m] for m in sorted(data)], marker="o", label=name)
    ax.legend()
    style(ax, "Requests per minute by instance", "requests")
    fig.tight_layout(); fig.savefig(f"{outdir}/by_instance.png", dpi=130); plt.close(fig)
    print(f"\nCharts saved to {outdir}/: requests, errors, error_rate, latency, by_instance")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--minutes", type=int, default=20)
    parser.add_argument("--endpoint", default=os.getenv("ENDPOINT", "http://localhost:4566"))
    parser.add_argument("--out", default="monitoring/charts")
    args = parser.parse_args()
    cw = boto3.client(
        "cloudwatch", endpoint_url=args.endpoint, region_name="us-east-1",
        aws_access_key_id="test", aws_secret_access_key="test",
    )
    rows, per_instance = collect(cw, args.minutes)
    if not rows:
        raise SystemExit("No metrics yet. Generate load first (monitoring/scripts/scenario.sh).")
    print_table(rows)
    print_alarms(cw)
    draw(rows, per_instance, args.out)


if __name__ == "__main__":
    main()
