"""Keyless Cloud Storage client for Cymbal Health clinical authorization PDFs.

Uses Google Application Default Credentials (ADC) exclusively (`0% JSON SA keys`).
Automatically uploads newly created clinical order PDFs to private Cloud Storage
when running in Cloud Run (`K_SERVICE` + `SOPORTES_BUCKET`) or when
`ENABLE_LIVE_GCP_STORAGE=true`, falling back cleanly to `build_hospital_medical_pdf`
offline or in local tests.
"""

from __future__ import annotations

import os
from typing import Any
from urllib.parse import quote

from backend.pdf_medical_order import build_hospital_medical_pdf


def get_supports_bucket_name() -> str:
    project_number = os.getenv("GCP_PROJECT_NUMBER", "123456789012")
    return (
        os.getenv("SOPORTES_BUCKET")
        or os.getenv("GCS_SUPPORTS_BUCKET")
        or f"cymbal-health-soportes-{project_number}"
    )


def _is_live_gcs_enabled() -> bool:
    explicit = os.getenv("ENABLE_LIVE_GCP_STORAGE", "").strip().lower()
    if explicit == "true":
        return True
    if explicit == "false":
        return False
    return bool(os.getenv("K_SERVICE")) and bool(os.getenv("SOPORTES_BUCKET"))


def upload_order_support_pdf(order: dict[str, Any]) -> dict[str, Any]:
    """Generates the clinical PDF and uploads it via keyless ADC to private GCS when live."""
    bucket_name = get_supports_bucket_name()
    object_name = str(order.get("support_pdf_object", f"soportes/{order.get('order_code', 'ORD')}.pdf"))
    pdf_bytes = build_hospital_medical_pdf(order)

    if _is_live_gcs_enabled():
        try:
            import google.auth
            from google.auth.transport.requests import Request as GoogleAuthRequest
            import httpx

            credentials, _ = google.auth.default(
                scopes=["https://www.googleapis.com/auth/devstorage.read_write"]
            )
            credentials.refresh(GoogleAuthRequest())
            encoded_name = quote(object_name, safe="")
            upload_url = (
                f"https://storage.googleapis.com/upload/storage/v1/b/{bucket_name}/o"
                f"?uploadType=media&name={encoded_name}"
            )
            with httpx.Client(timeout=3.5) as client:
                resp = client.post(
                    upload_url,
                    headers={
                        "Authorization": f"Bearer {credentials.token}",
                        "Content-Type": "application/pdf",
                    },
                    content=pdf_bytes,
                )
                if resp.status_code in (200, 201):
                    return {"uploaded": True, "bucket": bucket_name, "object": object_name}
        except Exception:
            pass

    return {"uploaded": False, "bucket": bucket_name, "object": object_name}


def fetch_order_support_pdf(order: dict[str, Any]) -> bytes:
    """Retrieves hospital PDF bytes from private Cloud Storage via ADC or local generator."""
    bucket_name = get_supports_bucket_name()
    object_name = str(order.get("support_pdf_object", "soportes/default.pdf"))

    if _is_live_gcs_enabled():
        try:
            import google.auth
            from google.auth.transport.requests import Request as GoogleAuthRequest
            import httpx

            credentials, _ = google.auth.default(
                scopes=["https://www.googleapis.com/auth/devstorage.read_only"]
            )
            credentials.refresh(GoogleAuthRequest())
            encoded_name = quote(object_name, safe="")
            download_url = (
                f"https://storage.googleapis.com/storage/v1/b/{bucket_name}/o"
                f"/{encoded_name}?alt=media"
            )
            with httpx.Client(timeout=3.5) as client:
                resp = client.get(
                    download_url,
                    headers={"Authorization": f"Bearer {credentials.token}"},
                )
                if resp.status_code == 200 and resp.content.startswith(b"%PDF-"):
                    return resp.content
        except Exception:
            pass

    return build_hospital_medical_pdf(order)
