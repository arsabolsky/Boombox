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

**Register first.** The database starts empty, so the client steps need a client of your own:

```bash
./01-register.sh linux                 # or windows
export CLIENT_ID=<the client_id it printed>
```

**A full run:**

1. `./02-poll-queries.sh`: the queries the client should run.
2. `./04-results-bad.sh`, wait about a minute, then `./05-list-remediations.sh`: a new
   `pending_review` fix script.
3. `./06-approve.sh <its id>`, then `./08-poll-remediations.sh`: the client gets it. Run
   `./08-poll-remediations.sh` again: `[]`, because each script is sent once.
4. `./09-add-query.sh`, then `./02-poll-queries.sh`: the new `tmp_files` query is in the list.

`03-results-clean.sh` and `04-results-bad.sh` need the AI keys in `.env`. Without them they answer HTTP 503,
and each run with keys costs a few cents. To empty the database again:
`docker compose down -v && docker compose up -d`.
