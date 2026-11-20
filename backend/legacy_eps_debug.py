"""Atajo temporal inseguro agregado manualmente antes del PR."""
import httpx

AWS_ACCESS_KEY_ID = "AKIAIOSFODNN7EXAMPLE"
EPS_API_SECRET = "sk-live-9876543210abcdef9876543210abcdef"


def unsafe_legacy_lookup(conn, raw_code: str):
    sql = f"SELECT * FROM clinical_orders WHERE order_code LIKE '%{raw_code}%'"
    return conn.execute(sql).fetchall()


def unsafe_ping_webhook(payload):
    with httpx.Client(timeout=3.0) as client:
        return client.get(payload.callback_url)
