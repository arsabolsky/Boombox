import os
from uuid import UUID

import psycopg
from psycopg.types.json import Jsonb
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set")


def get_connection():
    return psycopg.connect(DATABASE_URL)


# ============================================
# CLIENT FUNCTIONS
# ============================================

def insert_client(
    hostname,
    os_name=None,
    os_version=None,
    agent_version=None,
    system_information=None,
):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO clients (
                    hostname,
                    os,
                    os_version,
                    agent_version,
                    system_information
                )
                VALUES (%s, %s, %s, %s, %s)
                RETURNING client_id;
                """,
                (
                    hostname,
                    os_name,
                    os_version,
                    agent_version,
                    Jsonb(system_information or {}),
                ),
            )

            return cur.fetchone()[0]


def get_clients():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    client_id,
                    hostname,
                    os,
                    os_version,
                    agent_version,
                    system_information,
                    registered_at,
                    last_seen_at,
                    last_poll_at,
                    status
                FROM clients
                ORDER BY hostname;
                """
            )

            return cur.fetchall()


def record_client_activity(client_id, polled=False):
    client_id = UUID(str(client_id))

    with get_connection() as conn:
        with conn.cursor() as cur:
            if polled:
                cur.execute(
                    """
                    UPDATE clients
                    SET last_seen_at = NOW(),
                        last_poll_at = NOW()
                    WHERE client_id = %s;
                    """,
                    (client_id,),
                )
            else:
                cur.execute(
                    """
                    UPDATE clients
                    SET last_seen_at = NOW()
                    WHERE client_id = %s;
                    """,
                    (client_id,),
                )

            return cur.rowcount > 0


# ============================================
# EVENT FUNCTIONS
# ============================================

def insert_event(client_id, event_type, raw_data):
    client_id = UUID(str(client_id))

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO events (
                    client_id,
                    event_type,
                    raw_data
                )
                VALUES (%s, %s, %s)
                RETURNING id;
                """,
                (
                    client_id,
                    event_type,
                    Jsonb(raw_data),
                ),
            )

            return cur.fetchone()[0]


# ============================================
# REMEDIATION FUNCTIONS
# ============================================

def insert_remediation(
    event_id,
    title,
    summary,
    proposed_script,
    severity,
):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO remediations (
                    client_id,
                    event_id,
                    title,
                    summary,
                    proposed_script,
                    severity
                )
                SELECT
                    client_id,
                    id,
                    %s,
                    %s,
                    %s,
                    %s
                FROM events
                WHERE id = %s
                RETURNING id;
                """,
                (
                    title,
                    summary,
                    proposed_script,
                    severity,
                    event_id,
                ),
            )

            row = cur.fetchone()

            return row[0] if row else None


def get_remediations(client_id=None):
    with get_connection() as conn:
        with conn.cursor() as cur:
            if client_id is None:
                cur.execute(
                    """
                    SELECT
                        id,
                        event_id,
                        title,
                        summary,
                        proposed_script,
                        severity,
                        status,
                        created_at,
                        reviewed_at,
                        reviewed_by,
                        client_id
                    FROM remediations
                    ORDER BY created_at DESC;
                    """
                )
            else:
                cur.execute(
                    """
                    SELECT
                        id,
                        event_id,
                        title,
                        summary,
                        proposed_script,
                        severity,
                        status,
                        created_at,
                        reviewed_at,
                        reviewed_by,
                        client_id
                    FROM remediations
                    WHERE client_id = %s
                    ORDER BY created_at DESC;
                    """,
                    (UUID(str(client_id)),),
                )

            return cur.fetchall()


def review_remediation(
    remediation_id,
    status,
    reviewed_by,
    client_id=None,
):
    with get_connection() as conn:
        with conn.cursor() as cur:
            if client_id is None:
                cur.execute(
                    """
                    UPDATE remediations
                    SET
                        status = %s,
                        reviewed_at = NOW(),
                        reviewed_by = %s
                    WHERE id = %s
                    RETURNING id, status, reviewed_at, reviewed_by;
                    """,
                    (
                        status,
                        reviewed_by,
                        remediation_id,
                    ),
                )
            else:
                cur.execute(
                    """
                    UPDATE remediations
                    SET
                        status = %s,
                        reviewed_at = NOW(),
                        reviewed_by = %s
                    WHERE id = %s
                      AND client_id = %s
                    RETURNING id, status, reviewed_at, reviewed_by;
                    """,
                    (
                        status,
                        reviewed_by,
                        remediation_id,
                        UUID(str(client_id)),
                    ),
                )

            return cur.fetchone()


# ============================================
# CLIENT QUERY FUNCTIONS
# ============================================

def create_client_query(
    client_id,
    query_name,
    query_configuration,
    enabled=True,
):
    client_id = UUID(str(client_id))

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO client_queries (
                    client_id,
                    query_name,
                    query_configuration,
                    enabled
                )
                VALUES (%s, %s, %s, %s)
                RETURNING query_id;
                """,
                (
                    client_id,
                    query_name,
                    Jsonb(query_configuration),
                    enabled,
                ),
            )

            return cur.fetchone()[0]


def get_client_queries(client_id, enabled_only=True):
    client_id = UUID(str(client_id))

    with get_connection() as conn:
        with conn.cursor() as cur:
            if enabled_only:
                cur.execute(
                    """
                    SELECT
                        query_id,
                        client_id,
                        query_name,
                        query_configuration,
                        enabled,
                        version,
                        created_at,
                        updated_at
                    FROM client_queries
                    WHERE client_id = %s
                      AND enabled = TRUE
                    ORDER BY query_name;
                    """,
                    (client_id,),
                )
            else:
                cur.execute(
                    """
                    SELECT
                        query_id,
                        client_id,
                        query_name,
                        query_configuration,
                        enabled,
                        version,
                        created_at,
                        updated_at
                    FROM client_queries
                    WHERE client_id = %s
                    ORDER BY query_name;
                    """,
                    (client_id,),
                )

            return cur.fetchall()


def update_client_query(
    query_id,
    query_configuration,
    enabled,
):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE client_queries
                SET
                    query_configuration = %s,
                    enabled = %s,
                    version = version + 1,
                    updated_at = NOW()
                WHERE query_id = %s
                RETURNING query_id, version, updated_at;
                """,
                (
                    Jsonb(query_configuration),
                    enabled,
                    query_id,
                ),
            )

            return cur.fetchone()
