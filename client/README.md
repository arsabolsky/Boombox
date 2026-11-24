# Client

Runs on every monitored machine. It:

1. Registers once with the client API (`POST /api/v1/clients`) and saves its `client_id`.
2. Polls for osquery queries, runs them, and sends the rows back.
3. Polls for approved fix scripts and runs them.

| Folder | Client | Who |
|---|---|---|
| [`linux/`](linux/README.md) | Linux client in Go, runs as a systemd service | Kade |
| [`windows-client/`](windows-client/README.md) | Windows client in Go (current) and Python (earlier), runs as a Windows service | Mateo |

The request formats, and how to test without a real client, are in
[server/client-api/README.md](../server/client-api/README.md#for-the-clients-kade-mateo).
