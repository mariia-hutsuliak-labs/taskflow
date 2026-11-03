import json
import logging
import os
import random
import sys
import time
from datetime import datetime, timezone

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from starlette.routing import Match

REQUESTS = Counter("http_requests_total", "HTTP requests", ["method", "route", "status"])
LATENCY = Histogram("http_request_duration_seconds", "Request latency", ["route"])

# Share of requests that get an injected HTTP 500 (0.0-1.0), used to demo bad releases.
FAIL_RATE = float(os.getenv("FAIL_RATE", "0"))
SKIP_PATHS = {"/metrics", "/health"}

log = logging.getLogger("taskflow")
log.setLevel(logging.INFO)
log.propagate = False
_handler = logging.StreamHandler(sys.stdout)
_handler.setFormatter(logging.Formatter("%(message)s"))
log.addHandler(_handler)


def _route_template(request: Request) -> str:
    # Route template (/tasks/{task_id}), never the raw path: keeps label cardinality low.
    for route in request.app.router.routes:
        match, _ = route.matches(request.scope)
        if match == Match.FULL:
            return route.path
    return "unknown"


def setup_observability(app: FastAPI) -> None:
    @app.middleware("http")
    async def observe(request: Request, call_next):
        if request.url.path in SKIP_PATHS:
            return await call_next(request)

        route = _route_template(request)
        start = time.perf_counter()
        if random.random() < FAIL_RATE:
            response = JSONResponse({"detail": "injected failure"}, status_code=500)
        else:
            response = await call_next(request)
        duration = time.perf_counter() - start

        REQUESTS.labels(request.method, route, str(response.status_code)).inc()
        LATENCY.labels(route).observe(duration)
        log.info(
            json.dumps(
                {
                    "time": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
                    "level": "error" if response.status_code >= 500 else "info",
                    "msg": "request",
                    "method": request.method,
                    "route": route,
                    "status": response.status_code,
                    "duration_ms": round(duration * 1000, 1),
                    "version": os.getenv("APP_VERSION", "dev"),
                }
            )
        )
        return response

    @app.get("/metrics", include_in_schema=False)
    def metrics() -> Response:
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
