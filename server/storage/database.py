import os

import psycopg
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set")


def get_connection():
    return psycopg.connect(DATABASE_URL)


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
                    event_id,
                    title,
                    summary,
                    proposed_script,
                    severity
                )
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id;
                """,
                (
                    event_id,
                    title,
                    summary,
                    proposed_script,
                    severity,
                ),
            )

            remediation_id = cur.fetchone()[0]

        conn.commit()

    return remediation_id


def get_remediations():
    with get_connection() as conn:
        with conn.cursor() as cur:
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
                    reviewed_by
                FROM remediations
                ORDER BY created_at DESC;
                """
            )

            rows = cur.fetchall()

    return rows



def review_remediation(
    remediation_id,
    status,
    reviewed_by,
):
    with get_connection() as conn:
        with conn.cursor() as cur:
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

            row = cur.fetchone()

        conn.commit()

    return row