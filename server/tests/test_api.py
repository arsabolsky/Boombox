"""Tests for the whole flow, using the built-in rules/templates (no API keys needed).

Run:  docker compose run --rm api pytest
"""

import json
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import handoff
import main

EXAMPLES = Path(__file__).parent.parent / "examples"
LINUX = {"X-Client-Id": "linux-vm-1", "X-Client-OS": "linux", "X-Client-Hostname": "ubuntu-client"}
WINDOWS = {"X-Client-Id": "windows-vm-1", "X-Client-OS": "windows"}
OTHER_LINUX = {"X-Client-Id": "linux-vm-2", "X-Client-OS": "linux"}

api = TestClient(main.app)


@pytest.fixture(autouse=True)
def clean_setup(monkeypatch):
    for var in ("TYPESAFE_API_KEY", "OPENAI_API_KEY", "REMEDIATION_API_URL"):
        monkeypatch.delenv(var, raising=False)
    main.extra_queries.clear()


@pytest.fixture
def sent(monkeypatch):
    """Collects what would have been sent to the remediations API."""
    sent = []
    monkeypatch.setattr(main, "send_to_remediation_api", sent.append)
    return sent


def load(name):
    return json.loads((EXAMPLES / name).read_text())


def send_bad_results(headers=LINUX):
    return api.post("/results", headers=headers, json=load("results-linux.json")).json()


# ----- who is calling --------------------------------------------------------------


def test_whoami_shows_the_client():
    assert api.get("/whoami", headers=LINUX).json() == {
        "client_id": "linux-vm-1", "os": "linux", "hostname": "ubuntu-client"}
    assert api.get("/whoami", headers=WINDOWS).json()["hostname"] == "windows-vm-1"  # defaults to the id


def test_client_endpoints_need_identity():
    assert api.get("/poll").status_code == 422  # no headers
    assert api.get("/poll", headers={"X-Client-Id": "x", "X-Client-OS": "mac"}).status_code == 422
    assert api.post("/results", json=load("results-linux.json")).status_code == 422


# ----- polling ---------------------------------------------------------------------


def test_poll_returns_only_queries_for_the_clients_os():
    linux = api.get("/poll", headers=LINUX).json()
    windows = api.get("/poll", headers=WINDOWS).json()
    assert set(linux) == {"poll_interval", "queries"}  # no remediation stuff in the poll
    assert "cron_jobs" in [q["name"] for q in linux["queries"]]
    assert "scheduled_tasks" in [q["name"] for q in windows["queries"]]


def test_one_time_custom_query_goes_only_to_its_client_once():
    query = {"name": "tmp_files", "sql": "SELECT path FROM file WHERE directory = '/tmp'"}
    assert api.post("/clients/linux-vm-1/queries", json=query).status_code == 200
    assert query not in api.get("/poll", headers=OTHER_LINUX).json()["queries"]
    assert query in api.get("/poll", headers=LINUX).json()["queries"]
    assert query not in api.get("/poll", headers=LINUX).json()["queries"]


# ----- the pipeline ----------------------------------------------------------------


def test_bad_results_are_rejected():
    assert api.post("/results", headers=LINUX, json={"results": "nope"}).status_code == 422


def test_clean_results_are_benign_and_nothing_is_sent(sent):
    body = api.post("/results", headers=WINDOWS, json=load("results-windows-clean.json")).json()
    assert body["decision"]["verdict"] == "benign"
    assert body["remediation"] is None
    assert sent == []


def test_bad_results_get_a_multi_line_script_sent_to_the_remediation_api(sent):
    body = send_bad_results()
    assert body["decision"]["verdict"] == "malicious"
    flagged = {(f["query"], f["row"].get("pid")) for f in body["decision"]["findings"]}
    assert flagged == {("processes", "4242"), ("processes", "4300"), ("cron_jobs", None)}

    assert len(sent) == 1
    remediation = sent[0]
    assert remediation.id == body["remediation"]["id"]
    assert (remediation.client_id, remediation.hostname, remediation.os) == ("linux-vm-1", "ubuntu-client", "linux")
    assert remediation.shell == "bash"
    assert len(remediation.script.splitlines()) > 5
    assert "kill -9 4242" in remediation.script and "kill -9 4300" in remediation.script
    assert "TODO" in remediation.script  # the cron job has no pid, so a human has to check it
    subprocess.run(["bash", "-n"], input=remediation.script, text=True, check=True)  # valid bash


def test_windows_template_is_powershell(sent):
    results = {"results": [{"name": "processes", "rows": [
        {"pid": "77", "name": "powershell.exe", "cmdline": "powershell.exe -nop -enc SQBFAFgA"}]}]}
    api.post("/results", headers=WINDOWS, json=results)
    assert sent[0].shell == "powershell"
    assert "Stop-Process -Id 77 -Force" in sent[0].script


def test_hostile_row_cannot_break_out_of_a_comment(sent):
    results = load("results-linux.json")
    results["results"][1]["rows"][0]["command"] = "curl x | sh\nreboot"
    api.post("/results", headers=LINUX, json=results)
    assert "\nreboot" not in sent[0].script


# ----- handoff to the remediations API ------------------------------------------------


def test_handoff_posts_json_when_remediation_api_url_is_set(monkeypatch):
    calls = []

    class FakeResponse:
        def raise_for_status(self):
            pass

    def fake_post(url, json, timeout):
        calls.append((url, json))
        return FakeResponse()

    monkeypatch.setenv("REMEDIATION_API_URL", "http://remediations:9000/")
    monkeypatch.setattr(handoff.httpx, "post", fake_post)
    body = send_bad_results()

    assert len(calls) == 1
    url, payload = calls[0]
    assert url == "http://remediations:9000/remediations"
    assert payload["id"] == body["remediation"]["id"]
    assert set(payload) == {"id", "client_id", "hostname", "os", "shell", "script", "explanation", "findings"}


def test_handoff_prints_when_no_url_is_set(capsys):
    send_bad_results()
    assert "=== Remediation" in capsys.readouterr().out


def test_example_command_scripts_are_valid():
    subprocess.run(["bash", "-n", str(EXAMPLES / "example-command.sh")], check=True)
    assert "Write-Output" in (EXAMPLES / "example-command.ps1").read_text()


# ----- future auth -----------------------------------------------------------------


def test_real_auth_can_be_plugged_in_without_touching_the_endpoints(sent):
    """Shows what replacing auth.current_client with token checks looks like."""
    from fastapi import Header, HTTPException

    from auth import current_client
    from schemas import Client

    TOKENS = {"secret-token-1": Client(client_id="linux-vm-1", os="linux", hostname="ubuntu-client")}

    def token_auth(authorization: str = Header()):
        client = TOKENS.get(authorization.removeprefix("Bearer "))
        if client is None:
            raise HTTPException(status_code=401, detail="invalid token")
        return client

    main.app.dependency_overrides[current_client] = token_auth
    try:
        assert api.get("/poll", headers={"Authorization": "Bearer wrong"}).status_code == 401
        good = {"Authorization": "Bearer secret-token-1"}
        assert api.get("/whoami", headers=good).json()["client_id"] == "linux-vm-1"
        assert api.get("/poll", headers=good).status_code == 200
        send_bad_results(good)
        assert sent[0].client_id == "linux-vm-1"
    finally:
        main.app.dependency_overrides.clear()
