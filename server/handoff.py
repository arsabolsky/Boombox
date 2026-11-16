"""Where finished remediation scripts go: the remediations API (another team's service).

Our API's job ends here. The remediations API decides what happens next: showing the
script to a person, approval, sending it to the client, and keeping track of it.

How it works today:
  - If REMEDIATION_API_URL is set, each remediation is POSTed there as JSON
    (the Remediation shape in schemas.py).
  - If it isn't set, the remediation is printed to the server's console instead,
    so you can see what would have been sent: `docker compose logs -f api`.

If the remediations API wants something different (another URL, another JSON shape,
an API key, a database insert...), change only this function.
"""

import os

import httpx

from schemas import Remediation


def send_to_remediation_api(remediation: Remediation) -> None:
    url = os.getenv("REMEDIATION_API_URL")
    if url:
        response = httpx.post(f"{url.rstrip('/')}/remediations", json=remediation.model_dump(), timeout=10)
        response.raise_for_status()
        return

    print(f"\n=== Remediation {remediation.id} for {remediation.hostname} ({remediation.shell}) ===")
    print(remediation.explanation)
    print(remediation.script)
