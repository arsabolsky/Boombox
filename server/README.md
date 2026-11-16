# Boombox backend API

A small FastAPI app. It tells clients what to collect, decides whether what they sent back
looks bad, and writes a multi-line script to fix it. That script is handed to the
**remediations API** (another team's service), which takes care of approval and running it
on the client.

## Files

| File | What it does |
|---|---|
| `main.py` | All the endpoints. Start reading here. |
| `auth.py` | Works out which client is calling. The one place to change for real authentication. |
| `schemas.py` | The JSON shapes going in and out. |
| `queries.py` | The osquery queries clients run. Edit this to collect something new. |
| `decision.py` | Step 1: is anything bad? Uses TypeSafe Jev, or simple rules when there's no key. |
| `remediation.py` | Step 2: write a fix script. Uses OpenAI, or a template when there's no key. |
| `handoff.py` | Step 3: send the script to the remediations API. The one place to change for that API. |
| `mock_remediations.py` | A stand-in for the remediations API, so client devs can build now. Delete when the real one exists. |
| `tests/test_api.py` | Tests for the whole flow. |
| `examples/` | Sample client data, `demo.sh` (runs the whole flow), and harmless example scripts. |

The other folders (`ingest/`, `triage/`, ...) are the original placeholders from the repo
skeleton. This code doesn't use them.

## Run it

```bash
docker compose up --build              # from the repo root
open http://localhost:8000/docs        # Swagger UI: try every endpoint from the browser
server/examples/demo.sh                # or watch the whole flow in the terminal
docker compose run --rm api pytest     # run the tests
```

Without API keys, the server uses built-in rules and template scripts, so you can build
and test against it for free. Settings go in a `.env` file in the repo root (copy
`.env.example`):

```
TYPESAFE_API_KEY=...      # decision model (Jev)
OPENAI_API_KEY=...        # remediation model
REMEDIATION_API_URL=...   # where scripts are sent; blank = printed to `docker compose logs -f api`
```

## The flow

```
 client                          our API                             remediations API
   │ GET /poll ───────────────────▶│                                   (other team)
   │◀── queries ───────────────────│                                       │
   │                               │                                       │
   │ run each query with osquery   │                                       │
   │                               │                                       │
   │ POST /results ───────────────▶│ decision.py:    anything bad?         │
   │◀── decision ──────────────────│ remediation.py: write a fix script    │
   │                               │ handoff.py ── POST /remediations ────▶│ approval,
   │                               │                                       │ delivery,
   │◀──────────────── approved scripts, however the remediations API does it ─┘ tracking
```

Our API never sends scripts to clients. The client gets them from the remediations API.

## Who is calling (authentication later)

Client endpoints never take a client id in the URL or the body. They get the caller from
`current_client` in `auth.py`, and only return that client's own data.

Today there is no real authentication. The client says who it is with headers, and the
API believes it:

```
X-Client-Id: linux-vm-1        required: stable id, e.g. osquery's system_info.uuid
X-Client-OS: linux             required: linux or windows
X-Client-Hostname: ubuntu-1    optional
```

When authentication is ready, only `current_client` changes. It reads a token, checks it,
returns 401 for bad ones, and returns the `Client` the auth system says the token belongs
to. The endpoints stay the same. The test
`test_real_auth_can_be_plugged_in_without_touching_the_endpoints` shows this working. For
the client, the only change is sending `Authorization: Bearer <token>` instead of the
`X-Client-*` headers.

## For the client (Kade, Mateo)

Send the `X-Client-*` headers on every request. Then repeat forever:

1. `GET /poll`
2. Run every query in `queries` with osquery, for example `osqueryi --json "<sql>"`.
3. `POST /results` with the rows (format below).
4. Sleep `poll_interval` seconds.

Getting and running fix scripts is a separate loop against the remediations API. Until
that exists, use our **mock** of it (same headers):

- `GET /mock/remediations/commands`: scripts to run. Always one harmless example.
- `POST /mock/remediations/commands/{id}/result` with `{"exit_code": 0, "output": "..."}`.

The scripts are multi-line, so save each one to a file and run the file:

- Linux: `bash /tmp/boombox-<id>.sh`
- Windows: `powershell -ExecutionPolicy Bypass -File C:\Windows\Temp\boombox-<id>.ps1`

The example scripts are `examples/example-command.sh` and `examples/example-command.ps1`.
They print some info and write one file to the temp folder.

`GET /whoami` shows who the API thinks you are. Use it to check your headers, and later
your token.

```bash
curl localhost:8000/poll -H "X-Client-Id: linux-vm-1" -H "X-Client-OS: linux"
```

**Poll response**

```json
{
  "poll_interval": 300,
  "queries": [
    {"name": "processes", "sql": "SELECT pid, parent, name, path, cmdline, uid, on_disk FROM processes"},
    {"name": "cron_jobs", "sql": "SELECT command, path FROM crontab"}
  ]
}
```

**Results body** (`POST /results`)

```json
{
  "results": [
    {"name": "processes", "rows": [{"pid": "4242", "name": "bash", "cmdline": "bash -i >& /dev/tcp/…"}]},
    {"name": "cron_jobs", "rows": []},
    {"name": "admin_users", "error": "osquery said: no such table"}
  ]
}
```

- `name` is the query's name from the poll.
- `rows` is exactly what `osqueryi --json` printed; don't convert anything.
- If a query failed, send `error` instead of `rows`.

The response comes back right away with what the server decided. If anything looked bad,
the fix script is written in the background (OpenAI can take a minute or two) and sent to
the remediations API under `remediation_id`:

```json
{
  "decision": {"verdict": "malicious", "findings": [{"query": "processes", "row": {}, "verdict": "malicious", "confidence": 0.9}]},
  "remediation_id": "9ae8e385-f776-4da9-b2d4-caec5cc13b1d"
}
```

## For the remediations API team

When `REMEDIATION_API_URL` is set, every remediation is sent as
`POST {REMEDIATION_API_URL}/remediations` with this JSON body:

```json
{
  "id": "659b53f3-0a14-4ea6-a8da-04dfff8d9946",
  "client_id": "linux-vm-1",
  "hostname": "ubuntu-client",
  "os": "linux",
  "shell": "bash",
  "script": "#!/usr/bin/env bash\nset -u\n\n# malicious (0.90) in processes: …\nkill -9 4242 …\n",
  "explanation": "What was found, what the script does, what to double-check.",
  "findings": [{"query": "processes", "row": {"pid": "4242", "…": "…"}, "verdict": "malicious", "confidence": 0.9}]
}
```

- `client_id` is the same id the client uses with our API (later: the authenticated client).
- `script` is a multi-line bash or PowerShell script. Nothing has run yet.
- If you need a different URL, shape or credentials, change `send_to_remediation_api` in
  `handoff.py`. It's the only place that talks to your API.

## For the dashboard (Xander, Aiden)

| Endpoint | What it does |
|---|---|
| `POST /clients/{client_id}/queries` | Asks one client to run a custom query once: `{"name": "...", "sql": "..."}` |

Not protected yet; the dashboard team decides how.

## Changing things

- **Collect something new:** add a `Query` to `queries.py` and restart.
- **Different queries per client:** `queries_for(client)` in `queries.py` decides what each
  client runs. Once auth knows more about a client (its group, what it may see), add those
  fields to `Client` in `schemas.py` and filter there.
- **Different models:** `decision.py` and `remediation.py` each have one function the API
  calls (`decide` and `make_script`). Swap what's inside; keep the inputs and outputs.
- **Slow models:** the fix script is written after `/results` answers (`BackgroundTasks` in
  `main.py`), so a slow model never makes the client wait.
- **One-time queries** live in memory (`extra_queries` in `main.py`) and reset on restart.
  Move them to the database when there is one.
