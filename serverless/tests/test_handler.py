import importlib
import json
import sys
from pathlib import Path

import boto3
import pytest
from moto import mock_aws

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lambda"))


@pytest.fixture
def handler(monkeypatch):
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test")
    monkeypatch.setenv("TABLE_NAME", "taskflow-tasks")
    with mock_aws():
        boto3.client("dynamodb").create_table(
            TableName="taskflow-tasks",
            KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        module = importlib.import_module("handler")
        module._table = None
        yield module


def call(handler, method, task_id=None, body=None):
    event = {
        "httpMethod": method,
        "pathParameters": {"id": task_id} if task_id else None,
        "body": json.dumps(body) if body is not None else None,
    }
    result = handler.lambda_handler(event, None)
    parsed = json.loads(result["body"]) if result["body"] else None
    return result["statusCode"], parsed


def test_create_get_delete_flow(handler):
    status, task = call(handler, "POST", body={"title": "Здати лабу"})
    assert status == 201
    assert task["done"] is False

    status, fetched = call(handler, "GET", task["id"])
    assert status == 200
    assert fetched["title"] == "Здати лабу"

    assert call(handler, "DELETE", task["id"]) == (204, None)
    assert call(handler, "GET", task["id"])[0] == 404


def test_list_tasks(handler):
    call(handler, "POST", body={"title": "a"})
    call(handler, "POST", body={"title": "b"})
    status, items = call(handler, "GET")
    assert status == 200
    assert [t["title"] for t in items] == ["a", "b"]


def test_create_requires_title(handler):
    assert call(handler, "POST", body={"description": "x"})[0] == 422
    assert call(handler, "POST", body={"title": "  "})[0] == 422


def test_invalid_json(handler):
    result = handler.lambda_handler({"httpMethod": "POST", "body": "{oops"}, None)
    assert result["statusCode"] == 400


def test_delete_missing_returns_404(handler):
    assert call(handler, "DELETE", "nope")[0] == 404


def test_unsupported_method(handler):
    assert call(handler, "PUT", "x")[0] == 405
