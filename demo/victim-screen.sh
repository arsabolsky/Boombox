#!/usr/bin/env bash
# VICTIM pane: show the victim's "hacked screen". Messages from the attacker appear here.
cd "$(dirname "$0")"
docker compose exec victim tail -n 30 -f /tmp/hacked-screen
