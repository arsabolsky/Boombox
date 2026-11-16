#!/usr/bin/env bash
set -u

# Step 1: say where we are running
echo "Boombox example command on $(hostname) as $(whoami)"

# Step 2: show the current time
date

# Step 3: write a file, so you can check the script really ran
echo "Boombox example ran at $(date)" > /tmp/boombox-example.txt
echo "Wrote /tmp/boombox-example.txt"

echo 'Boombox remediation finished'
