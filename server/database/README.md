# Database

PostgreSQL schema for the Boombox project (Aiden). Both the client API and the dashboard API
read and write it.

## Setup

`docker compose up` from the repo root creates the database and runs `schema.sql`
automatically the first time. The tables start empty: clients register themselves, and
events and fix scripts are added as the system runs. To empty everything again:
`docker compose down -v`.

To set it up by hand instead, create a PostgreSQL database named `boombox`, then run:

```bash
psql -d boombox -f server/database/schema.sql
```

## Tables

| Table | What's in it | Added by |
|---|---|---|
| `clients` | One row per registered machine: hostname, OS, last seen | client API, when a client registers |
| `events` | Query results that looked bad, as `JSONB` | client API, after Jev flags something |
| `remediations` | Fix scripts and their status: `pending_review`, `approved`, `denied`, `executed` | client API writes them; the dashboard approves or denies |
| `client_queries` | Extra osquery queries for one client | dashboard API |

You can look at the data with:

```sql
SELECT * FROM clients;
SELECT * FROM events;
SELECT * FROM remediations;
SELECT * FROM client_queries;
```

Or run `tests/10-watch.sh`, which keeps showing the events and fix scripts.

## Relationships

```text
clients.client_id
    ↓
events.client_id, remediations.client_id, client_queries.client_id

events.id
    ↓
remediations.event_id
```

`events.raw_data` uses PostgreSQL `JSONB` so different types of endpoint telemetry can be
stored without requiring the same fields for every event.
