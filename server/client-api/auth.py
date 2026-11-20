"""Who is calling the API?

Every client endpoint gets the caller from `current_client` and only returns data
for that client. This is the ONE place to change when real authentication exists.

Right now a client registers once (POST /api/v1/clients), gets a client_id back, and
sends it on every request:

    X-Client-Id: 11111111-1111-4111-8111-111111111111

We look that id up in the database. Unknown ids get a 401. The client's OS and
hostname come from the database, not from the request.

When real authentication is ready, rewrite `current_client` to read a token instead
(authorization: str = Header()), check it, and return the Client that token belongs
to. Nothing else has to change.
"""

from fastapi import Header, HTTPException

from schemas import Client
from storage.database import get_client


def current_client(
    x_client_id: str = Header(description="The client_id you got from POST /api/v1/clients"),
) -> Client:
    row = get_client(x_client_id)
    if row is None:
        raise HTTPException(status_code=401, detail="Unknown client. Register with POST /api/v1/clients first.")

    client_id, hostname, os_name, status = row
    if status != "active":
        raise HTTPException(status_code=403, detail="This client is disabled.")

    os_name = (os_name or "").lower()
    if os_name not in ("linux", "windows"):
        raise HTTPException(status_code=400, detail=f"Client OS must be linux or windows, not {os_name!r}.")

    return Client(client_id=str(client_id), os=os_name, hostname=hostname)
