# Client API

The Python (FastAPI) API that clients talk to. It hands out osquery queries, checks the
results with Jev, has OpenAI write a fix script for anything bad, and saves it in the
database for a person to review. Approved scripts go back to the client on its next poll.

Run it with the rest of the stack: `docker compose up --build` from the repo root, then open
http://localhost:8080/docs.

## Files

| File | What it does |
|---|---|
| `main.py` | Puts the app together. Start reading here. |
| `auth.py` | Works out which client is calling, from the `X-Client-Id` header. |
| `schemas.py` | The JSON shapes going in and out. |
| `ingest/routes.py` | Register, poll and results endpoints. |
| `ingest/queries.py` | The default osquery queries for each OS. Edit this to collect something new. |
| `triage/decision.py` | Asks Jev whether each row is benign, suspicious or malicious. |
| `analysis/remediation.py` | Asks OpenAI to write a fix script. |
| `remediation/save.py` | Saves fix scripts to the database and finds approved ones. |
| `remediation/routes.py` | The endpoint clients use to report a script's result. |
| `storage/database.py` | All the SQL (Aiden). |
| `examples/` | Sample query results and `demo.sh`, which runs a whole client loop. |

## For the clients (Kade, Mateo)

### 1. Register once

```bash
curl -X POST localhost:8080/api/v1/clients -H "Content-Type: application/json" \
  -d '{"hostname": "ubuntu-01", "os": "linux", "os_version": "Ubuntu 24.04"}'
```

```json
{"client_id": "a7c55be4-b85b-4c7c-9666-82e863e4ea7f"}
```

`os` must be `linux` or `windows`. Save the `client_id` and send it on every other request:

```
X-Client-Id: a7c55be4-b85b-4c7c-9666-82e863e4ea7f
```

An unknown id gets a 401.

### 2. Then repeat forever

1. `GET /api/v1/poll`
2. Run every query in `queries` with osquery, e.g. `osqueryi --json "<sql>"`, and
   `POST /api/v1/results` with the rows.
3. Run every script in `scripts` and report each one with
   `POST /api/v1/remediations/{id}/result`.
4. Wait `poll_interval` seconds.

**Poll response:**

```json
{
  "poll_interval": 300,
  "queries": [
    {"name": "processes", "sql": "SELECT pid, parent, name, path, cmdline, uid, on_disk FROM processes"},
    {"name": "cron_jobs", "sql": "SELECT command, path FROM crontab"}
  ],
  "scripts": [
    {"id": 2, "shell": "bash", "script": "#!/usr/bin/env bash\necho 'hello'\n"}
  ]
}
```

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

- `name` is the query's name from the poll.
- `rows` is exactly what `osqueryi --json` printed. Don't convert anything.
- If a query failed, send `error` instead of `rows`.

The answer is the server's decision. If anything looked bad, a fix script is written in the
background (OpenAI can take a minute or two) and waits for a person to approve it.

```json
{"verdict": "malicious", "findings": [{"query": "processes", "row": {"pid": "4242"}, "verdict": "malicious", "confidence": 0.98}]}
```

**Running a script:** scripts are multi-line, so save each one to a file and run the file:

- Linux: `bash /tmp/boombox-<id>.sh`
- Windows: `powershell -ExecutionPolicy Bypass -File C:\Windows\Temp\boombox-<id>.ps1`

Then report the result. `exit_code` 0 means it worked:

```bash
curl -X POST localhost:8080/api/v1/remediations/2/result -H "X-Client-Id: <your id>" \
  -H "Content-Type: application/json" -d '{"exit_code": 0, "output": "what the script printed"}'
```

A script is handed out on every poll until you report it.

### Testing without the AI or the dashboard

The sample data has clients you can use right away:

| Client | `X-Client-Id` | What it has |
|---|---|---|
| Linux, `ubuntu-01` | `33333333-3333-4333-8333-333333333333` | one approved harmless test script |
| Windows, `LAPTOP-02` | `22222222-2222-4222-8222-222222222222` | one approved harmless test script, plus a custom query |

The test scripts print some info and write `boombox-test.txt` to the temp folder.
`examples/demo.sh` runs the whole Linux loop. To get the test scripts back after you've
run them, reset the database: `docker compose down -v && docker compose up`.

`POST /api/v1/results` needs the AI keys on the server. Without them it answers 503, which
still tells you your request was in the right format (a wrong format gets a 422).

## Good to know

- **The client_id is the only "login".** This is a proof of concept.
- **Fix scripts run as whatever user the client runs as.** Only approved scripts are handed out.
- **To change the AI:** `triage/decision.py` and `analysis/remediation.py` each have one
  function (`decide` and `make_script`). Change what's inside; keep the inputs and outputs.
- **To add a package:** run `uv add <package>` here, then commit `pyproject.toml` and `uv.lock`.
- **Running without Docker:** start the database (`docker compose up database`), then from
  this folder with the variables from `.env` exported: `uv run uvicorn main:app --reload --port 8080`.
