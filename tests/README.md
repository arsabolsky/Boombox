# Test requests

One `curl` file per step of the process. Start everything first with
`docker compose up --build` from the repo root, then run the files from this folder in order.
If `00-health.sh` shows `HTTP 000` right after starting, the client API is still starting:
wait a few seconds and try again.

| File | Step | API |
|---|---|---|
| `00-health.sh` | Both APIs are up | both |
| `01-register.sh [linux\|windows]` | Register a new client | client (8080) |
| `02-poll-queries.sh` | Get the osquery queries to run | client (8080) |
| `03-results-clean.sh` | Send normal results: expect `benign` | client (8080) |
| `04-results-bad.sh` | Send bad results: expect `malicious`, and a fix script about a minute later | client (8080) |
| `05-list-remediations.sh` | List fix scripts and their status | dashboard (8000) |
| `06-approve.sh <id>` | Approve a fix script | dashboard (8000) |
| `07-deny.sh <id>` | Deny a fix script | dashboard (8000) |
| `08-poll-remediations.sh` | Get approved fix scripts to run | client (8080) |
| `09-add-query.sh` | Give one client an extra query | dashboard (8000) |
| `10-watch.sh [seconds]` | Keep showing the saved query results and fix scripts, refreshing every 5 seconds | database |

**Tip:** run `./10-watch.sh` in a second terminal while you run the other steps, to watch
results and fix scripts appear and change status. Only results that looked bad are saved.

By default the client steps use the sample Linux client
(`33333333-3333-4333-8333-333333333333`). To use another one:

```bash
export CLIENT_ID=22222222-2222-4222-8222-222222222222   # sample Windows client
```

**A full run:**

1. `./02-poll-queries.sh`: the queries the client should run.
2. `./08-poll-remediations.sh`: the sample client gets its approved test script. Run it
   again: `[]`, because each script is sent once.
3. `./04-results-bad.sh`, wait a minute, then `./05-list-remediations.sh`: a new
   `pending_review` fix script.
4. `./06-approve.sh <its id>`, then `./08-poll-remediations.sh`: the client gets it.
5. `./09-add-query.sh`, then `./02-poll-queries.sh`: the new `tmp_files` query is in the list.

Steps 3 and 4 need the AI keys in `.env`. Without them they answer HTTP 503, and each run
with keys costs a few cents. To start over with fresh sample data:
`docker compose down -v && docker compose up -d`.
