# Server (Admin Server / Cluster / Cloud)

Pipeline, in order:

| Dir | Diagram step |
|-----|--------------|
| `ingest/` | Receives osquery TLS POSTs (`/api/v1/enroll`, `/api/v1/log`) and pushes them onto the queue |
| `triage/` | Lightweight LLM pulls from the queue and decides "sus or not" |
| `storage/` | Database schema and the "outgest" script that logs suspicious events |
| `analysis/` | Big LLM analyzes the stored report and proposes a remediation script |
| `api/` | REST API the dashboard reads from and writes approvals to |
| `notify/` | Discord / webhook push notifications when a new suggestion is ready |
| `remediation/` | Delivers approved scripts to the endpoint runner and records results |

Configuration comes from the repo-root `.env` (see `.env.example`).
