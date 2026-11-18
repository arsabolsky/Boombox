"""STAND-IN for the remediations service (Aiden is building the real one).

These endpoints exist only so client developers can build the "get a fix script,
run it, report back" part of the client now. They always return the same harmless
example script (examples/example-command.sh or .ps1), and the result endpoint just
says "received".

The real remediations service will decide its own URLs and JSON shapes. When it exists,
point the client at it and delete this file (and its one line in main.py).
"""

from pathlib import Path

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from auth import current_client
from schemas import Client

EXAMPLES = Path(__file__).parent.parent / "examples"
EXAMPLE_SCRIPTS = {
    "bash": (EXAMPLES / "example-command.sh").read_text(),
    "powershell": (EXAMPLES / "example-command.ps1").read_text(),
}

router = APIRouter(prefix="/mock/remediations", tags=["mock remediations service"])


class Command(BaseModel):
    id: str
    shell: str  # "bash" or "powershell"
    script: str  # multi-line: save it to a file and run the file


class CommandResult(BaseModel):
    exit_code: int
    output: str  # what the script printed


@router.get("/commands", response_model=list[Command])
def get_commands(client: Client = Depends(current_client)):
    """Approved fix scripts for this client. (Mock: always one harmless example.)"""
    shell = "bash" if client.os == "linux" else "powershell"
    return [Command(id=f"example-{shell}", shell=shell, script=EXAMPLE_SCRIPTS[shell])]


@router.post("/commands/{command_id}/result")
def report_result(command_id: str, result: CommandResult, client: Client = Depends(current_client)):
    """Report what happened when the script ran. (Mock: nothing is stored.)"""
    print(f"[mock] {client.client_id} ran {command_id}: exit code {result.exit_code}")
    return {"received": command_id, "client_id": client.client_id, "exit_code": result.exit_code}
