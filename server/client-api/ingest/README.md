# Ingest

Where clients talk to the server.

- `routes.py`: `POST /api/v1/clients` registers a client; `GET /api/v1/poll` hands out
  queries and approved scripts; `POST /api/v1/results` takes the rows back and runs the
  pipeline (triage → analysis → remediation).
- `queries.py`: the default osquery queries for Linux and Windows, plus each client's own
  queries from the database (the `client_queries` table, managed by the dashboard).
