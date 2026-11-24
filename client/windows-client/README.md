# Windows Client

Runs on every monitored Windows host (Mateo). There are two versions:

| Folder | Status |
|---|---|
| [`Windows-client-go/`](Windows-client-go/README.md) | **Current.** Go, built as `BoomboxClient.exe`, installed as a Windows service with NSSM. Uses the current client API (registration, `poll/queries`, `results`, `poll/remediations`). |
| `Windows-client-py/` | Earlier Python version (`agent.py`), written against an older version of the API. Kept for reference. |

Both need osquery installed (https://osquery.io/downloads). Build and install steps are in
[`Windows-client-go/README.md`](Windows-client-go/README.md).
