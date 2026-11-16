#!/usr/bin/env bash
# Walks through the whole flow against a running server (docker compose up).
# Needs curl and python3 (only used to pretty-print JSON).
set -euo pipefail
URL="${URL:-http://localhost:8000}"
HERE="$(cd "$(dirname "$0")" && pwd)"

# Who we are. Later, real auth replaces these headers with a token.
ME=(-H "X-Client-Id: linux-vm-1" -H "X-Client-OS: linux" -H "X-Client-Hostname: ubuntu-client")

echo "== 0. Who does the API think I am?"
curl -s "$URL/whoami" "${ME[@]}" | python3 -m json.tool

echo "== 1. Poll: what should I run?"
curl -s "$URL/poll" "${ME[@]}" | python3 -c '
import sys, json
for q in json.load(sys.stdin)["queries"]:
    print(" ", q["name"], "->", q["sql"][:70])'

echo "== 2. Send back the rows (here: a reverse shell, a miner and a bad cron job)"
curl -s -X POST "$URL/results" "${ME[@]}" -H "Content-Type: application/json" -d @"$HERE/results-linux.json" | python3 -c '
import sys, json
body = json.load(sys.stdin)
print("verdict:", body["decision"]["verdict"], "| findings:", len(body["decision"]["findings"]))
r = body["remediation"]
print("\nSent to the remediations API:", r["id"], "(" + r["shell"] + ")\n")
print(r["explanation"], "\n")
print(r["script"])'
