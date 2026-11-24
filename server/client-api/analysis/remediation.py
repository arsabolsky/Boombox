"""Step 2 of the pipeline: write a multi-line script that fixes the findings.

Uses OpenAI (needs OPENAI_API_KEY), with reasoning turned up so it thinks the script
through first. OpenAI gets the findings plus the client's whole snapshot (so it can see
parent and child processes and connections) and the OS version.

Every script is checked automatically (analysis/checks.py). If the checks find problems,
they go back to OpenAI for one corrected attempt. If problems remain, they're added to
the explanation so the person reviewing it sees them.

The script is only a proposal. remediation/save.py stores it in the database, a
person approves or denies it on the dashboard, and only then does the client run it.
"""

import json
import os

from openai import OpenAI
from pydantic import BaseModel

from analysis.checks import check_script
from schemas import Client, Finding, QueryResult

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5")
REASONING_EFFORT = os.getenv("OPENAI_REASONING_EFFORT", "low")  # minimal, low, medium or high
ROWS_PER_QUERY = 200  # cap on snapshot rows sent per query, to keep requests a sensible size

INSTRUCTIONS = """\
You are the remediation step of an endpoint security tool. You get a list of findings
from one computer (rows of osquery results that looked suspicious or malicious), plus
the computer's whole snapshot for context. Write ONE multi-line script that fixes the
findings. A human reviews the script before it runs. It will run as root (Linux, bash)
or as SYSTEM (Windows, PowerShell).

Rules:
- Keep the script short and simple: a few clear steps, not a program.
- Linux hosts get a bash script, Windows hosts get a PowerShell script.
- Put each step on its own line, with a short comment above it saying what it does.
- Only touch what the findings point at. Kill specific PIDs; move (never delete) bad
  files into /var/lib/boombox/quarantine or C:\\ProgramData\\Boombox\\Quarantine;
  back up a cron job, service or scheduled task before disabling it.
- title: a short headline for the dashboard, e.g. "Reverse shell and crypto miner on web-01".
- explanation: 2-4 sentences for the person approving it: what was found, what the
  script does, and anything to double-check.
- attack_processes lists the processes in the attack: the flagged processes and everything
  they started. Stop all of them: children first, then parents. Never stop a process that
  is not in that list, such as the program that launched the attack. The script runs later
  than this snapshot (after a person approves it), so new child processes may have started
  since: also stop every current child of these processes when the script runs, not only
  the ones listed. Short-lived helpers like sleep stop by themselves once their parent is
  gone, so don't wait for them or count them as failures.
- At the end, check that every process you meant to stop is really gone. If anything
  failed, print what and why, and exit 1. Exit 0 only when everything was fixed.
- The Boombox client, its connection to the Boombox server, and Tailscale (tailscaled,
  100.x.x.x addresses) are normal. Never touch them.
"""

# Only the tips for the client's OS are added to the instructions.
LINUX_TIPS = """\
Linux tips (bash):
- Find and stop processes with pgrep -f and pkill -f, using a pattern from their command
  line, instead of reading /proc yourself. pgrep -f never matches itself, so use it for
  the final check too. Stop current children with pkill -9 -P <pid>.
- Interactive shells (like "bash -i") ignore the normal kill signal (SIGTERM). Send
  SIGTERM, wait a second, then SIGKILL (kill -9 / pkill -9 -f) anything still running.
- Never assign to bash's read-only variables: PPID, UID, EUID, BASHPID, GROUPS. Assigning
  to them stops the script on the spot. Use other names, e.g. proc_ppid.
"""

WINDOWS_TIPS = """\
Windows tips (PowerShell):
- Never use PowerShell's built-in variable names for your own variables or parameters:
  $PID, $Host, $Error, $Args, $Input, $_ . $PID is read-only, so "$pid = ..." or
  "param($Pid)" fails. Use other names, e.g. $procId.
- Find processes and their command lines with Get-CimInstance Win32_Process. Stop them
  with Stop-Process -Id <id> -Force. Find current children by ParentProcessId.  
- Paths in single quotes need single backslashes: 'C:\\Users\\Public\\x.exe' and
  '\\Microsoft\\Windows\\' (never doubled).
- In double-quoted strings, write "${name}:" rather than "$name:" when a colon follows a
  variable; "$name:" is a syntax error.
- Before removing a registry value, save it with reg export. Before disabling a scheduled
  task, save it with Export-ScheduledTask, then use Disable-ScheduledTask.
- Don't hide errors with -ErrorAction SilentlyContinue or empty catch { } blocks on the
  important steps; check the result and report what failed.
"""


class Fix(BaseModel):
    title: str
    script: str
    explanation: str


def make_script(client: Client, findings: list[Finding], results: list[QueryResult], attack: list[dict]) -> Fix:
    shell = "bash" if client.os == "linux" else "powershell"
    details = {
        "os": client.os,
        "os_version": client.os_version,
        "hostname": client.hostname,
        "findings": [f.model_dump() for f in findings],
        "attack_processes": [{k: p.get(k) for k in ("pid", "parent", "cmdline")} for p in attack],
        "snapshot": {r.name: r.rows[:ROWS_PER_QUERY] for r in results},
    }

    instructions = INSTRUCTIONS + "\n" + (LINUX_TIPS if client.os == "linux" else WINDOWS_TIPS)
    fix = ask_openai(json.dumps(details, indent=2), instructions)
    problems = check_script(fix.script, shell)

    if problems:
        # One corrected attempt: show OpenAI its script and what the checks found.
        retry = (
            json.dumps(details, indent=2)
            + "\n\nYour previous script:\n" + fix.script
            + "\n\nAutomatic checks found these problems. Fix all of them:\n- " + "\n- ".join(problems)
        )
        fix = ask_openai(retry, instructions)
        problems = check_script(fix.script, shell)

    if problems:
        fix.explanation += "\n\nWarning: automatic checks still report problems:\n- " + "\n- ".join(problems)
    return fix


def ask_openai(text: str, instructions: str) -> Fix:
    response = OpenAI().responses.parse(
        model=OPENAI_MODEL,
        instructions=instructions,
        input=text,
        reasoning={"effort": REASONING_EFFORT},
        text_format=Fix,
    )
    return response.output_parsed
