"""Boombox backend API.

The whole flow:

  1. Client:  GET  /poll      -> the osquery queries to run
  2. Client:  POST /results   -> the rows from those queries
              The server runs the pipeline:
                decision.py     is anything bad?          (answers right away)
                remediation.py  if so, write a multi-line script to fix it   (in the background)
                handoff.py      send that script to the remediations API     (in the background)

Approving scripts and sending them to clients is the remediations API's job
(another team), not this one. Until it exists, mock_remediations.py stands in for
it so client developers can build that part of the client.

Who the client is comes from auth.py (today: X-Client-Id and X-Client-OS headers).
Client endpoints only ever return that client's own data.

Run it:   uvicorn main:app --reload     then open http://localhost:8000/docs

One-time queries are kept in memory (`extra_queries` below), so they reset when
the server restarts.
"""

import uuid
from os import getenv

from fastapi import BackgroundTasks, Depends, FastAPI
from fastapi.responses import RedirectResponse

from auth import current_client
from decision import decide
from handoff import send_to_remediation_api
from mock_remediations import router as mock_remediations_router
from queries import queries_for
from remediation import make_script
from schemas import Client, Finding, PollResponse, Query, Remediation, Results, ResultsResponse

POLL_INTERVAL = int(getenv("POLL_INTERVAL", "300"))  # seconds

app = FastAPI(title="Boombox API", description=__doc__)
app.include_router(mock_remediations_router)  # delete when the real remediations API exists

extra_queries: dict[str, list[Query]] = {}  # client_id -> one-time queries not yet sent


# ----- Client endpoints ----------------------------------------------------------
# Every one of these takes `client: Client = Depends(current_client)`.
# That's what makes them safe once auth.py does real authentication.


@app.get("/poll", response_model=PollResponse, tags=["client"])
def poll(client: Client = Depends(current_client)):
    """Called by the client every `poll_interval` seconds: the queries to run now.

    One-time queries (see POST /clients/{client_id}/queries) are handed out once.
    """
    return PollResponse(
        poll_interval=POLL_INTERVAL,
        queries=queries_for(client) + extra_queries.pop(client.client_id, []),
    )


@app.post("/results", response_model=ResultsResponse, tags=["client"])
def results(body: Results, background: BackgroundTasks, client: Client = Depends(current_client)):
    """Called by the client with the rows from the queries it ran.

    Answers right away with the decision. If anything looked bad, the fix script is
    written in the background (it can take a minute or two) and sent to the
    remediations API under `remediation_id`. The client doesn't need to wait for it.
    """
    ok_results = [r for r in body.results if r.error is None]
    decision = decide(client, ok_results)
    if decision.verdict == "benign":
        return ResultsResponse(decision=decision, remediation_id=None)

    remediation_id = str(uuid.uuid4())
    background.add_task(write_and_send_fix, remediation_id, client, decision.findings)
    return ResultsResponse(decision=decision, remediation_id=remediation_id)


def write_and_send_fix(remediation_id: str, client: Client, findings: list[Finding]):
    """Runs after /results has answered: write the script, hand it to the remediations API."""
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


# ----- Admin endpoints -------------------------------------------------------------
# Not protected yet; the dashboard team decides how.


@app.post("/clients/{client_id}/queries", tags=["admin"])
def add_query(client_id: str, query: Query):
    """Ask one client to run a custom query once, on its next poll."""
    extra_queries.setdefault(client_id, []).append(query)
    return {"queued": query.name, "client_id": client_id}


@app.get("/", include_in_schema=False)
def home():
    return RedirectResponse("/docs")
