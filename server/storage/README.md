# Storage

PostgreSQL schema and sample data for the Boombox project.

## Setup

Create a local PostgreSQL database named:

```text
boombox
```

Then run:

```bash
psql -d boombox -f server/storage/schema.sql
```

This creates the following tables:

```text
endpoints
events
remediations
```

To load sample test data, run:

```bash
psql -d boombox -f server/storage/sample_data.sql
```

You can verify the data with:

```sql
SELECT * FROM endpoints;
SELECT * FROM events;
SELECT * FROM remediations;
```

The sample data includes a Windows endpoint, a suspicious PowerShell process event, and a pending remediation recommendation.

## Database relationships

```text
endpoints.id
    ↓
events.endpoint_id

events.id
    ↓
remediations.event_id
```

`events.raw_data` uses PostgreSQL `JSONB` so different types of endpoint telemetry can be stored without requiring the same fields for every event.


# Storage

Database schema/migrations and the "outgest" script that writes triaged events and reports.
