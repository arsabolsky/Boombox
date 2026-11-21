# Dashboard

The website where a person reviews the fix scripts the AI writes and approves or denies
them (Xander). The code is in `frontend/boombox/`. It talks to the dashboard API in
[server/dashboard-api](../server/dashboard-api/README.md).

`docker compose up --build` from the repo root builds the website and serves it with nginx
at http://localhost (port 80). nginx also forwards the website's `/api` calls to the
dashboard API. The two files for that are `Dockerfile` and `nginx.conf` in this folder.

After changing the website's code, rebuild it with `docker compose up -d --build dashboard`.
For live reloading while you work on it, run `npm run dev` in `frontend/boombox/` instead
(it opens at http://localhost:5173).
