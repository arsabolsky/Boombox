#!/usr/bin/env bash
# Step 2 (client): get the osquery queries to run. Run them, then send the rows (steps 3a/3b).
CLIENT_API="${CLIENT_API:-http://localhost:8080}"
CLIENT_ID="${CLIENT_ID:?Register first: run ./01-register.sh, then export CLIENT_ID=<the client_id>}"

curl -sS -w '\nHTTP %{http_code}\n' "$CLIENT_API/api/v1/poll/queries" \
  -H "X-Client-Id: $CLIENT_ID"
