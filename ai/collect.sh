#!/usr/bin/env bash
# Collects a fresh osquery snapshot from every test machine into snapshots/.
set -euo pipefail
cd "$(dirname "$0")"
for machine in clean compromised; do
  docker compose exec -T "$machine" python3 /lab/collect.py "$machine"
done
