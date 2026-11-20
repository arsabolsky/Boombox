# Server

Three parts, each in its own folder and its own Docker container:

| Folder | What it is | Port |
|---|---|---|
| [`client-api/`](client-api/README.md) | Python (FastAPI). Clients register, poll for queries and fix scripts, and send results. Runs the AI. | 8080 |
| [`dashboard-api/`](dashboard-api/README.md) | Go. The dashboard website reads fix scripts and approves or denies them here. | 8000 |
| [`database/`](database/README.md) | PostgreSQL tables and sample data. Both APIs read and write it. | 5432 |

The two APIs never call each other; everything goes through the database.

## Run everything

From the repo root:

```bash
cp .env.example .env          # add the AI keys if you have them
docker compose up --build
```

- Client API: http://localhost:8080/docs (try every endpoint in the browser)
- Dashboard website: http://localhost:5173
- Dashboard API: http://localhost:8000/health

The database is created with sample data the first time. To start over:
`docker compose down -v`, then `docker compose up`.

Without the AI keys everything works except `POST /api/v1/results`, which answers 503.
