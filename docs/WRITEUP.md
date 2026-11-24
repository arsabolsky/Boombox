# Boombox: Project Write-up

CYBER 344 (Operating Systems), Fall 2026

Boombox is a proof-of-concept **AI-assisted EDR** (endpoint detection and response) tool.
Small clients on Linux and Windows machines collect information with osquery and send it to
a server. An AI classifier decides whether anything looks malicious, a second AI model
writes a script to fix it, a person reviews and approves the script on a web dashboard, and
the client then runs it.

This document tells the story of the project: what we built, how and why, what went wrong
and how we fixed it, and how to set it up yourself.

**Contents**
1. [What we built](#1-what-we-built)
2. [Team](#2-team)
3. [Steps we took](#3-steps-we-took)
4. [Design decisions](#4-design-decisions)
5. [Problems we hit and how we solved them](#5-problems-we-hit-and-how-we-solved-them)
6. [Setup and usage](#6-setup-and-usage)
7. [Known limitations](#7-known-limitations)
8. [External tools and resources](#8-external-tools-and-resources)

---

## 1. What we built

```
 Linux / Windows machine                    Server (Docker Compose)
 ┌────────────────────┐   poll + results   ┌──────────────────────────────┐
 │ Boombox client     │ ─────────────────▶ │ Client API (Python, :8080)   │
 │  runs osquery      │                    │  ├─ filter our own traffic   │
 │  runs approved     │ ◀───────────────── │  ├─ Jev: is this row bad?    │
 │  fix scripts       │  approved scripts  │  ├─ OpenAI: write a fix      │
 └────────────────────┘                    │  └─ check the fix            │
                                           │             │                │
                                           │       PostgreSQL (:5432)     │
                                           │             │                │
                                           │ Dashboard API (Go, :8000)    │
                                           │ Dashboard website (Vue, :80) │
                                           └──────────────────────────────┘
                                                         ▲
                                                 a person reviews,
                                               edits, approves or denies
```

The pieces, and where they live in the repository:

| Part | What it does | Folder |
|---|---|---|
| Linux client | Go program; runs as a systemd service | `client/linux` |
| Windows client | Go program (earlier Python version kept); runs as a Windows service | `client/windows-client` |
| Client API | Python (FastAPI). Registers clients, hands out queries and approved scripts, receives results, runs the AI pipeline | `server/client-api` |
| Database | PostgreSQL tables shared by both APIs | `server/database` |
| Dashboard API | Go. Lists fix scripts and clients, approve/deny/edit, per-client queries | `server/dashboard-api` |
| Dashboard website | Vue. Review queue, backlog, analytics, clients | `dashboard/frontend/boombox` |
| Tests | One `curl` script per step of the flow, plus a database watcher and a cost report | `tests/` |
| Live demo | A victim machine with a reverse shell and an attacker machine, in Docker | `demo/` |

**The flow, step by step**

1. A client registers once (`POST /api/v1/clients` with its hostname, OS and OS version) and
   receives a `client_id`. It sends that id as the `X-Client-Id` header on every request.
2. The client polls `GET /api/v1/poll/queries` and gets osquery SQL to run: a default list
   for its OS plus any queries the dashboard assigned to that client.
3. It runs them with osquery and posts the rows to `POST /api/v1/results`.
4. The server drops rows that are our own normal traffic, then asks **TypeSafe Jev** about
   every remaining row: benign, suspicious, or malicious.
5. If anything is flagged, the findings are grouped into one attack and **OpenAI** writes a
   single bash (Linux) or PowerShell (Windows) script to fix it. The script is checked
   automatically and saved as `pending_review`.
6. A person opens the dashboard, reads the explanation and the script, can edit it, and
   approves or denies it.
7. The client polls `GET /api/v1/poll/remediations`, receives each approved script once,
   and runs it.

---

## 2. Team

| Person | Role | Main work |
|---|---|---|
| Andrew Sabolsky | Client API, AI pipeline, project lead | Repository structure and docs, client API, Jev and OpenAI pipeline, grouping and filtering, self-checks, cost tracking, Docker Compose and nginx setup, tests, live demo |
| Kade Onines | Linux client | Go client with registration, query and remediation loops, systemd service, logging; first task list |
| Mateo Vallejo | Windows client | Python client, then a faster Go client with retries and backoff; NSSM service and install scripts |
| Aiden McEwan | Database | PostgreSQL schema and database functions; first remediations API |
| Xander Whitby | Dashboard | Go dashboard API; Vue website with review queue, backlog, analytics, clients page, script editing |
| Ethan | Infrastructure | Proxmox VMs for the server and both clients, team network access, Docker restart policies, VM CPU fix |

A more detailed breakdown is in [docs/README.md](README.md#who-did-what).

---

## 3. Steps we took

**1. Plan and split the work (early October).** We sketched the data flow (client →
decision model → remediation model → database → dashboard → back to the client), set up the
repository with a folder for each part, and split it up: Linux client, Windows client, AI
models and API, database, dashboard, and infrastructure.

**2. Learn osquery and build the first client loop (October).** Kade built the first osquery
execution loop in Go, which became the Linux client.

**3. Build the parts in parallel (November 10–19).**
- Aiden designed the PostgreSQL schema and a first remediations API.
- Xander built the dashboard: first a Go API with the same routes, then the Vue website.
- Andrew built the client API and the AI pipeline. A larger first version (RabbitMQ queue,
  heuristic fallbacks) was cut down to a simple proof of concept: one FastAPI app, Jev for
  decisions, OpenAI for fixes, no fallbacks.
- Kade and Mateo built the client loops against the API as it was then.

**4. Merge everything into one system (November 19–20).** The parts had been built
separately, so they didn't fit together yet: two APIs on the same port, two ways of
identifying clients, a mock where the real remediation service should be. We picked one
folder layout (`server/client-api`, `server/dashboard-api`, `server/database`), moved
Aiden's database code into the client API, ran Xander's Go API side by side, and put
everything in one `compose.yaml`. Clients now register and use a database-issued UUID.

**5. Deploy to the team's servers (November 20–23).** Ethan set up the Proxmox VMs. We moved
the dashboard website to port 80 behind nginx, fixed a VM CPU setting that stopped the
website from building, and made every service restart automatically. Kade's and Mateo's
clients went live against the real server.

**6. Test with a live attack and improve the AI (November 21–23).** We built a demo: a victim
container with a real (harmless) reverse shell, and an attacker container. Running it again
and again exposed problems: repeat fixes, scripts that half-worked, false alarms, Windows
scripts that would have closed the user's desktop. We fixed them one at a time (see
section 5). By the end, the first fix closed the reverse shell in 3 out of 3 test runs.

**7. Clean up and document (November 23).** We removed the experiment folders, moved the
demo into `demo/`, and wrote this document.

---

## 4. Design decisions

| Decision | Why |
|---|---|
| **osquery for data collection** | It works on Linux and Windows with the same SQL-like queries (processes, network connections, cron jobs, scheduled tasks, startup programs), so both clients can share one server-side list of queries. |
| **Clients poll the server** (instead of the server pushing to them) | Polling works through NAT and firewalls, needs no open ports on the clients, and is simple to build. The cost is a delay of up to one polling interval. |
| **Queries are chosen by the server** | New queries can be added in one place (`server/client-api/ingest/queries.py`, or per client from the dashboard) without updating any client. |
| **Two AI models: a cheap classifier, then an LLM** | Jev checks every row of every poll, so it has to be fast and cheap (about 0.3 s and a fraction of a cent per call). OpenAI only runs when something is flagged, about once per attack. |
| **Jev for decisions** | Jev returns a calibrated label and confidence instead of free text, which is what a yes/no decision needs. Asking it one question per row tells us exactly which rows are bad. |
| **Context added to each row** | A row on its own (`bash -i`) says little. Adding the parent process and network connections (`started by a while true … /dev/tcp loop, connected to port 4444`) lets Jev judge it properly. |
| **A person approves every fix** | AI-written scripts run as root or SYSTEM. A mistake could take down a machine, so nothing runs without review. The reviewer can also edit the script. |
| **One fix per attack** | One attack shows up as several rows (a loop, its shell, the shell's connection, child processes) on every poll. Without grouping, each poll created a new fix. Findings are grouped by **process family**: follow each flagged process's flagged parents to the top of the attack. |
| **The attack list never includes parents that weren't flagged** | The program that launched an attack (for example `explorer.exe` or `sshd`) must never be killed. Only the flagged processes and their children are targeted. |
| **Fix scripts are sent once** | A script is marked executed as it's handed to the client. This avoids running the same fix repeatedly and needs no extra "report result" endpoint. If the attack is still there on the next poll, a new fix is written. |
| **Filter our own traffic in code, not in the prompt** | The Boombox client, osquery, closed connections and Tailscale are removed before Jev sees anything. Code is predictable; a prompt hint wasn't. |
| **Different tips for Linux and Windows** | bash and PowerShell have different pitfalls. Each request only gets the tips for its own OS, which keeps the prompt short. |
| **Automatic checks before review** | `bash -n`, ShellCheck, and our own checks catch common script mistakes. If any fail, the errors go back to OpenAI for one corrected try; anything left is shown to the reviewer as a warning. |
| **Low reasoning effort for OpenAI** | We tested high, medium and low. High took 100 seconds and 11¢ per fix and wrote over-complicated scripts; low took about 12 seconds and 1.5¢ and worked just as well. |
| **The client id is the only authentication** | This is a proof of concept. Real authentication can be added in one place (`server/client-api/auth.py`) later. |
| **Two APIs, one database** | The client API (Python) and the dashboard API (Go) never call each other; they share PostgreSQL. Each team member could work on their part independently. |
| **Everything in Docker Compose** | One command starts the database, both APIs and the website, the same way on a laptop and on the server. |
| **The dashboard website is built and served by nginx** | The first setup ran Vite's development server, which broke whenever the Go container restarted. A built site behind nginx is simpler and keeps working. |
| **uv for Python packages** | `uv.lock` pins exact package versions, so everyone and the server get the same build. |

---

## 5. Problems we hit and how we solved them

**Parts built separately didn't fit together.**
The client API, the database API and the dashboard API were built in parallel against
different assumptions. Two APIs used port 8000, clients identified themselves in two ways,
and two copies of the remediations API existed. *Fix:* one folder layout, Aiden's database
code moved into the client API, Xander's Go API kept for the dashboard, the client API moved
to port 8080, and clients register once to get a database UUID.

**The dashboard website stopped working when the Go API restarted.**
The website container shared the Go container's network so its development proxy could reach
`localhost:8000`. When the Go container restarted, the website was left on a network that no
longer existed, and port 80 went dead. *Fix:* build the website and serve it from its own
nginx container, which forwards `/api` to the Go API by name.

**The website wouldn't build on the server ("Illegal instruction").**
Vite 8 builds with a native program that needs modern CPU instructions (AVX2). The Proxmox VM
used the default virtual CPU (`QEMU Virtual CPU version 2.5+`), which hides them. *Fix:* in
Proxmox, set the VM's processor type to `host` and fully restart the VM.

**A new fix script on every poll.**
Clients send the same results every poll, so the same reverse shell got a new fix every few
seconds. A first fix (skip rows that already have an open fix) wasn't enough: PIDs change,
and Jev flags different parts of the same attack on different polls. *Fix:* group findings by
process family, skip any family that already has an open fix, and also remember fixes that are
still being written (OpenAI takes 10–20 seconds).

**AI fix scripts that only half worked.** Running the demo repeatedly showed several mistakes:
- Killing a parent process, then checking "is the child's parent still X?". Linux moves
  orphaned children under PID 1, so the check failed and the child was never killed.
- Assigning to `PPID` or `UID`, which are read-only in bash, so the script stopped on the spot.
- Sending only SIGTERM. An interactive `bash -i` ignores SIGTERM, so the reverse shell survived.
- A final "is it gone?" check using `grep` or `awk` on `ps` output, which found its own search
  command.
- The fix was written from a snapshot taken before the shell connected. By the time a person
  approved it, new processes existed that weren't in the list.

*Fix:* give OpenAI the exact list of attack processes, tell it to kill every **current** child
at run time (`pkill -9 -P`), to escalate to `kill -9`, and to use `pgrep -f` (which never
matches itself). The automatic checks now catch read-only variable assignments. After these
changes, the first fix closed the shell in 3 of 3 runs.

**False alarms.** Jev flagged the Boombox client's own connection to the server, closed
sockets with no process (`pid -1`), Tailscale, and even the Boombox client and osquery
themselves, including the osquery service on Windows. *Fix:* `triage/scope.py` removes these
before Jev sees them, matching by process name and by the program's file name in the path or
command line. Some normal programs (VS Code, Copilot, a Windows Update task) are still flagged
as "suspicious" around 50% confidence; a person denies those on the dashboard.

**Windows fixes that would have closed the desktop.** In a test with fake Windows data, the
first fix killed `explorer.exe`, because the process-family code had walked up from the
malware to the program that launched it. The script also used `$Pid` (read-only in
PowerShell), doubled backslashes inside single quotes, and `"$name:"` (a PowerShell syntax
error). *Fix:* the family walk stops at parents that weren't flagged; the prompt gets Windows
tips; the automatic checks look for these PowerShell mistakes.

**More AI thinking made things worse.** "High" reasoning wrote 100-line scripts that read
`/proc` by hand and still failed. *Fix:* reasoning set to low, plus a "keep it short and simple,
use `pgrep`/`pkill`" rule.

**The API changed while the clients were being built.** As the server was reorganized,
endpoints moved (for example `/poll` became `/api/v1/poll/queries`, and clients started
registering). *Fix:* the request formats are documented in `server/client-api/README.md`, with
a `curl` script for every step in `tests/`.

**Smaller issues:** a container left over from an older compose file held port 8000 (fixed
with `docker compose up --remove-orphans`); iCloud created duplicate files like
`schema 2.sql` in the repository folder (deleted after checking they were identical); and API
keys belong only in the git-ignored `.env`, never in `.env.example`.

---

## 6. Setup and usage

### Requirements

- **Server:** a Linux machine (or a Mac for local testing) with Docker and Docker Compose. If
  it's a virtual machine, its CPU must support AVX2 (in Proxmox, set the processor type to `host`).
- **API keys:** a TypeSafe API key for Jev and an OpenAI API key.
- **Clients:** Linux or Windows machines with [osquery](https://osquery.io/) installed, and Go
  to build the clients.
- Network access from the clients to the server's port 8080 (we used Tailscale).

### Start the server

```bash
git clone https://github.com/arsabolsky/Boombox.git
cd Boombox
cp .env.example .env      # then edit .env: set TYPESAFE_API_KEY and OPENAI_API_KEY
docker compose up -d --build
```

This starts four containers:

| Service | URL | What it is |
|---|---|---|
| `dashboard` | http://localhost | The dashboard website |
| `client-api` | http://localhost:8080/docs | The client API, with interactive docs (Swagger) |
| `dashboard-api` | http://localhost:8000/health | The dashboard API |
| `database` | `localhost:5432` | PostgreSQL. The tables are created automatically the first time |

The database starts empty. To empty it again: `docker compose down -v`, then
`docker compose up -d`. Settings (all in `.env`):

| Setting | Default | Meaning |
|---|---|---|
| `TYPESAFE_API_KEY`, `OPENAI_API_KEY` | (none) | Required for checking results; without them `POST /api/v1/results` answers 503 |
| `JEV_MODEL` | `jev-latest` | Jev model version |
| `OPENAI_MODEL` | `gpt-5` | OpenAI model |
| `OPENAI_REASONING_EFFORT` | `low` | How hard OpenAI thinks: `minimal`, `low`, `medium`, `high` |
| `BOOMBOX_SERVER_ADDRESSES` | (none) | Other addresses clients use to reach the server, so their connections aren't flagged |
| `JEV_PRICE_*`, `OPENAI_PRICE_*` | estimates | Prices per million tokens, used for cost tracking |

### Install the Linux client (Kade's)

```bash
cd client/linux
go build -o boombox-client .
cp .env.example .env      # set API_HOST to http://<server>:8080 and OS_VERSION
```

To run it as a service, use `boombox-client.service`. Two things to know: the unit file
expects the binary at `/user/sbin/boombox-client` (note "user", not "usr"; copy it there or
change the path), and the client reads `.env` from its working directory, which is `/` for
systemd services (put `.env` there, or add a `WorkingDirectory=` line to the unit). Then:

```bash
sudo cp boombox-client.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now boombox-client
```

### Install the Windows client (Mateo's)

Follow `client/windows-client/Windows-client-go/README.md`. In short, from an Administrator
PowerShell: run `install-dependencies.ps1` (Go and NSSM), build with
`go build -trimpath -ldflags="-s -w" -o BoomboxClient.exe .`, set `API_BASE_URL` in `.env` to
`http://<server>:8080/`, run `install-service.ps1`, then start the `BoomboxClient` service.

### Use it

1. Open the dashboard (http://<server>). Clients appear under **Clients** once they register.
2. When something suspicious happens on a client, a fix appears under **Review** within about
   a minute: severity, title, the AI's explanation, and the script.
3. Read it, edit it if needed (**Modify**), then **Approve & deploy** or **Deny**.
4. The client picks up approved fixes on its next poll and runs them.

To collect something new on every machine of an OS, add a query to
`server/client-api/ingest/queries.py` and run `docker compose up -d --build client-api`. To give
one client an extra query, use the dashboard API (`POST /api/v1/client-queries`, see
`tests/09-add-query.sh`).

### Test it without real clients

The `tests/` folder has a `curl` script for each step. See `tests/README.md`. For example:

```bash
cd tests
./01-register.sh linux                     # prints a client_id
export CLIENT_ID=<that client_id>
./02-poll-queries.sh                       # queries to run
./04-results-bad.sh                        # a reverse shell, a miner and a bad cron job
./05-list-remediations.sh                  # about a minute later: a pending fix
./06-approve.sh <id>
./08-poll-remediations.sh                  # the client receives the fix
./11-costs.sh                              # time, tokens and estimated cost of AI calls
```

### Run the live demo

See `demo/README.md`. In short: `cd demo && ./start.sh`, then `./victim-screen.sh` in one
terminal and `./attacker-listen.sh` in another. Paste the line from `funny-messages.txt` into
the attacker's shell, approve the fix on the dashboard, and watch the messages stop and the
attacker's connection close.

### API reference

- **Client API (port 8080):** `POST /api/v1/clients`, `GET /api/v1/poll/queries`,
  `POST /api/v1/results`, `GET /api/v1/poll/remediations`. Full formats in
  `server/client-api/README.md`, and live at http://localhost:8080/docs.
- **Dashboard API (port 8000):** `GET /api/v1/endpoints`, `GET|POST /api/v1/remediations`,
  `GET /api/v1/remediations/{id}`, `POST /api/v1/remediations/{id}/approve|deny`,
  `PUT /api/v1/remediations/{id}/script`, and per-client queries under
  `/api/v1/client-queries`. See `server/dashboard-api/README.md`.
- **Database tables:** `clients`, `events`, `remediations`, `client_queries`. See
  `server/database/README.md`.

---

## 7. Known limitations

- **Authentication is just the client id.** Anyone who knows a client id can act as that client.
- **Fixes are sent once with no result report.** If a client crashes before running a fix, it
  isn't sent again (a still-present attack gets a new fix on the next poll).
- **Some normal programs are still flagged as "suspicious"** (around 50% confidence); a person
  has to deny them.
- **PowerShell fixes are only pattern-checked.** There is no PowerShell in the server container,
  so syntax errors are only caught if they match a known mistake.
- **Connections to other Tailscale machines are ignored**, which means an attacker on the tailnet
  wouldn't be flagged by connection alone (the processes still would be).
- **Dashboard API:** creating a per-client query without `"enabled": true` saves it as disabled.

---

## 8. External tools and resources

**Data collection and clients**
- osquery: https://osquery.io/ and https://osquery.readthedocs.io/ (table schema: https://osquery.io/schema/)
- Go: https://go.dev/
- godotenv (`.env` loading in Go): https://github.com/joho/godotenv
- systemd service units: https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html
- NSSM, the Non-Sucking Service Manager (Windows services): https://nssm.cc/

**AI models**
- TypeSafe Jev API (decision model): https://docs.typesafe.ai/api
- OpenAI API, Responses API with structured outputs (remediation model, GPT-5): https://platform.openai.com/docs/api-reference/responses
- OpenAI Python SDK: https://github.com/openai/openai-python

**Server**
- FastAPI (client API): https://fastapi.tiangolo.com/
- Pydantic (request and response models): https://docs.pydantic.dev/
- HTTPX (calls to Jev): https://www.python-httpx.org/
- psycopg 3 (PostgreSQL from Python): https://www.psycopg.org/psycopg3/
- python-dotenv: https://github.com/theskumar/python-dotenv
- uv (Python packages and lock file): https://docs.astral.sh/uv/
- PostgreSQL: https://www.postgresql.org/docs/
- pgx (PostgreSQL from Go): https://github.com/jackc/pgx
- ShellCheck (bash script checks): https://www.shellcheck.net/

**Dashboard**
- Vue 3: https://vuejs.org/
- Vite: https://vite.dev/
- nginx: https://nginx.org/en/docs/

**Infrastructure**
- Docker and Docker Compose: https://docs.docker.com/compose/
- Proxmox VE (virtual machines; processor type settings): https://pve.proxmox.com/wiki/Qemu/KVM_Virtual_Machines
- Tailscale (network access between machines): https://tailscale.com/kb

**Demo**
- netcat (OpenBSD), cowsay and figlet, from the Ubuntu package archive: https://packages.ubuntu.com/

**Development assistance**
- Claude Code (Anthropic), an AI coding assistant, helped write and test code and
  documentation: https://www.anthropic.com/claude-code
