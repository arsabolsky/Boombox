# Boombox

An LLM-assisted EDR: osquery on Windows and Linux endpoints ships telemetry to a central
server, a lightweight model triages it, a larger model analyzes anything suspicious and
proposes a remediation, and a human approves it before the fix script runs on the endpoint.

## Repository layout

```
.
├── endpoint/                 # Everything that runs on monitored hosts
│   ├── linux/                # endpoint, installer, remediation runner
│   └── windows/              # endpoint, installer, remediation runner
├── server/                   # Admin server / cluster / cloud
│   ├── ingest/               # POST endpoint + queue for osquery TLS logs
│   ├── triage/               # Lightweight LLM "is this sus?" filter
│   ├── storage/              # Database schema + "outgest" export script
│   ├── analysis/             # Big-AI analysis & remediation proposal
│   ├── remediation/          # Packages approved scripts and forwards them to endpoints
│   ├── notify/               # Discord / Teams / webhook push notifications
│   └── api/                  # REST API backing the dashboard
├── dashboard/                # Web UI: analytics, accept/deny/modify suggestions
├── docs/                     # Architecture notes and diagrams
└── .github/                  # GitHub CI crap...idk tbd
```


## Getting started

1. Copy `.env.example` to `.env` and fill in secrets (never commit `.env`).
2. Stand up the server components (see `server/README.md`).
3. Install an endpoint agent:
   - Linux: `sudo endpoint/linux/install.sh`
   - Windows (admin PowerShell): `endpoint\windows\install.ps1`
