"""A minimal Boombox client for the demo (a stand-in until the real Linux client works).

Loop: poll queries -> run them with osquery -> send results -> poll remediations -> run them.
"""

import json
import os
import socket
import subprocess
import time
import urllib.error
import urllib.request

API = os.environ["CLIENT_API"]
POLL_SECONDS = int(os.environ.get("POLL_SECONDS", "20"))


def call(method, path, body=None, client_id=None):
    req = urllib.request.Request(API + path, method=method)
    if client_id:
        req.add_header("X-Client-Id", client_id)
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, data, timeout=120) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        print(f"  ! {method} {path} -> HTTP {e.code}: {e.read().decode()[:200]}")
        return None


def pretty_name():
    for line in open("/etc/os-release"):
        if line.startswith("PRETTY_NAME="):
            return line.split("=", 1)[1].strip().strip('"')
    return "Linux"


def wait_for_api():
    while True:
        try:
            urllib.request.urlopen(API.rsplit("/api/v1", 1)[0] + "/health", timeout=5)
            return
        except Exception:
            print("[client] waiting for the client API...")
            time.sleep(3)


wait_for_api()
reg = call("POST", "/clients", {"hostname": socket.gethostname(), "os": "linux", "os_version": pretty_name()})
client_id = reg["client_id"]
print(f"[client] registered as {client_id}")

while True:
    print(f"\n[client] {time.strftime('%H:%M:%S')} polling for queries")
    results = []
    for q in call("GET", "/poll/queries", client_id=client_id) or []:
        run = subprocess.run(["osqueryi", "--json", q["sql"]], capture_output=True, text=True, timeout=60)
        if run.returncode == 0:
            rows = json.loads(run.stdout or "[]")
            results.append({"name": q["name"], "rows": rows})
            print(f"  ran {q['name']}: {len(rows)} rows")
        else:
            results.append({"name": q["name"], "error": run.stderr.strip()[:300]})
            print(f"  ran {q['name']}: ERROR")

    decision = call("POST", "/results", {"results": results}, client_id=client_id)
    if decision:
        print(f"  verdict: {decision['verdict']}")
        for f in decision["findings"]:
            row = f["row"]
            what = row.get("cmdline") or row.get("command") or row.get("process_name") or json.dumps(row)[:80]
            print(f"    {f['verdict']} ({f['confidence']:.2f}) {f['query']}: {str(what)[:90]}")

    for fix in call("GET", "/poll/remediations", client_id=client_id) or []:
        print(f"\n[client] running approved fix script #{fix['id']}:")
        path = f"/tmp/boombox-{fix['id']}.sh"
        with open(path, "w") as fh:
            fh.write(fix["script"])
        run = subprocess.run(["bash", path], capture_output=True, text=True, timeout=300)
        print((run.stdout + run.stderr).strip()[:2000] or "(no output)")
        print(f"[client] fix #{fix['id']} exited {run.returncode}")

    time.sleep(POLL_SECONDS)
