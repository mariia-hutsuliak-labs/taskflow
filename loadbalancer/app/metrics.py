"""Collects request metrics in memory and publishes them to CloudWatch.

Every request is recorded (count, error flag, duration). A background thread
sends the accumulated values with PutMetricData every ``interval`` seconds.
Each metric is published twice: once without dimensions (the whole service,
used by the alarms) and once with the ``Instance`` dimension (per instance).
"""
import threading
import time
from datetime import datetime, timezone

NAMESPACE = "TaskFlow"


class MetricsPublisher:
    def __init__(self, client, instance, interval=10, namespace=NAMESPACE):
        self.client = client
        self.instance = instance
        self.interval = interval
        self.namespace = namespace
        self._lock = threading.Lock()
        self._reset()

    def _reset(self):
        self._requests = 0
        self._errors = 0
        self._durations = []

    def record(self, status, seconds):
        """Remember one handled request: HTTP status and duration in seconds."""
        with self._lock:
            self._requests += 1
            if status >= 500:
                self._errors += 1
            self._durations.append(seconds * 1000.0)

    def _take(self):
        with self._lock:
            snapshot = (self._requests, self._errors, self._durations)
            self._reset()
        return snapshot

    def build(self, requests, errors, durations, now=None):
        now = now or datetime.now(timezone.utc)
        stats = {
            "SampleCount": float(len(durations)),
            "Sum": sum(durations),
            "Minimum": min(durations),
            "Maximum": max(durations),
        }
        data = []
        for dims in ([], [{"Name": "Instance", "Value": self.instance}]):
            data += [
                {"MetricName": "RequestCount", "Dimensions": dims, "Timestamp": now,
                 "Value": float(requests), "Unit": "Count"},
                {"MetricName": "ErrorCount", "Dimensions": dims, "Timestamp": now,
                 "Value": float(errors), "Unit": "Count"},
                {"MetricName": "Latency", "Dimensions": dims, "Timestamp": now,
                 "StatisticValues": stats, "Unit": "Milliseconds"},
            ]
        return data

    def flush(self):
        """Publish everything recorded since the last flush. Returns the number of requests sent."""
        requests, errors, durations = self._take()
        if not requests:
            return 0
        try:
            self.client.put_metric_data(
                Namespace=self.namespace,
                MetricData=self.build(requests, errors, durations),
            )
        except Exception as exc:  # metrics must never break request handling
            print(f"[{self.instance}] metrics: PutMetricData failed: {exc}", flush=True)
            with self._lock:  # put the values back so they go out next time
                self._requests += requests
                self._errors += errors
                self._durations += durations
            return 0
        return requests

    def start(self):
        def loop():
            while True:
                time.sleep(self.interval)
                self.flush()

        threading.Thread(target=loop, daemon=True, name="metrics").start()
