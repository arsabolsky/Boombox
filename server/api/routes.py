"""Admin endpoints, for the dashboard.

Not protected yet; the dashboard team decides how.
"""

from fastapi import APIRouter

from ingest.queries import extra_queries
from schemas import Query

router = APIRouter(tags=["admin"])


@router.post("/clients/{client_id}/queries")
def add_query(client_id: str, query: Query):
    """Ask one client to run a custom query once, on its next poll."""
    extra_queries.setdefault(client_id, []).append(query)
    return {"queued": query.name, "client_id": client_id}
