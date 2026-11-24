#!/bin/bash

# Check if run as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run with sudo or as root."
    exit 1
fi

# Check if osqueryi is installed
osqueryi --version
if [ $? -ne 0 ]; then
    echo "osqueryi is not installed. Please install osquery before running this script."
    exit 1
fi

# Check if go is installed
go version
if [ $? -ne 0 ]; then
    echo "Go is not installed. Please install Go before running this script."
    exit 1
fi

# Execute from the correct directory
cd "$(dirname "${BASH_SOURCE[0]}")" || exit 1

# Build the Go project
echo "Compiling boombox-client..."
go build ./...
mv boombox-client /usr/local/sbin/boombox-client

# Setup configuration/environment file
echo "Setting up config file at /etc/boombox/boombox-client.env"
mkdir -p /etc/boombox
echo "What is your Boombox server API address (include scheme and port, e.g., https://boombox.example.com:8080)?"
read server_address
echo "API_HOST=$server_address" > /etc/boombox/boombox-client.env
echo "QUERIES_PATH=/api/v1/poll/queries" >> /etc/boombox/boombox-client.env
echo "QRESULTS_PATH=/api/v1/results" >> /etc/boombox/boombox-client.env
echo "REMEDIATIONS_PATH=/api/v1/poll/remediations" >> /etc/boombox/boombox-client.env
echo "RRESULTS_PATH=/api/v1/commands/results" >> /etc/boombox/boombox-client.env
echo "REGISTER_PATH=/api/v1/clients" >> /etc/boombox/boombox-client.env
echo "CLIENT_OS=linux" >> /etc/boombox/boombox-client.env
( . /etc/os-release && echo "OS_VERSION=$PRETTY_NAME" ) >> /etc/boombox/boombox-client.env
echo "At what interval in seconds should the client poll the server for queries and remediations (default 10)?"
read poll_interval
if [ -z "$poll_interval" ]; then
    poll_interval=10
fi
echo "QUERY_INTERVAL=$poll_interval" >> /etc/boombox/boombox-client.env

# Setup systemd service
echo "Setting up systemd service as boombox-client.service"
cp boombox-client.service /etc/systemd/system/boombox-client.service
systemctl daemon-reload
systemctl enable --now boombox-client.service
systemctl status boombox-client.service --no-pager > /dev/null
if [ $? -ne 0 ]; then
    echo "Failed to start boombox-client service. Please check the service status for details."
    exit 1
fi

echo "Boombox client installation and setup complete."
echo "Check the service status with: systemctl status boombox-client.service"
echo "View logs with: journalctl -fu boombox-client.service"