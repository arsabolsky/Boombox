# Dashboard

Web UI where a person reviews the fix scripts the AI writes (Xander, with Aiden).

- Show new fix scripts as they come in, with the AI's explanation and findings
- Approve or deny each script before it's sent to the client
- Send a one-time custom query to one client (`POST /clients/{client_id}/queries` on the backend API)

The format of the fix scripts is in
[server/README.md](../server/README.md#for-the-remediations-service-aiden).
