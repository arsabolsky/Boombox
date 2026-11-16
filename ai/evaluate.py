"""Run the models on the saved snapshots and score them against the answer keys.

    docker compose run --rm ai                         all machines, real models if keys are set
    docker compose run --rm ai python evaluate.py compromised
    docker compose run --rm -e DECISION_BACKEND=rules ai      force the regex rules (free)
    docker compose run --rm -e REMEDIATION_BACKEND=template ai   skip OpenAI (free)

For each machine it prints what was caught, missed and wrongly flagged, then
saves everything (findings + the fix script) to results/<machine>.json and
results/<machine>.sh so you can read the script.
"""

import json
import subprocess
import sys
import time
from pathlib import Path

from decision import decide
from remediation import make_script

HERE = Path(__file__).parent


def matches(finding: dict, item: dict) -> bool:
    return finding["query"] == item["query"] and item["contains"] in json.dumps(finding["row"])


def score(findings: list[dict], expected: list[dict]) -> dict:
    required = [item for item in expected if not item.get("optional")]
    caught = [item for item in required if any(matches(f, item) for f in findings)]
    missed = [item for item in required if item not in caught]
    false_alarms = [f for f in findings if not any(matches(f, item) for item in expected)]
    return {"caught": caught, "missed": missed, "false_alarms": false_alarms, "required": len(required)}


def evaluate(machine: str) -> dict:
    snapshot = json.loads((HERE / "snapshots" / f"{machine}.json").read_text())
    expected = json.loads((HERE / "expected" / f"{machine}.json").read_text())["should_flag"]
    client = snapshot["client"]
    rows = sum(len(r.get("rows", [])) for r in snapshot["results"])

    print(f"\n=== {machine} ({client['hostname']}, {rows} rows) ===")
    started = time.time()
    decision = decide(client["os"], snapshot["results"])
    took = time.time() - started
    result = score(decision["findings"], expected)

    print(f"decision: {decision['verdict']}  [{decision['backend']}, {took:.1f}s]")
    print(f"caught {len(result['caught'])}/{result['required']}, false alarms: {len(result['false_alarms'])}")
    for item in result["caught"]:
        print(f"  ✓ {item['what']}")
    for item in result["missed"]:
        print(f"  ✗ MISSED: {item['what']}")
    for f in result["false_alarms"]:
        print(f"  ! FALSE ALARM ({f['verdict']} {f['confidence']:.2f}) in {f['query']}: {json.dumps(f['row'])[:120]}")

    output = {"machine": machine, "decision": decision, "score": {k: len(v) if isinstance(v, list) else v for k, v in result.items()}}
    if decision["findings"]:
        started = time.time()
        fix = make_script(client["os"], client["hostname"], decision["findings"])
        print(f"fix script: {len(fix['script'].splitlines())} lines  [{fix['backend']}, {time.time() - started:.1f}s]")
        extension = "sh" if fix["shell"] == "bash" else "ps1"
        (HERE / "results" / f"{machine}.{extension}").write_text(fix["script"])
        if fix["shell"] == "bash":
            check = subprocess.run(["bash", "-n"], input=fix["script"], text=True, capture_output=True)
            print("  bash syntax:", "ok" if check.returncode == 0 else f"ERROR {check.stderr.strip()}")
        output["fix"] = fix

    (HERE / "results" / f"{machine}.json").write_text(json.dumps(output, indent=2))
    return result


if __name__ == "__main__":
    (HERE / "results").mkdir(exist_ok=True)
    machines = sys.argv[1:] or [p.stem for p in sorted((HERE / "expected").glob("*.json"))]
    totals = {"caught": 0, "required": 0, "false_alarms": 0}
    for machine in machines:
        r = evaluate(machine)
        totals["caught"] += len(r["caught"])
        totals["required"] += r["required"]
        totals["false_alarms"] += len(r["false_alarms"])
    print(f"\nTOTAL: caught {totals['caught']}/{totals['required']}, false alarms: {totals['false_alarms']}")
    print("Details and fix scripts: ai/results/")
