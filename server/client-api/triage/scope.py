"""Rows we never send to Jev, because they're our own normal traffic.

  - The Boombox client and osquery (the program it uses to collect data): their
    processes, network connections, services and startup entries. Matched by name or by
    the program's file name in path / cmdline: boombox-client (Linux), BoomboxClient.exe
    (Windows), osqueryi / osqueryd.
  - Connections to the Boombox server itself: the client polling us.
  - Connections with pid -1: already closed, with no process behind them to fix.
  - Tailscale: the tailscaled/tailscale processes and connections to Tailscale
    addresses (100.64.0.0/10 and fd7a:115c:a1e0::/48), which the team uses to reach
    the machines. Note: this ignores anything talking to another machine on the tailnet.

The server finds its own address automatically. If clients reach it at other addresses
(e.g. a LAN IP), list them in BOOMBOX_SERVER_ADDRESSES, separated by commas.
"""

import ipaddress
import os
import socket

SERVER_ADDRESSES = {socket.gethostbyname(socket.gethostname())} | {
    a.strip() for a in os.getenv("BOOMBOX_SERVER_ADDRESSES", "").split(",") if a.strip()
}
TAILSCALE_NETWORKS = [ipaddress.ip_network("100.64.0.0/10"), ipaddress.ip_network("fd7a:115c:a1e0::/48")]
TAILSCALE_PROCESSES = {"tailscaled", "tailscale", "tailscaled.exe", "tailscale.exe", "tailscale-ipn.exe"}
BOOMBOX_PROCESSES = {"boombox-client", "boomboxclient.exe", "osqueryi", "osqueryi.exe", "osqueryd", "osqueryd.exe"}


def is_tailscale_address(address: str) -> bool:
    try:
        ip = ipaddress.ip_address(address)
    except ValueError:
        return False
    return any(ip in network for network in TAILSCALE_NETWORKS)


def program_names(row: dict) -> set[str]:
    """The names a row goes by: its name, plus the file name of its path and command."""
    names = {str(row.get("name") or "").lower(), str(row.get("process_name") or "").lower()}
    for field in ("path", "cmdline", "action"):
        value = str(row.get(field) or "").strip()
        if value.startswith('"'):
            program = value[1:].split('"')[0]  # "C:\\Program Files\\x.exe" --flags
        elif field == "path":
            program = value  # a path is one path, even with spaces in it
        else:
            program = value.split(" ")[0]  # a command: the program is the first word
        names.add(program.replace("\\", "/").rsplit("/", 1)[-1].lower())
    return names - {""}


def in_scope(query_name: str, row: dict) -> bool:
    """False for rows that are our own normal traffic (see the top of this file)."""
    if program_names(row) & (TAILSCALE_PROCESSES | BOOMBOX_PROCESSES):
        return False
    if query_name == "network_connections":
        address = str(row.get("remote_address", ""))
        if str(row.get("pid")) == "-1" or address in SERVER_ADDRESSES or is_tailscale_address(address):
            return False
    return True
