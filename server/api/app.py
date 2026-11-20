from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from server.storage.database import (
    create_client_query,
    get_client_queries,
    get_clients,
    get_remediations,
    insert_client,
    insert_event,
    insert_remediation,
    review_remediation,
    update_client_query,
)

app = FastAPI(title="Boombox API")


class ClientRequest(BaseModel):
    hostname: str
    os_name: str | None = None
    os_version: str | None = None
    agent_version: str | None = None
    system_information: dict | None = None


class EventRequest(BaseModel):
    client_id: str
    event_type: str
    raw_data: dict


class RemediationRequest(BaseModel):
    event_id: int
    title: str
    summary: str | None = None
    proposed_script: str | None = None
    severity: str


class ReviewRequest(BaseModel):
    reviewed_by: str


class ClientQueryRequest(BaseModel):
    client_id: str
    query_name: str
    query_configuration: dict
    enabled: bool = True


class ClientQueryUpdateRequest(BaseModel):
    query_configuration: dict
    enabled: bool


@app.get("/health")
def health_check():
    return {"status": "ok"}


# ============================================
# CLIENTS
# ============================================

@app.post("/api/v1/clients")
def create_client(client: ClientRequest):
    client_id = insert_client(
        hostname=client.hostname,
        os_name=client.os_name,
        os_version=client.os_version,
        agent_version=client.agent_version,
        system_information=client.system_information,
    )

    return {
        "client_id": str(client_id),
        "status": "registered",
    }


@app.get("/api/v1/clients")
def list_clients():
    rows = get_clients()

    return [
        {
            "client_id": str(row[0]),
            "hostname": row[1],
            "os": row[2],
            "os_version": row[3],
            "agent_version": row[4],
            "system_information": row[5],
            "registered_at": row[6],
            "last_seen_at": row[7],
            "last_poll_at": row[8],
            "status": row[9],
        }
        for row in rows
    ]


# ============================================
# EVENTS
# ============================================

@app.post("/api/v1/events")
def create_event(event: EventRequest):
    try:
        event_id = insert_event(
            client_id=event.client_id,
            event_type=event.event_type,
            raw_data=event.raw_data,
        )
    except Exception:
        raise HTTPException(
            status_code=404,
            detail=f"Client {event.client_id} does not exist",
        )

    return {
        "id": event_id,
        "client_id": event.client_id,
    }


# ============================================
# REMEDIATIONS
# ============================================

@app.get("/api/v1/remediations")
def list_remediations(client_id: str | None = None):
    rows = get_remediations(client_id)

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
            "client_id": str(row[10]),
        }
        for row in rows
    ]


@app.post("/api/v1/remediations")
def create_remediation(remediation: RemediationRequest):
    remediation_id = insert_remediation(
        event_id=remediation.event_id,
        title=remediation.title,
        summary=remediation.summary,
        proposed_script=remediation.proposed_script,
        severity=remediation.severity,
    )

    if remediation_id is None:
        raise HTTPException(
            status_code=404,
            detail=f"Event {remediation.event_id} does not exist",
        )

    return {
        "id": remediation_id,
        "status": "pending_review",
    }


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


# ============================================
# CLIENT QUERIES
# ============================================

@app.post("/api/v1/client-queries")
def create_query(query: ClientQueryRequest):
    query_id = create_client_query(
        client_id=query.client_id,
        query_name=query.query_name,
        query_configuration=query.query_configuration,
        enabled=query.enabled,
    )

    return {
        "query_id": query_id,
        "client_id": query.client_id,
    }


@app.get("/api/v1/clients/{client_id}/queries")
def list_client_queries(
    client_id: str,
    enabled_only: bool = True,
):
    rows = get_client_queries(
        client_id=client_id,
        enabled_only=enabled_only,
    )

    return [
        {
            "query_id": row[0],
            "client_id": str(row[1]),
            "query_name": row[2],
            "query_configuration": row[3],
            "enabled": row[4],
            "version": row[5],
            "created_at": row[6],
            "updated_at": row[7],
        }
        for row in rows
    ]


@app.put("/api/v1/client-queries/{query_id}")
def update_query(
    query_id: int,
    update: ClientQueryUpdateRequest,
):
    row = update_client_query(
        query_id=query_id,
        query_configuration=update.query_configuration,
        enabled=update.enabled,
    )

    if row is None:
        raise HTTPException(
            status_code=404,
            detail=f"Query {query_id} does not exist",
        )

    return {
        "query_id": row[0],
        "version": row[1],
        "updated_at": row[2],
    }