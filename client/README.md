# Client

Runs on every monitored machine (Linux: Kade, Windows: Mateo). It:

1. Asks the backend API which osquery queries to run (`GET /poll`).
2. Runs them with osquery and sends the rows back (`POST /results`).
3. Runs fix scripts once a person has approved them, and reports the result.

The request formats, headers and example data are in
[server/README.md](../server/README.md#for-the-clients-kade-mateo).
