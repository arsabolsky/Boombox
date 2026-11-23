#!/usr/bin/env bash
# Stop the demo machines and the main Boombox stack.
cd "$(dirname "$0")"
docker compose down
(cd .. && docker compose down)
