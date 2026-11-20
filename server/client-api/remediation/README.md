# Remediation

Fix scripts in the database.

- `save.py`: saves each new fix script as "pending review", and finds a client's approved ones.
- `routes.py`: `POST /api/v1/remediations/{id}/result`, where a client reports what happened
  when it ran an approved script.

Approving and denying happens on the dashboard (`server/dashboard-api`).
