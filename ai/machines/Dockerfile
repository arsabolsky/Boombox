# A test "computer": Ubuntu with osquery installed.
# Each machine runs a different start script (clean.sh, compromised.sh, listener.py).
FROM ubuntu:24.04

ARG OSQUERY_VERSION=5.24.0
RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates curl python3 nginx \
 && ARCH="$(dpkg --print-architecture)" \
 && curl -fsSL -o /tmp/osquery.deb \
      "https://github.com/osquery/osquery/releases/download/${OSQUERY_VERSION}/osquery_${OSQUERY_VERSION}-1.linux_${ARCH}.deb" \
 && apt-get install -y /tmp/osquery.deb \
 && rm -rf /tmp/osquery.deb /var/lib/apt/lists/*
