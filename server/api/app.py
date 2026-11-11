from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from psycopg.errors import ForeignKeyViolation

from server.storage.database import (
    get_remediations,
    insert_remediation,
    review_remediation,
)

app = FastAPI(title="Boombox API")


class RemediationRequest(BaseModel):
    event_id: int
    title: str
    summary: str | None = None
    proposed_script: str | None = None
    severity: str


class ReviewRequest(BaseModel):
    reviewed_by: str


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/api/v1/remediations")
def list_remediations():
    rows = get_remediations()

    return [
        {
            "id": row[0],
            "event_id": row[1],
            "title": row[2],
            "summary": row[3],
            "proposed_script": row[4],
            "severity": row[5],
            "status": row[6],
            "created_at": row[7],
            "reviewed_at": row[8],
            "reviewed_by": row[9],
        }
        for row in rows
    ]


@app.post("/api/v1/remediations")
def create_remediation(remediation: RemediationRequest):
    try:
        remediation_id = insert_remediation(
            event_id=remediation.event_id,
            title=remediation.title,
            summary=remediation.summary,
            proposed_script=remediation.proposed_script,
            severity=remediation.severity,
        )

        return {
            "id": remediation_id,
            "status": "pending_review",
        }

    except ForeignKeyViolation:
        raise HTTPException(
            status_code=404,
            detail=f"Event {remediation.event_id} does not exist",
        )


@app.post("/api/v1/remediations/{remediation_id}/approve")
def approve_remediation(
    remediation_id: int,
    review: ReviewRequest,
):
    row = review_remediation(
        remediation_id=remediation_id,
        status="approved",
        reviewed_by=review.reviewed_by,
    )

    if row is None:
        raise HTTPException(
            status_code=404,
            detail=f"Remediation {remediation_id} does not exist",
        )

    return {
        "id": row[0],
        "status": row[1],
        "reviewed_at": row[2],
        "reviewed_by": row[3],
    }


@app.post("/api/v1/remediations/{remediation_id}/deny")
def deny_remediation(
    remediation_id: int,
    review: ReviewRequest,
):
    row = review_remediation(
        remediation_id=remediation_id,
        status="denied",
        reviewed_by=review.reviewed_by,
    )

    if row is None:
        raise HTTPException(
            status_code=404,
            detail=f"Remediation {remediation_id} does not exist",
        )

    return {
        "id": row[0],
        "status": row[1],
        "reviewed_at": row[2],
        "reviewed_by": row[3],
    }