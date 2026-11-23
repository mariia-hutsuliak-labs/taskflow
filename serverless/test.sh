#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
BASE_URL="${1:-$(cat "$DIR/.api_url")}"

echo "--- POST /tasks"
RESP=$(curl -sS -X POST "$BASE_URL/tasks" \
  -H "Content-Type: application/json" \
  -d '{"title": "Здати лабу 8", "description": "LocalStack + Lambda"}' \
  -w '\n%{http_code}')
echo "$RESP"
ID=$(echo "$RESP" | head -n1 | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])')

echo "--- GET /tasks"
curl -sS "$BASE_URL/tasks" -w '\n%{http_code}\n'

echo "--- GET /tasks/$ID"
curl -sS "$BASE_URL/tasks/$ID" -w '\n%{http_code}\n'

echo "--- DELETE /tasks/$ID"
curl -sS -X DELETE "$BASE_URL/tasks/$ID" -o /dev/null -w '%{http_code}\n'

echo "--- GET /tasks/$ID (after delete)"
curl -sS "$BASE_URL/tasks/$ID" -w '\n%{http_code}\n'
