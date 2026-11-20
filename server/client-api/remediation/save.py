"""Fix scripts in the database: saving new ones, handing out approved ones.

A fix script goes through these statuses (the remediations table):

    pending_review  ->  approved  ->  executed
                    ->  denied

  - write_and_save_fix()  saves a new one as pending_review (called by /api/v1/results)
  - a person approves or denies it on the dashboard (server/dashboard-api)
  - approved_scripts()    hands approved ones to the client and marks them executed
                          (called by /api/v1/poll/remediations)
"""

from analysis.remediation import make_script
from schemas import Client, Decision, Remediation
from storage.database import insert_event, insert_remediation, take_approved_remediations

SEVERITY = {"malicious": "high", "suspicious": "medium"}


def write_and_save_fix(client: Client, decision: Decision):
    """Runs after /api/v1/results has answered: write the script and save it for review."""
    fix = make_script(client, decision.findings)

    # The database stores each remediation against the event that caused it.
    event_id = insert_event(
        client_id=client.client_id,
        event_type="findings",
        raw_data=decision.model_dump(),
    )
    insert_remediation(
        event_id=event_id,
        title=fix.title,
        summary=fix.explanation,
        proposed_script=fix.script,
        severity=SEVERITY[decision.verdict],
    )


def approved_scripts(client: Client) -> list[Remediation]:
    """This client's approved fix scripts. Each one is handed out once, then marked executed."""
    return [
        Remediation(id=remediation_id, script=script)
        for remediation_id, script in take_approved_remediations(client.client_id)
        if script
    ]
