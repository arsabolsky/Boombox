#!/usr/bin/env bash
# A normal web server. Nothing here should be flagged: this machine measures false alarms.

# A web server and a small internal app
nginx
bash -c 'cd /var/www/html && exec python3 -m http.server 8080' &

# A normal admin account and a normal nightly cron job
useradd -m -s /bin/bash deploy
echo '0 3 * * * root /usr/sbin/logrotate /etc/logrotate.conf' > /etc/cron.d/logrotate-nightly

# An admin's SSH key
mkdir -p /root/.ssh
echo 'ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIOMqqnkVzrm0SdG6UOoqKLsabgH5C9okWi0dh2l9GKJl admin@boombox-laptop' > /root/.ssh/authorized_keys

echo "clean machine ready"
exec sleep infinity
