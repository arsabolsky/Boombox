#!/usr/bin/env bash
# Step 7 (dashboard): give one client an extra osquery query. It shows up in that
# client's queries (02-poll-queries.sh) every time, while enabled.
CLIENT_ID="${CLIENT_ID:-33333333-3333-4333-8333-333333333333}"   # sample Linux client
DASHBOARD_API="${DASHBOARD_API:-http://localhost:8000}"

curl -sS -w '\nHTTP %{http_code}\n' -X POST "$DASHBOARD_API/api/v1/client-queries" \
  -H "Content-Type: application/json" \
  -d "{
  \"client_id\": \"$CLIENT_ID\",
  \"query_name\": \"tmp_files\",
  \"enabled\": true,
  \"query_configuration\": {\"query\": \"SELECT path FROM file WHERE directory = '/tmp'\"}
}"
