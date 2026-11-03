import json
import logging

from fastapi.testclient import TestClient

from app import observability
from app.main import app

client = TestClient(app)


def test_metrics_endpoint_counts_requests():
    client.get("/version")
    response = client.get("/metrics")
    assert response.status_code == 200
    assert 'http_requests_total{method="GET",route="/version",status="200"}' in response.text
    assert "http_request_duration_seconds_bucket" in response.text


def test_metrics_use_route_template_not_raw_path():
    # Invalid id -> 422 from validation, so the test needs no database.
    assert client.get("/tasks/not-a-number").status_code == 422
    text = client.get("/metrics").text
    assert 'route="/tasks/{task_id}"' in text
    assert "not-a-number" not in text


def test_health_and_metrics_are_not_counted():
    client.get("/health")
    text = client.get("/metrics").text
    assert 'route="/health"' not in text
    assert 'route="/metrics"' not in text


def test_fail_rate_returns_500(monkeypatch):
    monkeypatch.setattr(observability, "FAIL_RATE", 1.0)
    assert client.get("/version").status_code == 500
    assert client.get("/health").status_code == 200


class _ListHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.lines = []

    def emit(self, record):
        self.lines.append(record.getMessage())


def test_request_log_is_json():
    handler = _ListHandler()
    observability.log.addHandler(handler)
    try:
        client.get("/version")
    finally:
        observability.log.removeHandler(handler)
    data = json.loads(handler.lines[-1])
    assert data["route"] == "/version"
    assert data["status"] == 200
    assert data["level"] == "info"
    assert "duration_ms" in data
