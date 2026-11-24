# Boombox

An AI-assisted EDR (endpoint detection and response) proof of concept.

Clients on Windows and Linux machines run osquery queries and send the results to the
server. A decision model (TypeSafe Jev) flags anything suspicious, a remediation model
(OpenAI) writes a script to fix it, and a person approves the script on the dashboard
before the client runs it.

- [docs/WRITEUP.md](docs/WRITEUP.md): the project write-up: steps we took, design
  decisions, problems and how we solved them, setup, and references.
- [docs/README.md](docs/README.md): how the pieces fit together, and who did what.

## Team

| Person | Part |
|---|---|
| Andrew Sabolsky | Client API, AI pipeline (Jev + OpenAI), Docker setup, tests, live demo |
| Kade Onines | Linux client (Go) |
| Mateo Vallejo | Windows client (Go, earlier Python) |
| Aiden McEwan | Database (PostgreSQL) |
| Xander Whitby | Dashboard API (Go) and website (Vue) |
| Ethan | Infrastructure (Proxmox VMs, networking, Docker restarts) |

## Repository layout

```
.
├── client/              # Runs on monitored machines (Linux: Kade, Windows: Mateo)
├── server/
│   ├── client-api/      # Python: what clients talk to, plus the AI (Andrew)
│   ├── dashboard-api/   # Go: what the dashboard talks to (Xander)
│   └── database/        # PostgreSQL tables (Aiden)
├── dashboard/           # Vue website where people approve fixes (Xander)
├── demo/                # Live demo: a reverse shell that Boombox catches and closes
└── docs/                # How it all fits together, and the task list
```

## Getting started

1. Copy `.env.example` to `.env`. Add the AI keys if you have them (never commit `.env`).
2. From the repo root: `docker compose up --build`
3. Open:
   - http://localhost: the dashboard website
   - http://localhost:8080/docs: the client API, where you can try every endpoint in the browser
   - http://localhost:8000/health: the dashboard API

The database starts empty. To empty it again: `docker compose down -v`.

More detail is in [server/README.md](server/README.md).
