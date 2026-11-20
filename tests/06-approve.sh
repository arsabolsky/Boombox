#!/usr/bin/env bash
# Step 5 (dashboard): approve a fix script. The client gets it from 08-poll-remediations.sh.
# Usage: ./06-approve.sh <remediation id>
DASHBOARD_API="${DASHBOARD_API:-http://localhost:8000}"
ID="${1:?Usage: ./06-approve.sh <remediation id from step 5>}"

curl -sS -w '\nHTTP %{http_code}\n' -X POST "$DASHBOARD_API/api/v1/remediations/$ID/approve" \
  -H "Content-Type: application/json" \
  -d '{"reviewed_by": "tester"}'
