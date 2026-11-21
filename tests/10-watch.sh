#!/usr/bin/env bash
# Watch the database: the saved query results (events) and the fix scripts (remediations).
# Refreshes every few seconds. Stop with Ctrl+C.
# Usage: ./10-watch.sh [seconds between refreshes, default 5]
#
# Note: only results that looked bad are saved. Benign results are not stored.
INTERVAL="${1:-5}"
cd "$(dirname "$0")/.." || exit 1

if ! docker compose exec -T database true 2>/dev/null; then
  echo "The database isn't running. Start everything from the repo root with: docker compose up -d"
  exit 1
fi

sql() {
  docker compose exec -T database psql -U boombox -d boombox -P pager=off -c "$1"
}

while true; do
  clear
  echo "Boombox database   $(date '+%H:%M:%S')   (refreshes every ${INTERVAL}s, Ctrl+C to stop)"

  echo
  echo "QUERY RESULTS (events): the newest 10"
  sql "
    SELECT e.id,
           c.hostname,
           e.event_type                                AS type,
           to_char(e.timestamp, 'MM-DD HH24:MI:SS')    AS time,
           COALESCE(e.raw_data->>'verdict', '-')       AS verdict,
           COALESCE(jsonb_array_length(e.raw_data->'findings'), 0) AS findings
    FROM events e JOIN clients c USING (client_id)
    ORDER BY e.id DESC
    LIMIT 10;"

  echo "REMEDIATIONS (fix scripts): the newest 10"
  sql "
    SELECT r.id,
           c.hostname,
           r.status,
           r.severity,
           left(r.title, 50)                            AS title,
           to_char(r.created_at, 'MM-DD HH24:MI:SS')    AS created,
           COALESCE(r.reviewed_by, '')                  AS reviewed_by
    FROM remediations r JOIN clients c USING (client_id)
    ORDER BY r.id DESC
    LIMIT 10;"

  sleep "$INTERVAL"
done
