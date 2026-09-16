#!/bin/sh
set -e

API_URL="${API_URL:-http://localhost:8000}"

cat > /usr/share/nginx/html/config.js <<CONFIG
window.API_URL = "${API_URL}";
CONFIG

exec nginx -g "daemon off;"
