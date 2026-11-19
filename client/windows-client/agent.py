import json
import os
import signal
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urljoin
from urllib.request import Request, urlopen

BASE_DIR = Path(__file__).resolve().parent
STOP_EVENT = threading.Event()


def log(message):
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    print(f"{timestamp} {message}", flush=True)


def load_env_file(path):
    """Load simple KEY=VALUE settings without requiring python-dotenv."""
    if not path.exists():
        return

    for line_number, raw_line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ValueError(f"Invalid .env line {line_number}: expected KEY=VALUE")

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]

        # Values already supplied by Windows or NSSM take priority.
        os.environ.setdefault(key, value)


load_env_file(BASE_DIR / ".env")


def env_bool(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_int(name, default, minimum=1):
    value = int(os.environ.get(name, default))
    if value < minimum:
        raise ValueError(f"{name} must be at least {minimum}.")
    return value


API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000/").strip()
API_TOKEN = os.environ.get("API_TOKEN", "").strip()
OSQUERY_PATH = os.environ.get(
    "OSQUERY_PATH", r"C:\Program Files\osquery\osqueryi.exe"
).strip()
CLIENT_ID_PATH = Path(
    os.environ.get("CLIENT_ID_PATH", str(BASE_DIR / "client-id.txt"))
)
CHECK_WHOAMI = env_bool("CHECK_WHOAMI", False)
RUN_ONCE = env_bool("RUN_ONCE", False)
ENABLE_REMEDIATION = env_bool("ENABLE_REMEDIATION", True)
REMEDIATION_API_PREFIX = os.environ.get(
    "REMEDIATION_API_PREFIX", "mock/remediations"
).strip().strip("/")
REMEDIATION_POLL_INTERVAL_SECONDS = env_int(
    "REMEDIATION_POLL_INTERVAL_SECONDS", 10
)
REMEDIATION_TIMEOUT_SECONDS = env_int("REMEDIATION_TIMEOUT_SECONDS", 60)
QUERY_TIMEOUT_SECONDS = env_int("QUERY_TIMEOUT_SECONDS", 30)
HTTP_TIMEOUT_SECONDS = env_int("HTTP_TIMEOUT_SECONDS", 30)
RESULTS_TIMEOUT_SECONDS = env_int("RESULTS_TIMEOUT_SECONDS", 180)
DEFAULT_POLL_INTERVAL_SECONDS = env_int("DEFAULT_POLL_INTERVAL_SECONDS", 300)
MINIMUM_POLL_INTERVAL_SECONDS = env_int("MINIMUM_POLL_INTERVAL_SECONDS", 5)
MAXIMUM_POLL_INTERVAL_SECONDS = env_int("MAXIMUM_POLL_INTERVAL_SECONDS", 3600)
MAXIMUM_QUERY_OUTPUT_BYTES = env_int("MAXIMUM_QUERY_OUTPUT_BYTES", 5 * 1024 * 1024)


def error_result(name, message, exit_code=None, stderr=None):
    details = [message.rstrip(".")]
    if exit_code is not None:
        details.append(f"exit code {exit_code}")
    if stderr and stderr.strip():
        details.append(stderr.strip())
    return {"name": name, "error": ": ".join(details)}


def run_osquery(name, sql):
    if not isinstance(sql, str) or not sql.strip():
        return error_result(name, "The server returned an empty SQL query.")

    try:
        completed = subprocess.run(
            [OSQUERY_PATH, "--json", sql],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=QUERY_TIMEOUT_SECONDS,
            shell=False,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
    except subprocess.TimeoutExpired:
        return error_result(
            name, f"The osquery query exceeded {QUERY_TIMEOUT_SECONDS} seconds."
        )
    except OSError as error:
        return error_result(name, f"Could not start osqueryi.exe: {error}")

    if completed.returncode != 0:
        return error_result(
            name,
            "osquery returned a nonzero exit code.",
            completed.returncode,
            completed.stderr,
        )

    output_size = len(completed.stdout.encode("utf-8"))
    if output_size > MAXIMUM_QUERY_OUTPUT_BYTES:
        return error_result(
            name,
            f"osquery output exceeded {MAXIMUM_QUERY_OUTPUT_BYTES} bytes.",
        )

    try:
        rows = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        return error_result(name, f"osquery returned invalid JSON: {error}")

    if not isinstance(rows, list):
        return error_result(name, "osquery did not return a JSON array.")

    result = {"name": name, "rows": rows}
    if completed.stderr.strip():
        log(f"osquery warning for {name}: {completed.stderr.strip()}")
    return result


def get_or_create_client_id(osquery_uuid):
    if CLIENT_ID_PATH.exists():
        stored = CLIENT_ID_PATH.read_text(encoding="utf-8").strip()
        try:
            return str(uuid.UUID(stored))
        except ValueError as error:
            raise RuntimeError(
                f"The client ID file contains an invalid UUID: {CLIENT_ID_PATH}"
            ) from error

    try:
        client_id = str(uuid.UUID(osquery_uuid))
    except (ValueError, AttributeError, TypeError):
        client_id = str(uuid.uuid4())

    CLIENT_ID_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        with CLIENT_ID_PATH.open("x", encoding="utf-8") as file:
            file.write(client_id + "\n")
    except FileExistsError:
        # Another instance created it between our existence check and write.
        return get_or_create_client_id(osquery_uuid)

    log(f"Created persistent client ID file at {CLIENT_ID_PATH}")
    return client_id


def get_identity():
    result = run_osquery(
        "client_identity",
        "SELECT uuid AS client_id, hostname FROM system_info;",
    )
    if "error" in result:
        raise RuntimeError(result["error"])
    if not result["rows"]:
        raise RuntimeError("The system_info query returned no identity row.")

    row = result["rows"][0]
    hostname = str(row.get("hostname", "")).strip()
    osquery_uuid = str(row.get("client_id", "")).strip()
    if not hostname:
        raise RuntimeError("The system_info result did not include a hostname.")

    return {
        "client_id": get_or_create_client_id(osquery_uuid),
        "hostname": hostname,
        "operating_system": "windows",
    }


def client_headers(identity):
    headers = {
        "Accept": "application/json",
        "X-Client-Id": identity["client_id"],
        "X-Client-OS": identity["operating_system"],
        "X-Client-Hostname": identity["hostname"],
    }
    if API_TOKEN:
        headers["Authorization"] = f"Bearer {API_TOKEN}"
    return headers


def api_request(method, endpoint, identity, payload=None, timeout=None, extra_headers=None):
    url = urljoin(API_BASE_URL.rstrip("/") + "/", endpoint.lstrip("/"))
    headers = client_headers(identity)
    if extra_headers:
        headers.update(extra_headers)

    body = None
    if payload is not None:
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = Request(url, data=body, headers=headers, method=method)
    try:
        with urlopen(request, timeout=timeout or HTTP_TIMEOUT_SECONDS) as response:
            response_body = response.read()
            if not response_body:
                return response.status, None
            return response.status, json.loads(response_body.decode("utf-8"))
    except HTTPError as error:
        response_body = error.read(4096).decode("utf-8", errors="replace")
        raise RuntimeError(
            f"{method} {url} returned HTTP {error.code}: {response_body}"
        ) from error
    except URLError as error:
        raise RuntimeError(f"Could not reach {url}: {error.reason}") from error
    except TimeoutError as error:
        raise RuntimeError(f"{method} {url} timed out.") from error
    except json.JSONDecodeError as error:
        raise RuntimeError(f"{method} {url} returned invalid JSON: {error}") from error


def check_whoami(identity):
    status, _ = api_request("GET", "whoami", identity)
    log(f"GET /whoami returned HTTP {status}")


def poll(identity):
    status, response = api_request("GET", "poll", identity)
    if status == 204 or response is None:
        return {"poll_interval": DEFAULT_POLL_INTERVAL_SECONDS, "queries": []}
    if not isinstance(response, dict):
        raise RuntimeError("GET /poll did not return a JSON object.")

    queries = response.get("queries", [])
    if not isinstance(queries, list):
        raise RuntimeError("GET /poll returned a non-list queries value.")

    return {
        "poll_interval": response.get(
            "poll_interval", DEFAULT_POLL_INTERVAL_SECONDS
        ),
        "queries": queries,
    }


def post_results(identity, results):
    submission_id = str(uuid.uuid4())
    status, response = api_request(
        "POST",
        "results",
        identity,
        payload={"results": results},
        timeout=RESULTS_TIMEOUT_SECONDS,
        extra_headers={"Idempotency-Key": submission_id},
    )
    log(f"POST /results submission {submission_id} returned HTTP {status}")

    if isinstance(response, dict):
        decision = response.get("decision")
        if isinstance(decision, dict):
            log(f"Server decision: {decision.get('verdict', 'unknown')}")
        remediation_id = response.get("remediation_id")
        if remediation_id:
            log(f"Server created remediation {remediation_id}")


def get_remediation_commands(identity):
    endpoint = f"{REMEDIATION_API_PREFIX}/commands"
    status, response = api_request("GET", endpoint, identity)
    if status == 204 or response is None:
        return []
    if not isinstance(response, list):
        raise RuntimeError(f"GET /{endpoint} did not return a JSON list.")
    return response


def combine_command_output(stdout, stderr):
    parts = []
    if stdout:
        parts.append(stdout.strip())
    if stderr:
        parts.append("[stderr]\n" + stderr.strip())
    output = "\n".join(part for part in parts if part)
    encoded = output.encode("utf-8")
    if len(encoded) > MAXIMUM_QUERY_OUTPUT_BYTES:
        output = encoded[:MAXIMUM_QUERY_OUTPUT_BYTES].decode(
            "utf-8", errors="replace"
        )
        output += "\n[output truncated]"
    return output


def execute_remediation(command):
    command_id = str(command.get("id", "")).strip()
    shell = str(command.get("shell", "")).strip().lower()
    script = command.get("script", "")

    if not command_id:
        raise ValueError("Remediation command did not include an id.")
    if shell != "powershell":
        return command_id, {
            "exit_code": -1,
            "output": f"Unsupported Windows remediation shell: {shell or 'missing'}",
        }
    if not isinstance(script, str) or not script.strip():
        return command_id, {
            "exit_code": -1,
            "output": "Remediation command did not include a script.",
        }

    script_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            suffix=".ps1",
            prefix="boombox-",
            delete=False,
        ) as script_file:
            script_file.write(script)
            script_file.write("\n")
            script_path = Path(script_file.name)

        completed = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(script_path),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=REMEDIATION_TIMEOUT_SECONDS,
            shell=False,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        return command_id, {
            "exit_code": completed.returncode,
            "output": combine_command_output(completed.stdout, completed.stderr),
        }
    except subprocess.TimeoutExpired as error:
        stdout = error.stdout or ""
        stderr = error.stderr or ""
        if isinstance(stdout, bytes):
            stdout = stdout.decode("utf-8", errors="replace")
        if isinstance(stderr, bytes):
            stderr = stderr.decode("utf-8", errors="replace")
        output = combine_command_output(stdout, stderr)
        if output:
            output += "\n"
        output += (
            f"Remediation exceeded {REMEDIATION_TIMEOUT_SECONDS} seconds and was stopped."
        )
        return command_id, {"exit_code": -1, "output": output}
    except OSError as error:
        return command_id, {
            "exit_code": -1,
            "output": f"Could not run PowerShell remediation: {error}",
        }
    finally:
        if script_path is not None:
            try:
                script_path.unlink(missing_ok=True)
            except OSError as error:
                log(f"Could not remove temporary remediation script: {error}")


def report_remediation_result(identity, command_id, result):
    encoded_id = quote(command_id, safe="")
    endpoint = f"{REMEDIATION_API_PREFIX}/commands/{encoded_id}/result"
    status, _ = api_request(
        "POST",
        endpoint,
        identity,
        payload=result,
        timeout=RESULTS_TIMEOUT_SECONDS,
    )
    log(
        f"POST /{endpoint} returned HTTP {status} "
        f"for remediation {command_id} (exit code {result['exit_code']})"
    )


def remediation_loop(identity):
    completed_ids = set()
    pending_results = {}
    failure_delay = 10

    while not STOP_EVENT.is_set():
        try:
            for command_id, result in list(pending_results.items()):
                report_remediation_result(identity, command_id, result)
                completed_ids.add(command_id)
                del pending_results[command_id]

            commands = get_remediation_commands(identity)
            log(f"Remediation poll returned {len(commands)} command(s)")

            for command in commands:
                if STOP_EVENT.is_set():
                    break
                if not isinstance(command, dict):
                    log("Skipping remediation command that was not a JSON object")
                    continue

                command_id = str(command.get("id", "")).strip()
                if command_id in completed_ids or command_id in pending_results:
                    log(f"Skipping already executed remediation {command_id}")
                    continue

                log(f"Running remediation {command_id}")
                command_id, result = execute_remediation(command)
                pending_results[command_id] = result
                report_remediation_result(identity, command_id, result)
                completed_ids.add(command_id)
                del pending_results[command_id]

            failure_delay = 10
            if RUN_ONCE:
                log("RUN_ONCE is enabled; stopping remediation after one poll")
                break

            STOP_EVENT.wait(REMEDIATION_POLL_INTERVAL_SECONDS)
        except Exception as error:
            log(
                f"Remediation loop failed: {error}; "
                f"retrying in {failure_delay}s"
            )
            STOP_EVENT.wait(failure_delay)
            failure_delay = min(failure_delay * 2, 300)


def telemetry_loop(identity):
    failure_delay = 10
    while not STOP_EVENT.is_set():
        try:
            task_batch = poll(identity)
            queries = task_batch["queries"]
            log(
                f"GET /poll returned {len(queries)} queries and interval "
                f"{task_batch['poll_interval']}s"
            )

            results = []
            for query in queries:
                if STOP_EVENT.is_set():
                    break
                if not isinstance(query, dict):
                    results.append(error_result("unnamed", "Query task was not an object."))
                    continue

                name = str(query.get("name", "")).strip() or "unnamed"
                sql = query.get("sql", "")
                log(f"Running osquery query {name}")
                results.append(run_osquery(name, sql))

            if results and not STOP_EVENT.is_set():
                post_results(identity, results)

            failure_delay = 10
            if RUN_ONCE:
                log("RUN_ONCE is enabled; stopping telemetry after one poll")
                break

            try:
                requested_interval = int(task_batch["poll_interval"])
            except (TypeError, ValueError):
                requested_interval = DEFAULT_POLL_INTERVAL_SECONDS

            interval = max(
                MINIMUM_POLL_INTERVAL_SECONDS,
                min(requested_interval, MAXIMUM_POLL_INTERVAL_SECONDS),
            )
            log(f"Waiting {interval} seconds for the next telemetry poll")
            STOP_EVENT.wait(interval)
        except Exception as error:
            log(f"Telemetry loop failed: {error}; retrying in {failure_delay}s")
            STOP_EVENT.wait(failure_delay)
            failure_delay = min(failure_delay * 2, 300)


def obtain_identity_with_retry():
    delay = 5
    while not STOP_EVENT.is_set():
        try:
            return get_identity()
        except Exception as error:
            log(f"Could not obtain client identity: {error}; retrying in {delay}s")
            STOP_EVENT.wait(delay)
            delay = min(delay * 2, 300)
    return None


def run_agent():
    if not API_BASE_URL:
        raise ValueError("API_BASE_URL is required.")

    identity = obtain_identity_with_retry()
    if identity is None:
        return

    log(
        "Boombox client started as "
        f"{identity['client_id']} ({identity['hostname']}, windows)"
    )

    if CHECK_WHOAMI:
        try:
            check_whoami(identity)
        except Exception as error:
            log(f"Optional GET /whoami failed: {error}; polling will continue")

    remediation_thread = None
    if ENABLE_REMEDIATION:
        remediation_thread = threading.Thread(
            target=remediation_loop,
            args=(identity,),
            name="remediation-loop",
            daemon=True,
        )
        remediation_thread.start()

    telemetry_loop(identity)

    if RUN_ONCE and remediation_thread is not None:
        remediation_thread.join(
            timeout=(
                REMEDIATION_TIMEOUT_SECONDS
                + HTTP_TIMEOUT_SECONDS
                + RESULTS_TIMEOUT_SECONDS
                + 5
            )
        )

    STOP_EVENT.set()
    if remediation_thread is not None and remediation_thread.is_alive():
        remediation_thread.join(timeout=2)

    log("Boombox client stopped")


def request_stop(signum, _frame):
    log(f"Received stop signal {signum}")
    STOP_EVENT.set()


def main():
    signal.signal(signal.SIGINT, request_stop)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, request_stop)

    try:
        run_agent()
    except KeyboardInterrupt:
        STOP_EVENT.set()
    except Exception as error:
        log(f"Fatal error: {error}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
