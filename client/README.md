# Client

Runs on every monitored machine (Linux: Kade, Windows: Mateo). It:

1. Registers once with the client API and saves its `client_id`.
2. Polls for osquery queries to run and approved fix scripts.
3. Runs the queries with osquery and sends the rows back.
4. Runs the approved fix scripts and reports the results.

The formats, and sample clients to test with, are in
[server/client-api/README.md](../server/client-api/README.md#for-the-clients-kade-mateo).
