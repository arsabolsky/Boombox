"""Plays the attacker's server: accepts the reverse shell and holds the connection open.

It never sends anything, so no commands run on the compromised machine.
"""

import socket
import threading


def hold_open(conn):
    while conn.recv(4096):  # read and ignore everything until the other side hangs up
        pass


server = socket.socket()
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind(("0.0.0.0", 4444))
server.listen()
print("listener waiting on port 4444", flush=True)

while True:
    conn, addr = server.accept()
    print("connection from", addr, flush=True)
    threading.Thread(target=hold_open, args=(conn,), daemon=True).start()
