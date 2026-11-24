# Linux Client

Runs on every monitored Linux host (Kade). A Go program (`client.go`) that:

1. Registers with the client API and keeps the `client_id` it gets back.
2. Every `QUERY_INTERVAL` seconds, gets the osquery queries to run
   (`GET /api/v1/poll/queries`), runs them with osquery, and sends the rows
   (`POST /api/v1/results`).
3. Gets approved fix scripts (`GET /api/v1/poll/remediations`) and runs them with bash.

osquery must be installed on the host (https://osquery.io/downloads).

## Build and configure

```bash
go build -o boombox-client .
cp .env.example .env
```

In `.env`, set `API_HOST` to the server's client API, e.g. `http://<server>:8080`, and
`OS_VERSION` to the host's OS name (e.g. `Ubuntu 24.04.1 LTS`). The other paths already
match the server.

## Run as a service

`boombox-client.service` runs the client as root and restarts it if it stops. Two things
to know before installing it:

- It expects the program at `/user/sbin/boombox-client` (note "user", not "usr"). Copy the
  program there, or change `ExecStart` to where you put it.
- The client reads `.env` from its working directory, and systemd services start in `/`.
  Put `.env` in `/`, or add a `WorkingDirectory=` line pointing at the folder with `.env`.

```bash
sudo cp boombox-client.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now boombox-client
journalctl -u boombox-client -f        # watch its log
```
