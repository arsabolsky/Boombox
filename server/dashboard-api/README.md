# Dashboard backend (Go)

REST API that backs the Vue dashboard in `dashboard/frontend/boombox`. Talks to the
PostgreSQL database defined in `server/database/schema.sql` using
[pgx](https://github.com/jackc/pgx) with a connection pool.

It runs in Docker with the rest of the backend (`docker compose up --build` from the repo
root) on port 8000. The website reaches it through nginx at `/api`.

## Layout

```
cmd/server/      entrypoint: config, DB pool, HTTP server, graceful shutdown
internal/db/     connection pool + all SQL queries
internal/api/    HTTP handlers and routing
```

## Configuration

Reads the repo-root `.env` (or `./.env`); real environment variables win.

| Variable             | Default | Notes                                        |
|----------------------|---------|----------------------------------------------|
| `DATABASE_URL`       | —       | Required, e.g. `postgresql://boombox:changeme@localhost:5432/boombox` |
| `DASHBOARD_API_ADDR` | `:8000` | Matches the Vite dev proxy in the frontend   |

## Run

```bash
# 1. Database (see server/database/README.md)
psql -d boombox -f server/database/schema.sql

# 2. API
cd server/dashboard-api
go run ./cmd/server

# 3. Frontend (proxies /api and /health to :8000)
cd ../../dashboard/frontend/boombox && npm run dev
```

## Endpoints

| Method | Path                                   | Body                                  |
|--------|----------------------------------------|---------------------------------------|
| GET    | `/health`                              | — (503 if the DB is unreachable)      |
| GET    | `/api/v1/remediations`                 | —                                     |
| GET    | `/api/v1/remediations/{id}`            | —                                     |
| POST   | `/api/v1/remediations`                 | `{event_id, title, severity, summary?, proposed_script?}` |
| POST   | `/api/v1/remediations/{id}/approve`    | `{reviewed_by}`                       |
| POST   | `/api/v1/remediations/{id}/deny`       | `{reviewed_by}`                       |
| PUT    | `/api/v1/remediations/{id}/script`     | `{proposed_script}` (only while pending review; otherwise 409) |
| GET    | `/api/v1/endpoints`                    | — (every client, with event and pending-fix counts) |
| GET    | `/api/v1/clients/{client_id}/queries`  | — (that client's extra queries)       |
| POST   | `/api/v1/client-queries`               | `{client_id, query_name, query_configuration, enabled}` (send `"enabled": true`; it defaults to false) |
| PUT    | `/api/v1/client-queries/{id}`          | `{query_configuration, enabled}`      |

Errors use the shape `{"detail": "..."}` (404 for a missing remediation or
event, 422 for bad input).
