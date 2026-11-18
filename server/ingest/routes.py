"""Client endpoints: where clients get their queries and send back the results.

  1. Client:  GET  /poll      -> the osquery queries to run
  2. Client:  POST /results   -> the rows from those queries
              The server runs the pipeline:
                triage/decision.py         is anything bad?                    (answers right away)
                analysis/remediation.py    if so, write a script to fix it     (in the background)
                remediation/handoff.py     send that script to the remediations service (in the background)

Who the client is comes from auth.py (today: X-Client-Id and X-Client-OS headers).
These endpoints only ever return that client's own data.
"""

import uuid
from os import getenv

from fastapi import APIRouter, BackgroundTasks, Depends

from analysis.remediation import make_script
from auth import current_client
from ingest.queries import extra_queries, queries_for
from remediation.handoff import send_to_remediation_api
from schemas import Client, Finding, PollResponse, Remediation, Results, ResultsResponse
from triage.decision import decide

POLL_INTERVAL = int(getenv("POLL_INTERVAL", "300"))  # seconds

router = APIRouter(tags=["client"])

# Every endpoint here takes `client: Client = Depends(current_client)`.
# That's what makes them safe once auth.py does real authentication.


@router.get("/poll", response_model=PollResponse)
def poll(client: Client = Depends(current_client)):
    """Called by the client every `poll_interval` seconds: the queries to run now.

    One-time queries (see POST /clients/{client_id}/queries) are handed out once.
    """
    return PollResponse(
        poll_interval=POLL_INTERVAL,
        queries=queries_for(client) + extra_queries.pop(client.client_id, []),
    )


@router.post("/results", response_model=ResultsResponse)
def results(body: Results, background: BackgroundTasks, client: Client = Depends(current_client)):
    """Called by the client with the rows from the queries it ran.

    Answers right away with the decision. If anything looked bad, the fix script is
    written in the background (it can take a minute or two) and sent to the
    remediations service under `remediation_id`. The client doesn't need to wait for it.
    """
    ok_results = [r for r in body.results if r.error is None]
    decision = decide(client, ok_results)
    if decision.verdict == "benign":
        return ResultsResponse(decision=decision, remediation_id=None)

    remediation_id = str(uuid.uuid4())
    background.add_task(write_and_send_fix, remediation_id, client, decision.findings)
    return ResultsResponse(decision=decision, remediation_id=remediation_id)


def write_and_send_fix(remediation_id: str, client: Client, findings: list[Finding]):
    """Runs after /results has answered: write the script, hand it to the remediations service."""
    script = make_script(client, findings)
    remediation = Remediation(
        id=remediation_id,
        client_id=client.client_id,
        hostname=client.hostname,
        os=client.os,
        shell=script.shell,
        script=script.script,
        explanation=script.explanation,
        findings=findings,
    )
    send_to_remediation_api(remediation)
