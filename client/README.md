# Client

Runs on every monitored machine (Linux: Kade, Windows: Mateo). It:

1. Registers once with the client API and saves its `client_id`.
2. Polls for osquery queries, runs them, and sends the rows back.
3. Polls for approved fix scripts and runs them.

The formats, and how to test, are in
[server/client-api/README.md](../server/client-api/README.md#for-the-clients-kade-mateo).
