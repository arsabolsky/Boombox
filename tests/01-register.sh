#!/usr/bin/env bash
# Step 1 (client): register a new client. Save the client_id it returns.
# Usage: ./01-register.sh [linux|windows]
CLIENT_API="${CLIENT_API:-http://localhost:8080}"
OS="${1:-linux}"

curl -sS -w '\nHTTP %{http_code}\n' -X POST "$CLIENT_API/api/v1/clients" \
  -H "Content-Type: application/json" \
  -d "{\"hostname\": \"test-$OS\", \"os\": \"$OS\", \"os_version\": \"Test OS 1.0\"}"

echo "Use it in the next steps with:  export CLIENT_ID=<the client_id above>"
