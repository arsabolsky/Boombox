# Remediation

Fix scripts in the database.

- `save.py`: saves each new fix script as "pending review", and hands out approved ones.
- `routes.py`: `GET /api/v1/poll/remediations`, where a client gets its approved fix
  scripts. Each one is marked executed as it's handed out, so it's sent only once.

Approving and denying happens on the dashboard (`server/dashboard-api`).
