"""Runs inside a test machine: runs every query in queries.json with osquery and
saves the results to snapshots/<name>.json.

Usage (from the ai/ folder):   docker compose exec compromised python3 /lab/collect.py compromised

The snapshot has the same shape as the backend API's POST /results body, plus a
"client" block, so it can be replayed against the API later.
"""

import json
import socket
import subprocess
import sys

name = sys.argv[1]
queries = json.load(open("/lab/queries.json"))

results = []
for query_name, sql in queries.items():
    run = subprocess.run(["osqueryi", "--json", sql], capture_output=True, text=True, timeout=60)
    if run.returncode == 0:
        results.append({"name": query_name, "rows": json.loads(run.stdout or "[]")})
    else:
        results.append({"name": query_name, "error": run.stderr.strip()})

snapshot = {
    "client": {"client_id": name, "os": "linux", "hostname": socket.gethostname()},
    "results": results,
}
with open(f"/lab/snapshots/{name}.json", "w") as f:
    json.dump(snapshot, f, indent=2)

rows = sum(len(r.get("rows", [])) for r in results)
errors = [r["name"] for r in results if "error" in r]
print(f"{name}: {rows} rows from {len(results)} queries" + (f", failed: {errors}" if errors else ""))
