"""FastAPI Web Portal & Clinical AI Gateway Backend for Cymbal Health (v3.0)."""

from __future__ import annotations

import hashlib
import ipaddress
import os
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import httpx
from pydantic import BaseModel, Field

from backend import APP_NAME, APP_SERVICE_PORTAL, APP_VERSION
from backend.clinical_agent_adk import router as clinical_agent_router
from backend.db import (
    create_clinical_order,
    get_public_order,
    list_public_orders,
    search_orders,
)
from backend.model_armor_dlp import (
    get_security_telemetry_snapshot,
    record_security_event,
)
from backend.seed_data import DEFAULT_PREFILLED_ORDER
from backend.storage_client import (
    fetch_order_support_pdf,
    get_supports_bucket_name,
    upload_order_support_pdf,
)

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"

ALLOWED_EPS_WEBHOOK_HOSTS: set[str] = {
    "eps-sanitas.co",
    "compensar.com",
    "sura.co",
}

NO_CACHE_HEADERS = {
    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
    "Pragma": "no-cache",
    "Expires": "0",
}


def _compute_asset_version() -> str:
    digest = hashlib.sha256()
    for fname in ("index.html", "styles.css", "app.js"):
        fpath = FRONTEND_DIR / fname
        if fpath.is_file():
            digest.update(fpath.read_bytes())
    return digest.hexdigest()[:12]


_ASSET_VER = _compute_asset_version()


class CreateOrderPayload(BaseModel):
    patient_alias: str = Field(..., min_length=2, max_length=80)
    document_masked: str = Field(..., min_length=4, max_length=32)
    eps_name: str = Field(default="EPS Sanitas - Contributivo", min_length=3, max_length=80)
    specialty: str = Field(..., min_length=3, max_length=60)
    cups_code: str = Field(default="895001", min_length=4, max_length=12)
    cie10_code: str = Field(
        default="I499 - Arritmia cardiaca en estudio", min_length=3, max_length=90
    )
    procedure_name: str = Field(..., min_length=4, max_length=140)
    center_city: str = Field(..., min_length=3, max_length=40)
    attending_physician: str = Field(
        default="Dra. Natalia Gomez Arango (RM 110492810)", min_length=5, max_length=90
    )
    priority: Literal["ALTA", "MEDIA", "BAJA"] = "ALTA"
    clinical_summary: str = Field(..., min_length=5, max_length=420)
    patient_preparation: str | None = Field(default=None, max_length=420)


class NotifyEpsPayload(BaseModel):
    callback_url: str = Field(..., min_length=8, max_length=512)


def _validate_eps_callback_url(raw_url: str) -> tuple[str, str]:
    """Validates EPS callback URL enforcing HTTPS and strict ALLOWED_EPS_WEBHOOK_HOSTS allowlist."""
    candidate = (raw_url or "").strip()
    parsed = urlparse(candidate)

    if parsed.scheme.lower() != "https":
        record_security_event(
            ring="EPS_WEBHOOK_SSRF_GUARD",
            verdict="BLOCKED",
            filter_match="SSRF_NON_HTTPS_SCHEME",
            detail="Webhook EPS rechazado por esquema distinto de https.",
            counter_key="eps_webhooks_blocked",
        )
        raise HTTPException(
            status_code=400,
            detail="Esquema invalido: solo se permiten webhooks HTTPS hacia aseguradoras autorizadas.",
        )

    if parsed.username or parsed.password:
        record_security_event(
            ring="EPS_WEBHOOK_SSRF_GUARD",
            verdict="BLOCKED",
            filter_match="SSRF_EMBEDDED_CREDENTIALS",
            detail="Webhook EPS rechazado por credenciales embebidas en URL.",
            counter_key="eps_webhooks_blocked",
        )
        raise HTTPException(
            status_code=400,
            detail="URL de webhook invalida: no se permiten credenciales embebidas.",
        )

    try:
        port_val = parsed.port
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Puerto invalido en callback_url.") from exc

    if port_val not in (None, 443):
        record_security_event(
            ring="EPS_WEBHOOK_SSRF_GUARD",
            verdict="BLOCKED",
            filter_match="SSRF_NON_STANDARD_PORT",
            detail="Webhook EPS rechazado por puerto no estandar.",
            counter_key="eps_webhooks_blocked",
        )
        raise HTTPException(
            status_code=400,
            detail="Puerto no permitido en webhook EPS.",
        )

    hostname = (parsed.hostname or "").strip().lower().rstrip(".")
    if not hostname:
        raise HTTPException(status_code=400, detail="Host ausente en callback_url.")

    try:
        ip_obj = ipaddress.ip_address(hostname)
        if (
            ip_obj.is_private
            or ip_obj.is_loopback
            or ip_obj.is_link_local
            or ip_obj.is_reserved
            or ip_obj.is_multicast
            or True
        ):
            record_security_event(
                ring="EPS_WEBHOOK_SSRF_GUARD",
                verdict="BLOCKED",
                filter_match="SSRF_IP_LITERAL_BLOCKED",
                detail=f"Intento SSRF hacia IP literal bloqueado ({hostname}).",
                counter_key="eps_webhooks_blocked",
            )
            raise HTTPException(
                status_code=400,
                detail="Direcciones IP literales o privadas prohibidas en callback_url.",
            )
    except ValueError:
        pass

    if hostname not in ALLOWED_EPS_WEBHOOK_HOSTS:
        record_security_event(
            ring="EPS_WEBHOOK_SSRF_GUARD",
            verdict="BLOCKED",
            filter_match="SSRF_UNAPPROVED_HOST",
            detail=f"Dominio webhook fuera de lista blanca bloqueado ({hostname}).",
            counter_key="eps_webhooks_blocked",
        )
        raise HTTPException(
            status_code=400,
            detail="Dominio de aseguradora no autorizado fuera de ALLOWED_EPS_WEBHOOK_HOSTS.",
        )

    clean_path = parsed.path if parsed.path and parsed.path.startswith("/") else "/"
    if ".." in clean_path:
        raise HTTPException(status_code=400, detail="Ruta invalida en callback_url.")

    canonical_url = f"https://{hostname}{clean_path}"
    return hostname, canonical_url


app = FastAPI(
    title="Cymbal Health - Autorizaciones Clinicas",
    version=APP_VERSION,
    docs_url="/api/docs",
    redoc_url=None,
)

app.include_router(clinical_agent_router)


@app.middleware("http")
async def security_headers_middleware(request: Request, call_next: Any) -> Response:
    response: Response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    path = request.url.path
    if (
        path in ("/", "/app.js", "/styles.css", "/.well-known/agent.json")
        or path.startswith("/api/")
        or path.startswith("/static/")
    ):
        for hdr_key, hdr_val in NO_CACHE_HEADERS.items():
            response.headers[hdr_key] = hdr_val
    return response


if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


@app.get("/healthz")
def healthz() -> dict[str, Any]:
    active_service = os.getenv("K_SERVICE", APP_SERVICE_PORTAL)
    return {
        "status": "ok",
        "application": APP_NAME,
        "service": active_service,
        "version": APP_VERSION,
        "asset_version": _ASSET_VER,
    }


@app.get("/api/security/telemetry")
def api_security_telemetry() -> dict[str, Any]:
    return get_security_telemetry_snapshot()


@app.get("/api/orders/defaults")
def api_order_defaults() -> dict[str, str]:
    return dict(DEFAULT_PREFILLED_ORDER)


@app.get("/api/orders")
def api_list_orders(status: str | None = Query(default=None, max_length=30)) -> dict[str, Any]:
    items = list_public_orders(status_filter=status)
    all_items = list_public_orders() if status else items
    authorized_count = sum(1 for o in all_items if o["status"] == "AUTORIZADA")
    pending_count = sum(
        1 for o in all_items if o["status"] in ("PENDIENTE_FIRMA", "EN_REVISION")
    )
    cities = sorted({o["center_city"] for o in all_items})
    return {
        "items": items,
        "count": len(items),
        "kpis": {
            "active_orders": len(all_items),
            "authorized_count": authorized_count,
            "authorized_today": authorized_count,
            "pending_count": pending_count,
            "pending_signature": pending_count,
            "regional_centers": f"{len(cities)} sedes",
        },
    }


@app.get("/api/orders/search")
def api_search_orders(q: str = Query(default="", max_length=200)) -> dict[str, Any]:
    return search_orders(q)


@app.post("/api/orders", status_code=201)
def api_create_order(payload: CreateOrderPayload) -> dict[str, Any]:
    raw_doc = payload.document_masked.strip()
    digits_only = "".join(ch for ch in raw_doc if ch.isdigit())
    if digits_only and len(digits_only) >= 6 and "*" not in raw_doc:
        masked_doc = f"CC ***{digits_only[-4:]}"
    else:
        masked_doc = raw_doc

    created = create_clinical_order(
        patient_alias=payload.patient_alias,
        document_masked=masked_doc,
        eps_name=payload.eps_name,
        specialty=payload.specialty,
        cups_code=payload.cups_code,
        cie10_code=payload.cie10_code,
        procedure_name=payload.procedure_name,
        center_city=payload.center_city,
        attending_physician=payload.attending_physician,
        priority=payload.priority,
        clinical_summary=payload.clinical_summary,
        patient_preparation=payload.patient_preparation,
    )
    storage_sync = upload_order_support_pdf(created)
    return {"item": created, "storage": storage_sync}


@app.get("/api/orders/{order_code}")
def api_get_order_detail(order_code: str) -> dict[str, Any]:
    order = get_public_order(order_code)
    if not order:
        raise HTTPException(status_code=404, detail="Orden clinica no encontrada.")
    return {
        "item": order,
        "support_pdf_url": f"/api/orders/{order['order_code']}/support.pdf?v={_ASSET_VER}",
        "storage": {
            "bucket": get_supports_bucket_name(),
            "object": order["support_pdf_object"],
        },
    }


@app.post("/api/orders/{order_code}/notify-eps")
def api_notify_eps_order_status(
    order_code: str, payload: NotifyEpsPayload
) -> dict[str, Any]:
    approved_host, canonical_target_url = _validate_eps_callback_url(payload.callback_url)
    order = get_public_order(order_code)
    if not order:
        raise HTTPException(status_code=404, detail="Orden clinica no encontrada.")

    outbound_payload = {
        "order_code": order["order_code"],
        "folio_number": order["folio_number"],
        "cups_code": order["cups_code"],
        "status": order["status"],
        "center_city": order["center_city"],
    }
    delivered_live = False
    if (
        approved_host in ALLOWED_EPS_WEBHOOK_HOSTS
        and os.getenv("ENABLE_LIVE_EPS_WEBHOOK", "false").lower() == "true"
    ):
        try:
            with httpx.Client(timeout=3.5, follow_redirects=False) as client:
                resp = client.post(canonical_target_url, json=outbound_payload)
                delivered_live = 200 <= resp.status_code < 300
        except Exception:
            delivered_live = False

    return {
        "status": "notified",
        "order_code": order["order_code"],
        "order_status": order["status"],
        "target_host": approved_host,
        "callback_url": canonical_target_url,
        "delivered_live": delivered_live,
    }


@app.get("/api/orders/{order_code}/support.pdf")
def api_download_order_pdf(order_code: str) -> Response:
    order = get_public_order(order_code)
    if not order:
        raise HTTPException(status_code=404, detail="Soporte PDF no encontrado.")
    pdf_bytes = fetch_order_support_pdf(order)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="{order["order_code"]}-autorizacion.pdf"',
            **NO_CACHE_HEADERS,
        },
    )


@app.get("/", response_class=HTMLResponse)
def serve_portal_ui() -> Response:
    asset_ver = _compute_asset_version()
    index_file = FRONTEND_DIR / "index.html"
    html = (
        index_file.read_text(encoding="utf-8")
        .replace('href="/styles.css"', f'href="/styles.css?v={asset_ver}"')
        .replace('src="/app.js"', f'src="/app.js?v={asset_ver}"')
    )
    return HTMLResponse(content=html, status_code=200, headers=dict(NO_CACHE_HEADERS))


@app.get("/styles.css")
def serve_css() -> Response:
    css_text = (FRONTEND_DIR / "styles.css").read_text(encoding="utf-8")
    return Response(
        content=css_text,
        media_type="text/css; charset=utf-8",
        headers=dict(NO_CACHE_HEADERS),
    )


@app.get("/app.js")
def serve_js() -> Response:
    js_text = (FRONTEND_DIR / "app.js").read_text(encoding="utf-8")
    return Response(
        content=js_text,
        media_type="application/javascript; charset=utf-8",
        headers=dict(NO_CACHE_HEADERS),
    )
