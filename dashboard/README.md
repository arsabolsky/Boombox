# Dashboard

The website where a person reviews the fix scripts the AI writes (Xander). The code is in
`frontend/boombox/`. It talks to the dashboard API in
[server/dashboard-api](../server/dashboard-api/README.md).

| Page | What it shows |
|---|---|
| Review | Fix scripts waiting for review: severity, client, the AI's explanation, and the script. Edit the script (Modify), then Approve & deploy or Deny |
| Backlog | Every fix that was approved or denied, and by whom |
| Dashboard | Alerts over time, by severity and by client |
| Clients | Registered machines, when they were last seen, and their pending fixes |

`docker compose up --build` from the repo root builds the website and serves it with nginx
at http://localhost (port 80). nginx also forwards the website's `/api` calls to the
dashboard API. The two files for that are `Dockerfile` and `nginx.conf` in this folder.

After changing the website's code, rebuild it with `docker compose up -d --build dashboard`.
For live reloading while you work on it, run `npm run dev` in `frontend/boombox/` instead
(it opens at http://localhost:5173).
