# Remediation

Getting fix scripts to the remediations service (Aiden), which handles
approval and running them on the client.

- `handoff.py`: sends each script to `REMEDIATION_API_URL`, or prints it if that isn't set.
- `mock.py`: a stand-in for the remediations service so client devs can build now. Delete it
  (and its line in `main.py`) when the real API exists.
