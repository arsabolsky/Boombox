# Backend API review

Status as of Nov 12, 2026, on branch `andrew/models-pipeline` (not committed yet).

## What it is

A small FastAPI server in `server/` and one Docker container:

1. **Polling:** clients ask what to collect and get back osquery queries.
2. **Results:** clients send back the rows.
3. **Decision:** TypeSafe Jev labels each row benign, suspicious or malicious.
4. **Remediation:** if anything is bad, OpenAI writes a multi-line bash or PowerShell fix script.
5. **Handoff:** the script goes to the remediations API (another team), which handles approval and
   delivery to the client.

No API keys are needed to try it. Without them, decisions come from simple regex rules and fixes from a
template.

```
 client                          our API                             remediations API
   │ GET /poll ───────────────────▶│                                   (other team)
   │◀── queries ───────────────────│                                       │
   │ run queries with osquery      │                                       │
   │ POST /results ───────────────▶│ decision.py → remediation.py          │
   │◀── decision ──────────────────│ handoff.py ── POST /remediations ────▶│ approval,
   │                               │                                       │ delivery
   │◀──────────────────────── fix scripts (their API) ─────────────────────┘
```

## Files

| File | Job |
|---|---|
| `server/main.py` | All endpoints. Start here. |
| `server/auth.py` | Decides who the caller is. **The only place to change for real authentication.** |
| `server/schemas.py` | Every JSON shape in and out. |
| `server/queries.py` | The osquery queries for each OS. Edit to collect something new. |
| `server/decision.py` | Step 1, `decide()`: Jev, or regex rules without a key. |
| `server/remediation.py` | Step 2, `make_script()`: OpenAI, or a template without a key. |
| `server/handoff.py` | Step 3, `send_to_remediation_api()`. **The only place that talks to the remediations API.** |
| `server/mock_remediations.py` | Stand-in for the remediations API so client devs can build now. Delete when the real one exists. |
| `server/tests/test_api.py` | 13 tests, all passing. |
| `server/examples/` | Sample results, `demo.sh`, and harmless example scripts for client devs. |
| `compose.yaml` | One service: `api` on port 8000. |

## Endpoints

| Endpoint | Who calls it | What it does |
|---|---|---|
| `GET /poll` | Client | Returns `poll_interval` and the `queries` for this client's OS, plus any one-time queries. |
| `POST /results` | Client | Takes the rows, returns the decision right away; the fix script is written in the background and handed off. |
| `GET /mock/remediations/commands` | Client | **Mock** of the remediations API: one harmless example script. |
| `POST /mock/remediations/commands/{id}/result` | Client | **Mock**: accepts the script's exit code and output. |
| `GET /whoami` | Client (testing) | Shows who the API thinks the caller is. |
| `POST /clients/{client_id}/queries` | Dashboard / admin | Asks one client to run a custom query once. |
| `GET /docs` | Anyone | Swagger UI for all of the above. |

## Decisions we made

- **Remediation is fully separate.** Our API never sends scripts to clients. It writes the script and hands
  it off. Approval, delivery and tracking belong to the remediations API.
- **Authentication can be added in one place.** Client endpoints get the caller from `current_client()` in
  `auth.py` and only return that client's data. Today it trusts the `X-Client-*` headers. Later it will check
  a token instead, and no endpoint changes. A test proves this by plugging in fake token auth.
- **Identity is never in the URL or the request body.** A client can't claim to be another machine, so it
  stays safe once auth exists.
- **Remediations are multi-line scripts**, with a comment above each step. The client saves each one to a
  file and runs the file.
- **No database, queue or logging of remediations.** The only state is one-time queries, kept in memory.
- **Each model sits behind one function** (`decide`, `make_script`). Either can be swapped without touching
  the rest.

## Open items

- [ ] **Real models untested.** Jev and OpenAI haven't been called; there are no keys yet. Jev access is
      waitlist-only.
- [ ] **Queries untested on real machines.** Kade and Mateo should run each query in `queries.py` with
      `osqueryi`, especially the Windows ones.
- [ ] **Handoff format to agree.** The remediations team needs to agree to `POST /remediations` with the
      JSON shown in `server/README.md`, or say what they want instead (change only `handoff.py`).
- [ ] **Auth design pending.** Whoever builds auth rewrites `current_client()` in `auth.py`.
- [ ] **Old work is backed up, not lost.** The earlier, bigger version (Postgres queue, admin API) is in
      `git stash` (`git stash list`). Drop it once you're sure you don't need it.
- [ ] **The published architecture page is out of date.** It describes the old version; update or delete it.
- [ ] **Commit and push** this branch.

## Try it

```bash
docker compose up --build             # from the repo root
open http://localhost:8000/docs       # Swagger UI
server/examples/demo.sh               # whole flow in the terminal
docker compose run --rm api pytest    # tests
docker compose logs -f api            # see the scripts that would go to the remediations API
```

---

# For the client developers (Kade, Mateo)

Everything you need to build against our API. Swagger UI is at `http://<server>:8000/docs`.

## 1. Say who you are, on every request

```
X-Client-Id: <stable id>     required: use osquery's system_info.uuid
X-Client-OS: linux           required: linux or windows
X-Client-Hostname: <name>    optional
```

Check that the API sees you correctly:

```bash
curl http://<server>:8000/whoami -H "X-Client-Id: linux-vm-1" -H "X-Client-OS: linux"
# {"client_id": "linux-vm-1", "os": "linux", "hostname": "linux-vm-1"}
```

When real authentication arrives, these three headers are replaced by `Authorization: Bearer <token>`.
Nothing else in your code changes, so keep the headers in one place.

## 2. The loop

```
forever:
    GET  /poll                 -> poll_interval, queries
    for each query: run it with osquery (osqueryi --json "<sql>"), with a timeout
    POST /results              -> the rows from every query
    sleep poll_interval seconds
```

**`GET /poll` response**

```json
{
  "poll_interval": 300,
  "queries": [
    {"name": "processes", "sql": "SELECT pid, parent, name, path, cmdline, uid, on_disk FROM processes"},
    {"name": "cron_jobs", "sql": "SELECT command, path FROM crontab"}
  ]
}
```

**`POST /results` body**

```json
{
  "results": [
    {"name": "processes", "rows": [{"pid": "4242", "name": "bash", "cmdline": "bash -i"}]},
    {"name": "cron_jobs", "rows": []},
    {"name": "admin_users", "error": "osquery said: no such table"}
  ]
}
```

Rules:

- `name` is the query's `name` from the poll.
- `rows` is exactly what `osqueryi --json` printed. Don't convert strings to numbers or clean anything up.
- If a query fails, send `error` instead of `rows`, and keep going.
- Run SQL **only** through osquery, never through a shell. The query list comes from the server, so it can
  change without a client update.

The response comes back in under a second with what the server decided. If something looked bad, the fix
script is written in the background and goes to the remediations API, so you don't wait for it:

```json
{
  "decision": {"verdict": "malicious", "findings": [{"query": "processes", "row": {"pid": "4242"}, "verdict": "malicious", "confidence": 0.9}]},
  "remediation_id": "9ae8e385-f776-4da9-b2d4-caec5cc13b1d"
}
```

## 3. Running fix scripts (separate loop, remediations API)

Fix scripts will come from the **remediations API** (another team). Until it exists, our server has a
**mock** of it so you can build this part now. It always returns one harmless example script (it prints the
hostname, user and time, and writes one file to the temp folder).

```
forever (can share the main loop's timer):
    GET  /mock/remediations/commands                  -> scripts to run (same headers)
    for each: save `script` to a file, run it with `shell`, capture exit code + output
    POST /mock/remediations/commands/{id}/result      -> {"exit_code": 0, "output": "..."}
```

```json
[
  {"id": "example-bash", "shell": "bash", "script": "#!/usr/bin/env bash\nset -u\n\n# Step 1: say where we are running\n..."}
]
```

Scripts are multi-line, so save each one to a file and run the file:

```bash
bash /tmp/boombox-<id>.sh                                                      # Linux, as root
powershell -ExecutionPolicy Bypass -File C:\Windows\Temp\boombox-<id>.ps1      # Windows, as SYSTEM
```

The real remediations API will pick its own URLs and shapes, so keep its base URL and these two calls in
one place in your code. When it's ready, you change the URL and maybe the JSON field names.

## 4. Try it without a client

```bash
curl http://<server>:8000/poll -H "X-Client-Id: linux-vm-1" -H "X-Client-OS: linux"

curl -X POST http://<server>:8000/results \
  -H "X-Client-Id: linux-vm-1" -H "X-Client-OS: linux" -H "Content-Type: application/json" \
  -d @server/examples/results-linux.json
```

`results-linux.json` contains a reverse shell, a crypto miner and a malicious cron job, so it should come
back `"verdict": "malicious"`.

```bash
curl http://<server>:8000/mock/remediations/commands -H "X-Client-Id: linux-vm-1" -H "X-Client-OS: linux"
```

Or run everything at once: `server/examples/demo.sh`. Every endpoint can also be tried in the browser at
`http://<server>:8000/docs`.

## 5. Run the server yourself

```bash
git clone https://github.com/arsabolsky/Boombox.git && cd Boombox
git checkout andrew/models-pipeline
docker compose up --build          # API on http://localhost:8000
```

No API keys needed. Without them the server uses simple built-in rules instead of the AI models, which is
all you need to build the client.
