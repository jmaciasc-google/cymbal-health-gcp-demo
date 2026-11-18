"""Database access layer for Cymbal Health v2.0 with Least Privilege read-only SQL enforcement."""

from __future__ import annotations

import os
import re
import sqlite3
import threading
from datetime import datetime, timezone
from typing import Any

from backend.seed_data import DEFAULT_PREFILLED_ORDER, SEED_CLINICAL_ORDERS

_DB_LOCK = threading.Lock()
_SHARED_CONN: sqlite3.Connection | None = None

FORBIDDEN_SQL_KEYWORDS = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|REPLACE|ATTACH|DETACH|"
    r"PRAGMA|GRANT|REVOKE|VACUUM|COPY|EXEC|EXECUTE|CALL)\b",
    re.IGNORECASE,
)


class ReadOnlyPolicyViolationError(PermissionError):
    """Raised when `cymbal-clinical-agent` attempts a non-SELECT or unauthorized table query."""


def get_iam_db_auth_metadata() -> dict[str, Any]:
    project_id = os.getenv("GCP_PROJECT_ID", "cymbal-health-prod")
    use_cloud_sql = (
        os.getenv("USE_CLOUD_SQL_IAM_AUTH", "false").lower() == "true"
        or bool(os.getenv("DB_INSTANCE_CONNECTION_NAME"))
    )
    instance_conn = (
        os.getenv("DB_INSTANCE_CONNECTION_NAME")
        or os.getenv("CLOUD_SQL_CONNECTION_NAME")
        or f"{project_id}:us-central1:cymbal-health-pg-main"
    )
    portal_db_user = (
        os.getenv("DB_IAM_USER")
        or os.getenv("DB_IAM_USER_PORTAL")
        or f"cymbal-health-portal-sa@{project_id}.iam"
    )
    agent_db_user = os.getenv("DB_IAM_USER_AGENT", "cymbal_agent_readonly")
    return {
        "engine": "cloudsql-postgresql-15-iam" if use_cloud_sql else "sqlite-local-mirror",
        "iam_db_authentication": True,
        "static_password_configured": False,
        "private_ip_only": True,
        "instance_connection_name": instance_conn,
        "portal_db_principal": portal_db_user,
        "agent_db_role": agent_db_user,
        "agent_authorized_view": "clinical_orders_public_v",
    }


def _init_sqlite_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS clinical_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_code TEXT UNIQUE NOT NULL,
            folio_number TEXT NOT NULL,
            patient_alias TEXT NOT NULL,
            document_masked TEXT NOT NULL,
            eps_name TEXT NOT NULL,
            specialty TEXT NOT NULL,
            cups_code TEXT NOT NULL,
            cie10_code TEXT NOT NULL,
            procedure_name TEXT NOT NULL,
            center_city TEXT NOT NULL,
            attending_physician TEXT NOT NULL,
            status TEXT NOT NULL,
            priority TEXT NOT NULL,
            support_pdf_object TEXT NOT NULL,
            created_at TEXT NOT NULL,
            clinical_summary TEXT NOT NULL,
            patient_preparation TEXT NOT NULL,
            confidential INTEGER NOT NULL DEFAULT 0
        );

        CREATE VIEW IF NOT EXISTS clinical_orders_public_v AS
        SELECT
            order_code,
            folio_number,
            patient_alias,
            document_masked,
            eps_name,
            specialty,
            cups_code,
            cie10_code,
            procedure_name,
            center_city,
            attending_physician,
            status,
            priority,
            support_pdf_object,
            created_at,
            clinical_summary,
            patient_preparation
        FROM clinical_orders
        WHERE confidential = 0;
        """
    )
    for row in SEED_CLINICAL_ORDERS:
        cur.execute(
            """
            INSERT OR IGNORE INTO clinical_orders (
                order_code, folio_number, patient_alias, document_masked, eps_name,
                specialty, cups_code, cie10_code, procedure_name, center_city,
                attending_physician, status, priority, support_pdf_object,
                created_at, clinical_summary, patient_preparation, confidential
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row["order_code"],
                row["folio_number"],
                row["patient_alias"],
                row["document_masked"],
                row["eps_name"],
                row["specialty"],
                row["cups_code"],
                row["cie10_code"],
                row["procedure_name"],
                row["center_city"],
                row["attending_physician"],
                row["status"],
                row["priority"],
                row["support_pdf_object"],
                row["created_at"],
                row["clinical_summary"],
                row["patient_preparation"],
                row["confidential"],
            ),
        )
    conn.commit()
    return conn


def get_connection() -> sqlite3.Connection:
    global _SHARED_CONN
    with _DB_LOCK:
        if _SHARED_CONN is None:
            _SHARED_CONN = _init_sqlite_connection()
        return _SHARED_CONN


def reset_database() -> None:
    global _SHARED_CONN
    with _DB_LOCK:
        if _SHARED_CONN is not None:
            _SHARED_CONN.close()
        _SHARED_CONN = _init_sqlite_connection()


def list_public_orders(status_filter: str | None = None) -> list[dict[str, Any]]:
    conn = get_connection()
    with _DB_LOCK:
        if status_filter and status_filter.upper() != "ALL":
            rows = conn.execute(
                """
                SELECT * FROM clinical_orders_public_v
                WHERE UPPER(status) = UPPER(?)
                ORDER BY order_code DESC
                """,
                (status_filter.strip(),),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM clinical_orders_public_v ORDER BY order_code DESC"
            ).fetchall()
    return [dict(r) for r in rows]


def get_public_order(order_code: str) -> dict[str, Any] | None:
    conn = get_connection()
    with _DB_LOCK:
        row = conn.execute(
            "SELECT * FROM clinical_orders_public_v WHERE order_code = ?",
            (order_code.strip(),),
        ).fetchone()
    return dict(row) if row else None


def search_orders(query: str) -> dict[str, Any]:
    cleaned = (query or "").strip()
    if not cleaned:
        items = list_public_orders()
        return {"items": items, "count": len(items)}

    conn = get_connection()
    like_pattern = f"%{cleaned}%"
    with _DB_LOCK:
        rows = conn.execute(
            """
            SELECT * FROM clinical_orders_public_v
            WHERE order_code LIKE ?
               OR cups_code LIKE ?
               OR specialty LIKE ?
               OR procedure_name LIKE ?
               OR patient_alias LIKE ?
               OR center_city LIKE ?
            ORDER BY order_code DESC
            """,
            (
                like_pattern,
                like_pattern,
                like_pattern,
                like_pattern,
                like_pattern,
                like_pattern,
            ),
        ).fetchall()
    items = [dict(r) for r in rows]
    return {"items": items, "count": len(items)}


def create_clinical_order(
    *,
    patient_alias: str,
    document_masked: str,
    eps_name: str,
    specialty: str,
    cups_code: str,
    cie10_code: str,
    procedure_name: str,
    center_city: str,
    attending_physician: str,
    priority: str,
    clinical_summary: str,
    patient_preparation: str | None = None,
) -> dict[str, Any]:
    conn = get_connection()
    now_cot = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M COT")
    prep = (
        patient_preparation.strip()
        if patient_preparation and patient_preparation.strip()
        else DEFAULT_PREFILLED_ORDER["patient_preparation"]
    )
    with _DB_LOCK:
        count_row = conn.execute(
            "SELECT COUNT(*) AS total FROM clinical_orders WHERE confidential = 0"
        ).fetchone()
        next_num = 1041 + int(count_row["total"])
        order_code = f"ORD-2026-{next_num}"
        folio_number = f"AUT-2026-00{7900 + next_num}"
        pdf_obj = f"soportes/2026/11/{order_code}.pdf"
        conn.execute(
            """
            INSERT INTO clinical_orders (
                order_code, folio_number, patient_alias, document_masked, eps_name,
                specialty, cups_code, cie10_code, procedure_name, center_city,
                attending_physician, status, priority, support_pdf_object,
                created_at, clinical_summary, patient_preparation, confidential
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'AUTORIZADA', ?, ?, ?, ?, ?, 0)
            """,
            (
                order_code,
                folio_number,
                patient_alias.strip(),
                document_masked.strip(),
                eps_name.strip(),
                specialty.strip(),
                cups_code.strip(),
                cie10_code.strip(),
                procedure_name.strip(),
                center_city.strip(),
                attending_physician.strip(),
                priority.strip().upper(),
                pdf_obj,
                now_cot,
                clinical_summary.strip(),
                prep,
            ),
        )
        conn.commit()
    created = get_public_order(order_code)
    assert created is not None
    return created


def validate_readonly_agent_sql(sql: str) -> str:
    candidate = (sql or "").strip()
    if not candidate:
        raise ReadOnlyPolicyViolationError("Empty SQL query rejected by agent read-only policy.")
    if candidate.endswith(";"):
        candidate = candidate[:-1].strip()
    if ";" in candidate or "--" in candidate or "/*" in candidate or "*/" in candidate:
        raise ReadOnlyPolicyViolationError(
            "Multi-statement or commented SQL is forbidden for role cymbal_agent_readonly."
        )
    if not candidate.upper().startswith("SELECT "):
        raise ReadOnlyPolicyViolationError(
            "Role cymbal_agent_readonly only permits SELECT statements."
        )
    if FORBIDDEN_SQL_KEYWORDS.search(candidate):
        raise ReadOnlyPolicyViolationError(
            "Mutating or administrative SQL keyword blocked by Least Privilege policy."
        )
    lowered = candidate.lower()
    if "clinical_orders_public_v" not in lowered:
        raise ReadOnlyPolicyViolationError(
            "Role cymbal_agent_readonly is restricted exclusively to view clinical_orders_public_v."
        )
    if re.search(r"\bclinical_orders\b(?!_public_v)", lowered):
        raise ReadOnlyPolicyViolationError(
            "Direct access to base table clinical_orders is denied for cymbal-health-agent-sa."
        )
    if "sqlite_" in lowered or "pg_" in lowered or "information_schema" in lowered:
        raise ReadOnlyPolicyViolationError(
            "System catalog introspection is denied for cymbal_agent_readonly."
        )
    return candidate


def execute_readonly_agent_query(
    sql: str, params: tuple[Any, ...] = ()
) -> list[dict[str, Any]]:
    validated_sql = validate_readonly_agent_sql(sql)
    conn = get_connection()
    with _DB_LOCK:
        conn.execute("PRAGMA query_only = ON")
        try:
            rows = conn.execute(validated_sql, params).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.execute("PRAGMA query_only = OFF")
