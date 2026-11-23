"""Automatic checks on a fix script before a person sees it.

check_script() returns a list of problems (empty means it passed).

Bash (Linux):
  1. bash -n      syntax errors
  2. ShellCheck   common bash mistakes (warnings and errors only)
  3. our own      assigning to bash's read-only variables, which stops the script on the
                  spot. ShellCheck doesn't catch it, and an earlier AI fix failed because of it.

PowerShell (Windows): there's no PowerShell in the server's container, so only our own
pattern checks for mistakes earlier AI fixes made:
  - using built-in variable names ($PID, $Host, ...) for your own variables
  - "$name:" inside a string, which PowerShell reads as a syntax error
  - doubled backslashes inside single quotes ('\\Microsoft\\Windows'), which point
    to the wrong place
  - empty catch { } blocks, which hide failures
"""

import re
import subprocess
import tempfile

READ_ONLY = ("PPID", "UID", "EUID", "BASHPID", "GROUPS", "SHELLOPTS", "BASHOPTS")
ASSIGNS_READ_ONLY = re.compile(r"^\s*(?:local\s+|export\s+|declare\s+)?(" + "|".join(READ_ONLY) + r")=", re.M)


PS_BUILT_IN = r"(PID|Host|Error|Args|Input|PSItem)"
PS_MISUSE = re.compile(
    r"\$" + PS_BUILT_IN + r"\s*=(?!=)"                     # $pid = 5
    r"|param\s*\([^)]*\$" + PS_BUILT_IN + r"\b"             # param([int]$Pid)
    r"|foreach\s*\(\s*\$" + PS_BUILT_IN + r"\s+in\b",      # foreach ($pid in ...)
    re.IGNORECASE,
)


PS_OTHER = [
    (re.compile(r"\$[A-Za-z_]\w*:(?![\w{$])"),
     'puts a colon right after a variable ("$name:"), which PowerShell reads as a syntax '
     'error. Write "${name}:" instead.'),
    (re.compile(r"'[^'\n]+\\\\[^'\n]*'"),
     "has doubled backslashes inside single quotes. Single-quoted strings don't need "
     "escaping, so this points to the wrong path. Use single backslashes."),
    (re.compile(r"catch\s*\{\s*\}"),
     "has an empty catch { } block, which hides failures. Report the error instead."),
]


REGEX_OPERATOR = re.compile(r"-[ci]?(not)?(match|replace|split)\s*$", re.IGNORECASE)


def check_powershell(script: str) -> list[str]:
    problems = []
    for pattern, message in PS_OTHER:
        for match in pattern.finditer(script):
            before = script[: match.start()]
            if "backslashes" in message and REGEX_OPERATOR.search(before):
                continue  # regexes (-match '\\d') do need doubled backslashes
            problems.append(f"script:{script.count(chr(10), 0, match.start()) + 1}: {message}")
    for match in PS_MISUSE.finditer(script):
        line = script.count("\n", 0, match.start()) + 1
        name = next(g for g in match.groups() if g)
        problems.append(
            f"script:{line}: uses ${name} as its own variable, but ${name} is built into "
            "PowerShell (and $PID is read-only). Use another name, e.g. $procId."
        )
    return problems


def check_script(script: str, shell: str) -> list[str]:
    if shell == "powershell":
        return check_powershell(script)

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
