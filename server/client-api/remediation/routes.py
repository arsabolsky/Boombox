"""Client endpoint for getting approved fix scripts.

  Client:  GET /api/v1/poll/remediations  -> approved fix scripts to run (each one is sent once)
"""

from fastapi import APIRouter, Depends

from auth import current_client
from remediation.save import approved_scripts
from schemas import Client, Remediation
from storage.database import record_client_activity

router = APIRouter(prefix="/api/v1", tags=["client"])


@router.get("/poll/remediations", response_model=list[Remediation])
def poll_remediations(client: Client = Depends(current_client)):
    """Called by the client every few minutes: fix scripts a person approved.

    Run each one right away. Each script is sent only once: the server marks it
    executed as it hands it out.
    """
    record_client_activity(client.client_id, polled=True)
    return approved_scripts(client)
