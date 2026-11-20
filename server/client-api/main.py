"""Boombox client API. This file only puts the pieces together.

  ingest/routes.py       register, GET /api/v1/poll, POST /api/v1/results
  remediation/routes.py  POST /api/v1/remediations/{id}/result

The dashboard has its own API, written in Go (server/dashboard-api). Both use the
same PostgreSQL database (server/database).

Run it:   uv run uvicorn main:app --reload --port 8080     then open http://localhost:8080/docs
"""

from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from ingest.routes import router as client_router
from remediation.routes import router as result_router

app = FastAPI(title="Boombox client API", description=__doc__)
app.include_router(client_router)
app.include_router(result_router)


@app.get("/", include_in_schema=False)
def home():
    return RedirectResponse("/docs")


@app.get("/health", include_in_schema=False)
def health():
    return {"status": "ok"}
