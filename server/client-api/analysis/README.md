# Analysis

The remediation model: writes one fix script for the findings.

- `remediation.py`: sends OpenAI the findings, the attack's processes, the client's whole
  snapshot and its OS version, and gets back a title, an explanation for the reviewer,
  and one script (bash for Linux, PowerShell for Windows). The prompt has shared rules
  plus tips for the client's OS only. Reasoning effort is low by default
  (`OPENAI_REASONING_EFFORT`).
- `checks.py`: checks every script before it's saved. Bash: `bash -n`, ShellCheck, and
  assignments to read-only variables (`PPID`, `UID`, ...). PowerShell: built-in variable
  names (`$PID`, ...), `"$name:"` in strings, doubled backslashes in single quotes, and
  empty `catch { }` blocks. If a check fails, the errors go back to OpenAI for one
  corrected try; anything still wrong is added to the explanation as a warning.
