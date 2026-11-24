# Triage

The decision model: is anything in the client's results bad?

- `scope.py`: removes rows that are our own normal traffic before anything else sees
  them: the Boombox client and osquery (by name or by the program's file name), the
  client's connections to the server, closed connections (`pid -1`), and Tailscale.
- `decision.py`: asks TypeSafe Jev about every remaining row: benign, suspicious or
  malicious, with a confidence. Each row gets context fields first (`_parent`,
  `_connections`, `_process`) so Jev can see who started a process and where it connects.
  Anything not benign with at least 50% confidence becomes a finding.
