# Client API

The Python (FastAPI) API that clients talk to. It hands out osquery queries, checks the
results with Jev, has OpenAI write a fix script for anything bad, and saves it in the
database for a person to review. The client picks up approved scripts by polling for them.

Run it with the rest of the stack: `docker compose up --build` from the repo root, then open
http://localhost:8080/docs.

## Files

| File | What it does |
|---|---|
| `main.py` | Puts the app together. Start reading here. |
| `auth.py` | Works out which client is calling, from the `X-Client-Id` header. |
| `schemas.py` | The JSON shapes going in and out. |
| `ingest/routes.py` | Register, poll for queries, and send results. |
| `ingest/queries.py` | The default osquery queries for each OS. Edit this to collect something new. |
| `triage/scope.py` | Rows never sent to Jev: the client's own requests, closed connections, Tailscale. |
| `triage/decision.py` | Asks Jev whether each row is benign, suspicious or malicious. |
| `analysis/remediation.py` | Asks OpenAI to write a fix script. |
| `remediation/save.py` | Saves fix scripts to the database and hands out approved ones. |
| `remediation/routes.py` | Poll for approved fix scripts. |
| `analysis/checks.py` | Checks each fix script before saving it: bash (bash -n, ShellCheck, read-only variables) and PowerShell (built-in variables, common mistakes). |
| `storage/database.py` | All the SQL (Aidan). |

## For the clients (Kade, Mateo)

### 1. Register once

```bash
curl -X POST localhost:8080/api/v1/clients -H "Content-Type: application/json" \
  -d '{"hostname": "ubuntu-01", "os": "linux", "os_version": "Ubuntu 24.04.1 LTS"}'
```

```json
{"client_id": "a7c55be4-b85b-4c7c-9666-82e863e4ea7f"}
```

All three fields are required:

- `hostname`: the machine's name
- `os`: `linux` or `windows`
- `os_version`: the OS's "pretty name", e.g. `Ubuntu 24.04.1 LTS` or `Windows 11 Pro`

Save the `client_id` it returns and send it on every other request:

```
X-Client-Id: a7c55be4-b85b-4c7c-9666-82e863e4ea7f
```

An unknown id gets a 401.

### 2. Then repeat forever

There are two things to poll. They can run in the same loop or in separate ones. Our
clients poll every 10 seconds by default (set in each client's `.env`). Every results
upload is a Jev call, so polling less often costs less. Both need the `X-Client-Id` header.

| Endpoint | Gives you | Then |
|---|---|---|
| `GET /api/v1/poll/queries` | osquery queries to run | run each one and `POST /api/v1/results` with the rows |
| `GET /api/v1/poll/remediations` | approved fix scripts | run each one |

### Queries

**`GET /api/v1/poll/queries`** returns:

```json
[
  {"name": "processes", "sql": "SELECT pid, parent, name, path, cmdline, uid, on_disk FROM processes"},
  {"name": "cron_jobs", "sql": "SELECT command, path FROM crontab"}
]
```

Run each one with osquery, e.g. `osqueryi --json "<sql>"`, and send all the rows back.

**Results body** (`POST /api/v1/results`):

```json
{
  "results": [
    {"name": "processes", "rows": [{"pid": "4242", "name": "bash", "cmdline": "bash -i >& /dev/tcp/…"}]},
    {"name": "cron_jobs", "rows": []},
    {"name": "admin_users", "error": "no such table"}
  ]
}
```

- `name` is the query's name from `/poll/queries`.
- `rows` is exactly what `osqueryi --json` printed. Don't convert anything.
- If a query failed, send `error` instead of `rows`.

The answer is the server's decision. If anything looked bad, a fix script is written in the
background (OpenAI can take a minute or two) and waits for a person to approve it.

```json
{"verdict": "malicious", "findings": [{"query": "processes", "row": {"pid": "4242"}, "verdict": "malicious", "confidence": 0.98}]}
```

### Remediations

**`GET /api/v1/poll/remediations`** returns the fix scripts a person approved:

```json
[
  {"id": 2, "script": "#!/usr/bin/env bash\necho 'hello'\n"}
]
```

Linux clients get bash scripts and Windows clients get PowerShell. Scripts are multi-line,
so save each one to a file and run the file:

- Linux: `bash /tmp/boombox-<id>.sh`
- Windows: `powershell -ExecutionPolicy Bypass -File C:\Windows\Temp\boombox-<id>.ps1`

**Each script is sent once.** As soon as `/poll/remediations` hands it to you, the server
marks it executed, so save it and run it right away. If your client crashes before running it, the
script is not sent again.

### Trying it by hand

The database starts empty, so register a client first. The easiest way is the browser page
at http://localhost:8080/docs, where every endpoint has a "Try it out" button. With `curl`:

```bash
# 1. Register and save the client_id
curl -s -X POST localhost:8080/api/v1/clients -H 'Content-Type: application/json' \
  -d '{"hostname": "test-box", "os": "linux", "os_version": "Ubuntu 24.04 LTS"}'

# 2. Poll for queries
curl -s localhost:8080/api/v1/poll/queries -H "X-Client-Id: <client_id>"

# 3. Send results (see the format above). Bad rows get a fix script about a minute later.
curl -s -X POST localhost:8080/api/v1/results -H "X-Client-Id: <client_id>" \
  -H 'Content-Type: application/json' -d @results.json

# 4. Approve the fix on the dashboard (http://localhost), then poll for it (sent once)
curl -s localhost:8080/api/v1/poll/remediations -H "X-Client-Id: <client_id>"
```

`POST /api/v1/results` needs the AI keys on the server. Without them it answers 503, which
still tells you your request was in the right format (a wrong format gets a 422).

## Good to know

- **The client_id is the only "login".** This is a proof of concept.
- **One fix per attack.** Clients send the same results on every poll, and one attack shows
  up as several rows (a process, its children, its connection). Processes are grouped by
  family (following parent processes up), so while an attack has a fix waiting for review
  or approved, it doesn't get another one. A different attack gets its own fix right away.
  Once a fix is denied or sent to the client, anything still there gets a new fix.
  (`remediation/save.py`)
- **Fix scripts run as whatever user the client runs as.** Only approved scripts are handed out.
- **To change the AI:** `triage/decision.py` and `analysis/remediation.py` each have one
  function (`decide` and `make_script`). Change what's inside; keep the inputs and outputs.
- **To add a package:** run `uv add <package>` here, then commit `pyproject.toml` and `uv.lock`.
- **Running without Docker:** start the database (`docker compose up database`), then from
  this folder with the variables from `.env` exported: `uv run uvicorn main:app --reload --port 8080`.
