# Ingest

Where clients talk to the server.

- `routes.py`: `GET /poll` hands out the queries to run; `POST /results` takes the rows
  back and runs the pipeline (triage → analysis → remediation handoff).
- `queries.py`: the osquery queries for Linux and Windows, plus one-time custom queries
  queued by the admin endpoint (`api/routes.py`).
