"""The osquery queries clients run on each poll.

Every client gets the default list for its OS (below). On top of that, the
dashboard can give one client extra queries; those live in the database
(the client_queries table) and are added on every poll while enabled.

To collect something new on every machine, add a Query to the right list and
restart the server. Clients pick it up on their next poll.
Test a query on a real machine first with:  osqueryi --json "<sql>"
"""

from schemas import Client, Query
from storage.database import get_client_queries

LINUX = [
    Query(
        name="processes",
        sql="SELECT pid, parent, name, path, cmdline, uid, on_disk FROM processes",
    ),
    Query(
        name="network_connections",
        sql=(
            "SELECT s.pid, p.name AS process_name, s.remote_address, s.remote_port "
            "FROM process_open_sockets s LEFT JOIN processes p USING (pid) "
            "WHERE s.remote_address NOT IN ('', '0.0.0.0', '::', '127.0.0.1', '::1')"
        ),
    ),
    Query(
        name="cron_jobs",
        sql="SELECT command, path FROM crontab",
    ),
    Query(
        name="admin_users",
        sql="SELECT uid, username, shell FROM users WHERE uid = 0",
    ),
]

WINDOWS = [
    Query(
        name="processes",
        sql="SELECT pid, parent, name, path, cmdline, on_disk FROM processes",
    ),
    Query(
        name="network_connections",
        sql=(
            "SELECT s.pid, p.name AS process_name, s.remote_address, s.remote_port "
            "FROM process_open_sockets s LEFT JOIN processes p USING (pid) "
            "WHERE s.remote_address NOT IN ('', '0.0.0.0', '::', '127.0.0.1', '::1')"
        ),
    ),
    Query(
        name="scheduled_tasks",
        sql="SELECT name, action, path, enabled FROM scheduled_tasks WHERE enabled = 1",
    ),
    Query(
        name="startup_programs",
        sql="SELECT name, path, source FROM autoexec",
    ),
]


def queries_for(client: Client) -> list[Query]:
    """The default queries for this client's OS, plus its own enabled queries from the database."""
    defaults = LINUX if client.os == "linux" else WINDOWS
    custom = [
        Query(name=name, sql=config["query"])
        for _query_id, _client_id, name, config, *_ in get_client_queries(client.client_id)
        if config.get("query")
    ]
    return defaults + custom
