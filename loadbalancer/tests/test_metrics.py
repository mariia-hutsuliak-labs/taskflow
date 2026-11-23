import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import boto3
import pytest
from moto import mock_aws

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
from metrics import MetricsPublisher  # noqa: E402


@pytest.fixture
def cw(monkeypatch):
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test")
    with mock_aws():
        yield boto3.client("cloudwatch")


def stat(cw, metric, statistic, dims=None):
    now = datetime.now(timezone.utc)
    resp = cw.get_metric_statistics(
        Namespace="TaskFlow", MetricName=metric, Dimensions=dims or [],
        StartTime=now - timedelta(minutes=5), EndTime=now + timedelta(minutes=1),
        Period=300, Statistics=[statistic],
    )
    return sum(p[statistic] for p in resp["Datapoints"])


def test_flush_publishes_counts_and_latency(cw):
    pub = MetricsPublisher(cw, "app1")
    pub.record(200, 0.010)
    pub.record(200, 0.030)
    pub.record(500, 0.020)
    assert pub.flush() == 3
    app1 = [{"Name": "Instance", "Value": "app1"}]
    assert stat(cw, "RequestCount", "Sum", app1) == 3
    assert stat(cw, "ErrorCount", "Sum", app1) == 1
    assert stat(cw, "Latency", "SampleCount", app1) == 3
    assert stat(cw, "Latency", "Sum", app1) == pytest.approx(60.0)
    assert stat(cw, "Latency", "Maximum", app1) == pytest.approx(30.0)


def test_metrics_are_also_published_without_dimensions(cw):
    pub = MetricsPublisher(cw, "app1")
    pub.record(200, 0.010)
    pub.flush()
    listed = cw.list_metrics(Namespace="TaskFlow", MetricName="RequestCount")["Metrics"]
    assert [] in [m["Dimensions"] for m in listed]


def test_per_instance_dimension(cw):
    pub = MetricsPublisher(cw, "app2")
    pub.record(200, 0.001)
    pub.flush()
    assert stat(cw, "RequestCount", "Sum", [{"Name": "Instance", "Value": "app2"}]) == 1
    assert stat(cw, "RequestCount", "Sum", [{"Name": "Instance", "Value": "app1"}]) == 0


def test_flush_without_requests_sends_nothing(cw):
    pub = MetricsPublisher(cw, "app1")
    assert pub.flush() == 0
    assert stat(cw, "RequestCount", "Sum") == 0


def test_counters_reset_after_flush(cw):
    pub = MetricsPublisher(cw, "app1")
    pub.record(200, 0.001)
    pub.flush()
    assert pub.flush() == 0


def test_failed_publish_keeps_values_for_next_flush():
    class Broken:
        def put_metric_data(self, **kwargs):
            raise RuntimeError("cloudwatch is down")

    pub = MetricsPublisher(Broken(), "app1")
    pub.record(500, 0.005)
    assert pub.flush() == 0
    assert pub._requests == 1 and pub._errors == 1
