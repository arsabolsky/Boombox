#!/usr/bin/env bash
# Step 6 (client): get approved fix scripts to run. Each one is sent only once, so running
# this again right away returns [].
CLIENT_API="${CLIENT_API:-http://localhost:8080}"
CLIENT_ID="${CLIENT_ID:?Register first: run ./01-register.sh, then export CLIENT_ID=<the client_id>}"

curl -sS -w '\nHTTP %{http_code}\n' "$CLIENT_API/api/v1/poll/remediations" \
  -H "X-Client-Id: $CLIENT_ID"
