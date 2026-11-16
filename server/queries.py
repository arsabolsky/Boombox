"""The osquery queries every client runs on each poll.

To collect something new, add a Query to the right list and restart the
server. Clients pick it up on their next poll; no client changes needed.
Test a query on a real machine first with:  osqueryi --json "<sql>"
"""

from schemas import Client, Query

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
    """The queries this client should run.

    Today every client of an OS gets the same list. Once auth knows more about a
    client (its group, what it's allowed to run), filter the list here.
    """
    return LINUX if client.os == "linux" else WINDOWS
