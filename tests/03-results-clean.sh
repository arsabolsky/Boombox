#!/usr/bin/env bash
# Step 3a (client): send back normal-looking query results. Expect "verdict": "benign".
# Needs the AI keys on the server; without them you get HTTP 503.
CLIENT_API="${CLIENT_API:-http://localhost:8080}"
CLIENT_ID="${CLIENT_ID:?Register first: run ./01-register.sh, then export CLIENT_ID=<the client_id>}"

curl -sS -w '\nHTTP %{http_code}\n' -X POST "$CLIENT_API/api/v1/results" \
  -H "X-Client-Id: $CLIENT_ID" \
  -H "Content-Type: application/json" \
  -d '{
  "results": [
    {"name": "processes", "rows": [
      {"pid": "1", "parent": "0", "name": "systemd", "path": "/usr/lib/systemd/systemd", "cmdline": "/sbin/init", "uid": "0", "on_disk": "1"},
      {"pid": "812", "parent": "1", "name": "sshd", "path": "/usr/sbin/sshd", "cmdline": "sshd: /usr/sbin/sshd -D", "uid": "0", "on_disk": "1"}
    ]},
    {"name": "cron_jobs", "rows": []}
  ]
}'
