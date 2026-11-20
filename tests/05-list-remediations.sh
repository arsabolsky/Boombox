#!/usr/bin/env bash
# Step 4 (dashboard): list every fix script and its status
# (pending_review, approved, denied, executed). Note the "id" of the one you want.
DASHBOARD_API="${DASHBOARD_API:-http://localhost:8000}"

curl -sS -w '\nHTTP %{http_code}\n' "$DASHBOARD_API/api/v1/remediations"
