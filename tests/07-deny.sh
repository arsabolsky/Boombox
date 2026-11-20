#!/usr/bin/env bash
# Step 5, the other choice (dashboard): deny a fix script. It is never sent to the client.
# Usage: ./07-deny.sh <remediation id>
DASHBOARD_API="${DASHBOARD_API:-http://localhost:8000}"
ID="${1:?Usage: ./07-deny.sh <remediation id from step 5>}"

curl -sS -w '\nHTTP %{http_code}\n' -X POST "$DASHBOARD_API/api/v1/remediations/$ID/deny" \
  -H "Content-Type: application/json" \
  -d '{"reviewed_by": "tester"}'
