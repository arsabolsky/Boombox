"""Boombox backend API. This file only puts the pieces together.

  ingest/routes.py     client endpoints: GET /poll, POST /results
  api/routes.py        admin endpoints: POST /clients/{client_id}/queries
  remediation/mock.py  stand-in for the remediations service (Aiden)

Approving scripts and sending them to clients is the remediations service's job, not
this one. Until it exists, remediation/mock.py stands in for it so client
developers can build that part of the client.

Run it:   uv run uvicorn main:app --reload     then open http://localhost:8000/docs
"""

from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from api.routes import router as admin_router
from ingest.routes import router as client_router
from remediation.mock import router as mock_remediations_router

app = FastAPI(title="Boombox API", description=__doc__)
app.include_router(client_router)
app.include_router(admin_router)
app.include_router(mock_remediations_router)  # delete when the real remediations service exists


@app.get("/", include_in_schema=False)
def home():
    return RedirectResponse("/docs")
