# Boombox

An AI-assisted EDR (endpoint detection and response) proof of concept.

Clients on Windows and Linux machines run osquery queries and send the results to the
server. A decision model (TypeSafe Jev) flags anything suspicious, a remediation model
(OpenAI) writes a script to fix it, and a person approves the script before it runs on the
machine.

See [docs/README.md](docs/README.md) for how the pieces fit together and who is working on what.

## Repository layout

```
.
├── client/          # Runs on monitored machines (Linux: Kade, Windows: Mateo)
├── server/          # Backend API (Andrew)
│   ├── ingest/      # Client endpoints: hand out queries, receive results
│   ├── triage/      # Decision model (Jev): is anything bad?
│   ├── analysis/    # Remediation model (OpenAI): write the fix script
│   ├── remediation/ # Hand the script to the remediations service
│   ├── api/         # Admin endpoints for the dashboard
│   └── examples/    # Sample data and a demo script
├── dashboard/       # Web UI where people approve fixes (Xander, Aiden)
└── docs/            # How it all fits together, and the task list
```

## Getting started

1. Copy `.env.example` to `.env` and fill in the API keys (never commit `.env`).
2. Start the server from the repo root: `docker compose up --build`
3. Open http://localhost:8000/docs to try every endpoint in the browser.

The server's details are in [server/README.md](server/README.md).
