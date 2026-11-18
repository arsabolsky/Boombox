#!/usr/bin/env bash
# Walks through the whole flow against a running server (docker compose up).
# Needs curl and uv (uv runs Python to pretty-print JSON).
set -euo pipefail
URL="${URL:-http://localhost:8000}"
HERE="$(cd "$(dirname "$0")" && pwd)"

# Who we are. Later, real auth replaces these headers with a token.
ME=(-H "X-Client-Id: linux-vm-1" -H "X-Client-OS: linux" -H "X-Client-Hostname: ubuntu-client")

echo "== 1. Poll: what should I run?"
curl -s "$URL/poll" "${ME[@]}" | uv run --no-project python -c '
import sys, json
for q in json.load(sys.stdin)["queries"]:
    print(" ", q["name"], "->", q["sql"][:70])'

echo "== 2. Send back the rows (here: a reverse shell, a miner and a bad cron job)"
curl -s -X POST "$URL/results" "${ME[@]}" -H "Content-Type: application/json" -d @"$HERE/results-linux.json" | uv run --no-project python -c '
import sys, json
body = json.load(sys.stdin)
print("verdict:", body["decision"]["verdict"], "| findings:", len(body["decision"]["findings"]))
print("fix script being written in the background:", body["remediation_id"])'
echo "   (see it with: docker compose logs -f api)"

echo "== 3. Mock remediations service: get a script to run"
SCRIPT=$(curl -s "$URL/mock/remediations/commands" "${ME[@]}" | uv run --no-project python -c 'import sys, json; print(json.load(sys.stdin)[0]["script"])')
echo "$SCRIPT"

echo "== 4. Run it the way a client would (save to a file, run the file) and report back"
FILE=$(mktemp /tmp/boombox-example-XXXX.sh)
echo "$SCRIPT" > "$FILE"
OUTPUT=$(bash "$FILE"); CODE=$?
rm -f "$FILE" /tmp/boombox-example.txt
echo "$OUTPUT"
uv run --no-project python -c 'import json, sys; print(json.dumps({"exit_code": int(sys.argv[1]), "output": sys.argv[2]}))' "$CODE" "$OUTPUT" \
  | curl -s -X POST "$URL/mock/remediations/commands/example-bash/result" "${ME[@]}" -H "Content-Type: application/json" -d @-
echo
