import importlib
import json
import sys
from pathlib import Path

import boto3
import pytest
from moto import mock_aws

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "serverless" / "lambda"))
sys.path.insert(0, str(ROOT / "loadbalancer" / "app"))


@pytest.fixture
def server(monkeypatch):
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test")
    monkeypatch.setenv("TABLE_NAME", "taskflow-tasks")
    monkeypatch.setenv("INSTANCE_ID", "app7")
    with mock_aws():
        for name in ("handler", "server"):
            sys.modules.pop(name, None)
        module = importlib.import_module("server")
        module.ensure_table()
        yield module


def test_health_returns_instance_id(server):
    status, body = server.route("GET", "/health")
    assert status == 200
    assert body == {"status": "ok", "instance": "app7"}


def test_whoami_returns_instance_id(server):
    assert server.route("GET", "/whoami") == (200, {"instance": "app7"})


def test_tasks_flow_through_lambda_handler(server):
    status, task = server.route("POST", "/tasks", json.dumps({"title": "x"}))
    assert status == 201
    assert server.route("GET", f"/tasks/{task['id']}")[0] == 200
    assert server.route("DELETE", f"/tasks/{task['id']}") == (204, None)
    assert server.route("GET", f"/tasks/{task['id']}")[0] == 404


def test_ensure_table_is_idempotent(server):
    server.ensure_table()
    tables = boto3.client("dynamodb").list_tables()["TableNames"]
    assert tables == ["taskflow-tasks"]


def test_unknown_path(server):
    assert server.route("GET", "/nope")[0] == 404


def test_boom_returns_500(server):
    status, body = server.route("GET", "/boom")
    assert status == 500
    assert body["instance"] == "app7"


def test_work_delays_response(server):
    import time

    started = time.perf_counter()
    status, body = server.route("GET", "/work?delay_ms=100")
    assert status == 200
    assert body["delay_ms"] == 100
    assert time.perf_counter() - started >= 0.1
