"""Automatic checks on a fix script before a person sees it.

check_script() returns a list of problems (empty means it passed). Only bash scripts are
checked; there's no PowerShell checker in the server's container.

  1. bash -n      syntax errors
  2. ShellCheck   common bash mistakes (warnings and errors only)
  3. our own      assigning to bash's read-only variables, which stops the script on the
                  spot. ShellCheck doesn't catch it, and an earlier AI fix failed because of it.
"""

import re
import subprocess
import tempfile

READ_ONLY = ("PPID", "UID", "EUID", "BASHPID", "GROUPS", "SHELLOPTS", "BASHOPTS")
ASSIGNS_READ_ONLY = re.compile(r"^\s*(?:local\s+|export\s+|declare\s+)?(" + "|".join(READ_ONLY) + r")=", re.M)


def check_script(script: str, shell: str) -> list[str]:
    if shell != "bash":
        return []

    problems = []
    with tempfile.NamedTemporaryFile("w", suffix=".sh") as f:
        f.write(script)
        f.flush()

        syntax = subprocess.run(["bash", "-n", f.name], capture_output=True, text=True)
        if syntax.returncode != 0:
            problems.append("bash syntax error: " + syntax.stderr.replace(f.name, "script").strip())

        lint = subprocess.run(["shellcheck", "-S", "warning", "-f", "gcc", f.name], capture_output=True, text=True)
        problems += [line.replace(f.name, "script") for line in lint.stdout.splitlines() if line.strip()]

    for match in ASSIGNS_READ_ONLY.finditer(script):
        line = script.count("\n", 0, match.start()) + 1
        problems.append(
            f"script:{line}: assigns to {match.group(1)}, a read-only bash variable. "
            "That stops the script at this line. Use another name, e.g. proc_ppid."
        )
    return problems
