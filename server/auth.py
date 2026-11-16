"""Who is calling the API?

Every client endpoint gets the caller from `current_client` and only returns data
for that client. This is the ONE place to change when real authentication exists.

Right now there is no real authentication: the client says who it is with three
headers and we believe it.

    X-Client-Id: linux-vm-1        (required: stable id, e.g. osquery's system_info.uuid)
    X-Client-OS: linux             (required: "linux" or "windows")
    X-Client-Hostname: ubuntu-1    (optional)

When real authentication is ready, rewrite `current_client` to:

    1. read the token:      authorization: str = Header()
    2. check it:            ask the auth service / look the token up in the database
    3. reject bad ones:     raise HTTPException(status_code=401, detail="invalid token")
    4. return the Client    built from what the auth system says about this token,
                            not from what the client claims about itself

Nothing else has to change: every endpoint that uses Depends(current_client) is then
protected, and still only sees that client's data. If the auth system knows more about
a client (its group, what it may run, ...), add those fields to `Client` in schemas.py
and use them in `queries_for` (queries.py).
"""

from typing import Literal

from fastapi import Header

from schemas import Client


def current_client(
    x_client_id: str = Header(description="Stable id for this machine, e.g. osquery's system_info.uuid"),
    x_client_os: Literal["linux", "windows"] = Header(description='"linux" or "windows"'),
    x_client_hostname: str | None = Header(default=None, description="Optional, shown to the people reviewing fixes"),
) -> Client:
    return Client(
        client_id=x_client_id,
        os=x_client_os,
        hostname=x_client_hostname or x_client_id,
    )
