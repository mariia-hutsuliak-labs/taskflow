import json
import os
import uuid
from datetime import datetime, timezone

import boto3
from botocore.exceptions import ClientError

TABLE_NAME = os.getenv("TABLE_NAME", "taskflow-tasks")

_table = None


def get_table():
    global _table
    if _table is None:
        _table = boto3.resource(
            "dynamodb", endpoint_url=os.getenv("DYNAMODB_ENDPOINT") or None
        ).Table(TABLE_NAME)
    return _table


def response(status, body=None):
    return {
        "statusCode": status,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": "" if body is None else json.dumps(body, ensure_ascii=False),
    }


def create_task(event):
    try:
        payload = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return response(400, {"detail": "Invalid JSON"})
    title = payload.get("title") if isinstance(payload, dict) else None
    if not isinstance(title, str) or not title.strip() or len(title) > 200:
        return response(422, {"detail": "title is required (max 200 chars)"})
    task = {
        "id": str(uuid.uuid4()),
        "title": title.strip(),
        "description": str(payload.get("description") or ""),
        "done": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    if payload.get("due_date"):
        task["due_date"] = str(payload["due_date"])
    get_table().put_item(Item=task)
    return response(201, task)


def list_tasks(_event):
    items = get_table().scan().get("Items", [])
    items.sort(key=lambda t: t["created_at"])
    return response(200, items)


def get_task(task_id):
    item = get_table().get_item(Key={"id": task_id}).get("Item")
    if item is None:
        return response(404, {"detail": "Task not found"})
    return response(200, item)


def delete_task(task_id):
    try:
        get_table().delete_item(
            Key={"id": task_id},
            ConditionExpression="attribute_exists(id)",
        )
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return response(404, {"detail": "Task not found"})
        raise
    return response(204)


def lambda_handler(event, _context):
    method = event.get("httpMethod")
    task_id = (event.get("pathParameters") or {}).get("id")
    if task_id is None:
        if method == "POST":
            return create_task(event)
        if method == "GET":
            return list_tasks(event)
    else:
        if method == "GET":
            return get_task(task_id)
        if method == "DELETE":
            return delete_task(task_id)
    return response(405, {"detail": "Method not allowed"})
