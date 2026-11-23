import json
import os
import re
import sys
import time
from urllib.parse import parse_qs
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import boto3
from botocore.exceptions import ClientError

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lambda"))
import handler as lambda_app  # noqa: E402
from metrics import MetricsPublisher  # noqa: E402

INSTANCE_ID = os.getenv("INSTANCE_ID", "local")
PORT = int(os.getenv("PORT", "8000"))
TASK_PATH = re.compile(r"^/tasks/([^/]+)$")
METRICS = None  # set in main when CLOUDWATCH_ENDPOINT is configured


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
    path, _, query = path.partition("?")
    path = path.rstrip("/") or "/"
    if path == "/health" and method == "GET":
        return 200, {"status": "ok", "instance": INSTANCE_ID}
    if path == "/work" and method == "GET":
        # artificial slowdown for the monitoring experiments: /work?delay_ms=300
        delay = int(parse_qs(query).get("delay_ms", ["0"])[0])
        time.sleep(min(max(delay, 0), 5000) / 1000)
        return 200, {"instance": INSTANCE_ID, "delay_ms": delay}
    if path == "/boom" and method == "GET":
        # artificial failure for the monitoring experiments
        return 500, {"detail": "simulated failure", "instance": INSTANCE_ID}
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
        started = time.perf_counter()
        try:
            status, payload = route(self.command, self.path, body)
        except Exception as exc:
            status, payload = 500, {"detail": f"internal error: {exc}"}
        if METRICS and not self.path.startswith("/health"):
            METRICS.record(status, time.perf_counter() - started)
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


def start_metrics():
    global METRICS
    endpoint = os.getenv("CLOUDWATCH_ENDPOINT")
    if not endpoint:
        return
    client = boto3.client("cloudwatch", endpoint_url=endpoint)
    METRICS = MetricsPublisher(client, INSTANCE_ID, int(os.getenv("METRICS_INTERVAL", "10")))
    METRICS.start()


if __name__ == "__main__":
    ensure_table()
    start_metrics()
    print(f"[{INSTANCE_ID}] listening on :{PORT}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
