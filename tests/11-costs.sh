#!/usr/bin/env bash
# Totals for every AI call so far: number of calls, average time, tokens, estimated cost.
# Every single call is also printed in the client API log as an "[ai]" line.
cd "$(dirname "$0")/.." || exit 1
docker compose exec -T client-api uv run --locked python usage.py
