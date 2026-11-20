#!/usr/bin/env bash
# Step 0: check that both APIs are running (start them with: docker compose up --build)
CLIENT_API="${CLIENT_API:-http://localhost:8080}"
DASHBOARD_API="${DASHBOARD_API:-http://localhost:8000}"

echo "Client API:"
curl -sS -w '\nHTTP %{http_code}\n' "$CLIENT_API/health"

echo "Dashboard API:"
curl -sS -w '\nHTTP %{http_code}\n' "$DASHBOARD_API/health"
