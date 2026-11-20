"""Boombox client API. This file only puts the pieces together.

  ingest/routes.py       POST /api/v1/clients, GET /api/v1/poll/queries, POST /api/v1/results
  remediation/routes.py  GET /api/v1/poll/remediations

The dashboard has its own API, written in Go (server/dashboard-api). Both use the
same PostgreSQL database (server/database).

Run it:   uv run uvicorn main:app --reload --port 8080     then open http://localhost:8080/docs
"""

from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from ingest.routes import router as client_router
from remediation.routes import router as remediation_router

app = FastAPI(title="Boombox client API", description=__doc__)
app.include_router(client_router)
app.include_router(remediation_router)


@app.get("/", include_in_schema=False)
def home():
    return RedirectResponse("/docs")


@app.get("/health", include_in_schema=False)
def health():
    return {"status": "ok"}
