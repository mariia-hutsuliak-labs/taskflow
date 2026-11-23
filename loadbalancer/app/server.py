import json
import os
import re
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import boto3
from botocore.exceptions import ClientError

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lambda"))
import handler as lambda_app  # noqa: E402

INSTANCE_ID = os.getenv("INSTANCE_ID", "local")
PORT = int(os.getenv("PORT", "8000"))
TASK_PATH = re.compile(r"^/tasks/([^/]+)$")


def ensure_table(retries=30):
    client = boto3.client(
        "dynamodb", endpoint_url=os.getenv("DYNAMODB_ENDPOINT") or None
    )
    for _ in range(retries):
        try:
            client.create_table(
                TableName=lambda_app.TABLE_NAME,
                KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
                AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
                BillingMode="PAY_PER_REQUEST",
            )
            return
        except ClientError as exc:
            if exc.response["Error"]["Code"] == "ResourceInUseException":
                return
            time.sleep(1)
        except Exception:
            time.sleep(1)
    raise RuntimeError("DynamoDB is not reachable")


def build_event(method, path, body):
    match = TASK_PATH.match(path)
    return {
        "httpMethod": method,
        "path": path,
        "pathParameters": {"id": match.group(1)} if match else None,
        "body": body,
    }


def route(method, path, body=None):
    path = path.split("?", 1)[0].rstrip("/") or "/"
    if path == "/health" and method == "GET":
        return 200, {"status": "ok", "instance": INSTANCE_ID}
    if path == "/whoami" and method == "GET":
        return 200, {"instance": INSTANCE_ID}
    if path == "/tasks" or TASK_PATH.match(path):
        result = lambda_app.lambda_handler(build_event(method, path, body), None)
        text = result["body"]
        return result["statusCode"], json.loads(text) if text else None
    return 404, {"detail": "Not found"}


class Handler(BaseHTTPRequestHandler):
    def handle_any(self):
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length).decode() if length else None
        status, payload = route(self.command, self.path, body)
        data = b"" if payload is None else json.dumps(payload, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("X-Instance-Id", INSTANCE_ID)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    do_GET = do_POST = do_DELETE = handle_any

    def log_message(self, fmt, *args):
        print(f"[{INSTANCE_ID}] {self.address_string()} {fmt % args}", flush=True)


if __name__ == "__main__":
    ensure_table()
    print(f"[{INSTANCE_ID}] listening on :{PORT}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
