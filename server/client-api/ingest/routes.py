"""Client endpoints: register, get work to do, send back results.

  1. Client:  POST /api/v1/clients   -> register once, get a client_id
  2. Client:  GET  /api/v1/poll      -> the osquery queries to run + approved fix scripts
  3. Client:  POST /api/v1/results   -> the rows from those queries
              The server runs the pipeline:
                triage/decision.py         is anything bad?                 (answers right away)
                analysis/remediation.py    if so, write a script to fix it  (in the background)
                remediation/save.py        save it for a person to review   (in the background)

Who the client is comes from auth.py (the X-Client-Id header).
These endpoints only ever return that client's own data.
"""

import os

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from auth import current_client
from ingest.queries import queries_for
from remediation.save import approved_scripts, write_and_save_fix
from schemas import Client, Decision, PollResponse, RegisterRequest, RegisterResponse, Results
from storage.database import insert_client, record_client_activity
from triage.decision import decide

POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "300"))  # seconds

router = APIRouter(prefix="/api/v1", tags=["client"])


@router.post("/clients", response_model=RegisterResponse)
def register(body: RegisterRequest):
    """Register a new client. Do this once and save the client_id it returns."""
    client_id = insert_client(
        hostname=body.hostname,
        os_name=body.os,
        os_version=body.os_version,
        agent_version=body.agent_version,
        system_information=body.system_information,
    )
    return RegisterResponse(client_id=str(client_id))


@router.get("/poll", response_model=PollResponse)
def poll(client: Client = Depends(current_client)):
    """Called by the client every `poll_interval` seconds: the work to do now.

    - queries: run each one with osquery, then POST the rows to /api/v1/results
    - scripts: fix scripts a person approved; run each, then report the result
    """
    record_client_activity(client.client_id, polled=True)
    return PollResponse(
        poll_interval=POLL_INTERVAL,
        queries=queries_for(client),
        scripts=approved_scripts(client),
    )


@router.post("/results", response_model=Decision)
def results(body: Results, background: BackgroundTasks, client: Client = Depends(current_client)):
    """Called by the client with the rows from the queries it ran.

    Answers right away with the decision. If anything looked bad, the fix script is
    written in the background (it can take a minute or two) and saved for a person
    to review on the dashboard. The client doesn't need to wait for it.
    """
    if not (os.getenv("TYPESAFE_API_KEY") and os.getenv("OPENAI_API_KEY")):
        raise HTTPException(
            status_code=503,
            detail="Your request was valid, but this server has no AI keys "
            "(TYPESAFE_API_KEY and OPENAI_API_KEY), so it can't check results.",
        )

    record_client_activity(client.client_id)
    ok_results = [r for r in body.results if r.error is None]
    decision = decide(client, ok_results)
    if decision.verdict != "benign":
        background.add_task(write_and_save_fix, client, decision)
    return decision
