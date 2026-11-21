"""Fix scripts in the database: saving new ones, handing out approved ones.

A fix script goes through these statuses (the remediations table):

    pending_review  ->  approved  ->  executed
                    ->  denied

  - write_and_save_fix()  saves a new one as pending_review (called by /api/v1/results)
  - a person approves or denies it on the dashboard (server/dashboard-api)
  - approved_scripts()    hands approved ones to the client and marks them executed
                          (called by /api/v1/poll/remediations)

No repeats: clients send the same results on every poll, and one attack shows up as
several rows (a process, its children, its network connection). So each finding gets a
key, and a finding is skipped if its key already has an open fix script (pending_review
or approved), or if a fix for it is being written right now:

  - processes and connections: the attack's "family", i.e. the top process you reach by
    following parent processes up. Everything a reverse shell starts shares one key.
  - anything else (cron jobs, users, ...): the row itself, without pid and parent.

A different attack gets a different key, so it gets its own fix right away. Once a fix
is denied or sent to the client, a problem that's still there gets a new fix.
"""

import hashlib
import json
import threading

from analysis.remediation import make_script
from schemas import Client, Decision, Finding, QueryResult, Remediation
from storage.database import insert_event, insert_remediation, open_fingerprints, take_approved_remediations

SEVERITY = {"malicious": "high", "suspicious": "medium"}

# Fingerprints whose fix is being written right now (OpenAI takes about a minute).
_in_progress: set[str] = set()
_lock = threading.Lock()


def family_key(pid: str, processes: dict) -> str:
    """Follow parents up to the top of the process's family and name the family after it."""
    top = processes[pid]
    for _ in range(50):  # a limit, in case bad data lists a process as its own parent
        parent = str(top.get("parent"))
        if parent not in processes or parent in ("0", "1"):  # stop below PID 1, the first process
            break
        top = processes[parent]
    text = "family: " + str(top.get("cmdline") or top.get("name"))
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def fingerprint(finding: Finding, processes: dict) -> str:
    """The key for a finding: its process family if it has a known process, else its row."""
    pid = str(finding.row.get("pid", ""))
    if pid in processes:
        return family_key(pid, processes)
    else:
        row = {k: v for k, v in finding.row.items() if k not in ("pid", "parent")}
        text = json.dumps({"query": finding.query, "row": row}, sort_keys=True)
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def write_and_save_fix(client: Client, decision: Decision, results: list[QueryResult]):
    """Runs after /api/v1/results has answered: write the script and save it for review."""
    processes = {str(r["pid"]): r for q in results if q.name == "processes" for r in q.rows if "pid" in r}
    groups: dict[str, list[Finding]] = {}
    for f in decision.findings:
        groups.setdefault(fingerprint(f, processes), []).append(f)

    with _lock:
        skip = open_fingerprints(client.client_id) | _in_progress
        new = {key: fs for key, fs in groups.items() if key not in skip}
        _in_progress.update(new)

    if not new:
        print(f"{client.hostname}: every finding already has an open fix script, not making another")
        return

    try:
        findings = [f for fs in new.values() for f in fs]
        verdict = "malicious" if any(f.verdict == "malicious" for f in findings) else "suspicious"
        # Every process in the flagged families, so the fix can stop the whole attack.
        attack = [p for pid, p in processes.items() if family_key(pid, processes) in new]
        fix = make_script(client, findings, results, attack)

        # The database stores each remediation against the event that caused it.
        event_id = insert_event(
            client_id=client.client_id,
            event_type="findings",
            raw_data={
                "verdict": verdict,
                "findings": [f.model_dump() for f in findings],
                "fingerprints": list(new),
            },
        )
        insert_remediation(
            event_id=event_id,
            title=fix.title,
            summary=fix.explanation,
            proposed_script=fix.script,
            severity=SEVERITY[verdict],
        )
    finally:
        with _lock:
            _in_progress.difference_update(new)


def approved_scripts(client: Client) -> list[Remediation]:
    """This client's approved fix scripts. Each one is handed out once, then marked executed."""
    return [
        Remediation(id=remediation_id, script=script)
        for remediation_id, script in take_approved_remediations(client.client_id)
        if script
    ]
