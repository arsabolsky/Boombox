#!/usr/bin/env bash
# Fresh start: empty database, main Boombox stack, then the victim and attacker machines.
set -e
cd "$(dirname "$0")"
docker compose down 2>/dev/null || true
(cd .. && docker compose down -v && docker compose up -d --build --wait)
docker compose up -d --build
echo
echo "Ready. Next:"
echo "  victim pane:   ./victim-screen.sh"
echo "  attacker pane: ./attacker-listen.sh   (then paste funny-messages.txt)"
echo "  dashboard:     http://localhost"
