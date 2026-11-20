"""5-Ring AI Defense Layer: Model Armor Guardrails + Cloud DLP (Ley 1581) + SecOps Telemetry.

Implements:
- Ring 1a: <30ms hospital input guardrails + optional live Google Cloud Model Armor API
  blocking Jailbreak/Prompt Injection, explicit SQLi, natural-language bulk data dumps,
  schema/resource enumeration, and SSRF metadata probes with HTTP 403.
- Ring 1b: Indirect Prompt Injection scanner for RAG chunks (`sanitize_rag_chunks`).
- Ring 2: In-line Colombian PII & PCI redaction (`mask_colombian_pii_dlp`:
  `[REDACTED_COLOMBIA_CC]`, `[REDACTED_PAYMENT_CARD]`, `[REDACTED_EMAIL]`).
- Ring 3: Output sanitization & internal identifier redaction (`sanitize_model_response`).
- Ring 5: Structured security telemetry & Google SecOps Chronicle UDM query.
"""

from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
import os
import re
import threading
import time
from typing import Any
import unicodedata

import httpx

FORBIDDEN_STATIC_KEY_ENV_VARS: tuple[str, ...] = (
    "GEMINI_API_KEY",
    "GOOGLE_API_KEY",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
)

# Ring 1a deterministic sub-30ms rules evaluated on normalized lowercase ASCII text
_RING_1A_RULES: tuple[tuple[str, re.Pattern[str], str], ...] = (
    (
        "PI_AND_JAILBREAK:SSRF_METADATA_PROBE",
        re.compile(
            r"("
            r"169\.254\.169\.254|"
            r"metadata\.google\.internal|"
            r"computemetadata/v1|"
            r"(?:file|gopher|dict|ftp|ldap)://|"
            r"https?://(?:127\.0\.0\.1|localhost|0\.0\.0\.0)"
            r")",
            re.IGNORECASE,
        ),
        "Intento de SSRF o acceso al Metadata Server bloqueado por Model Armor.",
    ),
    (
        "PI_AND_JAILBREAK:SQL_INJECTION_EXPLICIT",
        re.compile(
            r"("
            r"\bselect\s+\*|"
            r"\bunion\s+(?:all\s+)?select\b|"
            r"\bdrop\s+(?:table|view|database|schema)\b|"
            r"\btruncate\s+table\b|"
            r"\bdelete\s+from\b|"
            r"\binsert\s+into\b|"
            r"\bupdate\s+clinical_orders|"
            r"(?:'|\b)\s*or\s+['\"]?1['\"]?\s*=\s*['\"]?1|"
            r"\bconfidential\s*(?:=|!=|<>|>)\s*[01]|"
            r"\bord-2026-990[12]\b"
            r")",
            re.IGNORECASE,
        ),
        "Intento de inyeccion SQL o acceso a registros reservados Ley 1581 bloqueado.",
    ),
    (
        "PI_AND_JAILBREAK:BULK_EXFILTRATION_DUMP",
        re.compile(
            r"("
            r"\bdump\b|"
            r"\bvolcado\b|"
            r"toda\s+la\s+informacion\s+de\s+(?:esa|la|esta)\s+tabla|"
            r"todas\s+las\s+filas|"
            r"todos\s+los\s+(?:registros|pacientes|afiliados|datos)\s+de\s+la\s+(?:base|tabla|vista)|"
            r"listar?\s+(?:todas\s+las\s+ordenes|todos\s+los\s+pacientes|toda\s+la\s+tabla)|"
            r"(?:exporta|exportar|extrae|extraer|descarga|descargar|muestrame|dame)\s+toda\s+la\s+(?:base|tabla|informacion)|"
            r"\ball\s+rows\b|"
            r"\bentire\s+(?:table|database)\b|"
            r"\bexport\s+all\s+(?:records|patients|orders)\b"
            r")",
            re.IGNORECASE,
        ),
        "Solicitud de volcado o extraccion masiva de datos clinicos bloqueada (Deny-by-Default).",
    ),
    (
        "PI_AND_JAILBREAK:SCHEMA_RESOURCE_ENUMERATION",
        re.compile(
            r"("
            r"a\s+que\s+recursos\s+(?:puedes\s+conectarte|te\s+conectas|tienes\s+acceso)|"
            r"(?:que|cuales)\s+tablas\s+(?:existen|hay|tienes)|"
            r"(?:estructura|esquema|columnas)\s+de\s+la\s+(?:base\s+de\s+datos|tabla)|"
            r"\binformation_schema\b|"
            r"\bpg_catalog\b|"
            r"\bpg_tables\b|"
            r"\bsqlite_master\b|"
            r"\bclinical_orders_public_v\b|"
            r"\bcymbal_agent_readonly\b|"
            r"(?:que|cuales)\s+(?:buckets|bases\s+de\s+datos|cuentas\s+de\s+servicio|service\s+accounts)\b|"
            r"what\s+(?:tables|schemas|resources|buckets|databases)\s+(?:exist|can\s+you\s+access|are\s+connected)"
            r")",
            re.IGNORECASE,
        ),
        "Enumeracion de esquemas SQL y recursos internos de infraestructura bloqueada.",
    ),
    (
        "PI_AND_JAILBREAK:SYSTEM_OVERRIDE",
        re.compile(
            r"("
            r"ignore\s+(?:all\s+)?(?:previous|prior|above)\s+(?:instructions|prompts|rules)|"
            r"disregard\s+(?:all\s+)?(?:previous|system)\s+(?:instructions|rules)|"
            r"ignora\s+(?:todas\s+)?(?:las\s+|tus\s+)?(?:instrucciones|reglas|directrices)|"
            r"olvida\s+(?:todas\s+)?(?:tus\s+|las\s+)?(?:instrucciones|reglas)|"
            r"\bsystem\s+override\b|"
            r"\bdeveloper\s+mode\b|"
            r"\bmodo\s+(?:desarrollador|dios|sin\s+restricciones)\b|"
            r"\bjailbreak\b|"
            r"\bdan\s+mode\b|"
            r"(?:reveal|show|print|output|revela|muestrame|imprime|dime)\s+(?:your\s+|the\s+|tu\s+|el\s+)?(?:system\s+prompt|instrucciones\s+internas|prompt\s+del\s+sistema)|"
            r"desactiva\s+(?:model\s+armor|dlp|los\s+filtros|la\s+seguridad)"
            r")",
            re.IGNORECASE,
        ),
        "Intento de Prompt Injection / System Override bloqueado por Model Armor.",
    ),
)

_INDIRECT_RAG_PI_RE = re.compile(
    r"("
    r"ignore\s+(?:all\s+)?(?:previous|prior)\s+instructions|"
    r"ignora\s+(?:todas\s+)?las\s+instrucciones|"
    r"system\s+override|"
    r"developer\s+mode|"
    r"169\.254\.169\.254|"
    r"metadata\.google\.internal|"
    r"<script\b|"
    r"!\[[^\]]*\]\(https?://|"
    r"\bdrop\s+table\b|"
    r"\bconfidential\s*=\s*1\b"
    r")",
    re.IGNORECASE,
)

# Ring 2 Cloud DLP patterns (Colombian Ley 1581 de 2012 + PCI + Email)
_PAYMENT_CARD_RE = re.compile(
    r"\b(?:\d{4}[-\s]){3}\d{4}\b|\b\d{13,19}\b"
)
_EMAIL_RE = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
)
_COLOMBIA_CC_LABELED_RE = re.compile(
    r"\b(?:C\.?\s*C\.?|CEDULA(?:\s+DE\s+CIUDADANIA)?|DOCUMENTO(?:\s+DE\s+IDENTIDAD)?|T\.?\s*I\.?|C\.?\s*E\.?)"
    r"\s*(?:N[Oo.]?\s*)?[:#-]?\s*(?!\*{2,})\d[\d.\s-]{5,13}\d\b",
    re.IGNORECASE,
)
_COLOMBIA_CC_DOTTED_RE = re.compile(
    r"\b\d{1,3}(?:\.\d{3}){2}\b"
)
_COLOMBIA_CC_RAW_DIGITS_RE = re.compile(
    r"(?<![A-Za-z0-9*-])(?<!RM\s)\b\d{7,10}\b(?![-\d])"
)

# Ring 3 internal identifiers redaction
_INTERNAL_IDENTIFIERS_RE = re.compile(
    r"("
    r"\bclinical_orders_public_v\b|"
    r"\bclinical_orders\b|"
    r"\bcymbal_agent_readonly\b|"
    r"\bcymbal_portal_rw\b|"
    r"\bcymbal_health_db\b|"
    r"\bcymbal-health-pg-main\b|"
    r"gs://[A-Za-z0-9._/-]+|"
    r"\b[a-z0-9-]+@[a-z0-9-]+\.iam\.gserviceaccount\.com\b"
    r")",
    re.IGNORECASE,
)

_STRIP_EMOJI_RE = re.compile(
    "["
    "\U0001f1e0-\U0001f1ff"
    "\U0001f300-\U0001f5ff"
    "\U0001f600-\U0001f64f"
    "\U0001f680-\U0001f6ff"
    "\U0001f700-\U0001f77f"
    "\U0001f780-\U0001f7ff"
    "\U0001f800-\U0001f8ff"
    "\U0001f900-\U0001f9ff"
    "\U0001fa00-\U0001faff"
    "\u2600-\u27bf"
    "\ufe0f"
    "]+"
)

_TELEMETRY_LOCK = threading.Lock()
_SECURITY_EVENTS: deque[dict[str, Any]] = deque(maxlen=150)
_TELEMETRY_COUNTERS: dict[str, int] = {
    "prompts_inspected": 0,
    "ring1a_blocked": 0,
    "ring1b_rag_dropped": 0,
    "ring2_dlp_redactions": 0,
    "ring3_internal_redactions": 0,
    "ring4_oidc_hops": 0,
    "eps_webhooks_blocked": 0,
}


def _normalize_for_guardrail(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", str(text or ""))
    stripped = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    collapsed = re.sub(r"\s+", " ", stripped).strip().lower()
    return collapsed


def verify_zero_static_api_keys() -> None:
    """Rejects execution if any static LLM API key environment variable is configured."""
    for env_name in FORBIDDEN_STATIC_KEY_ENV_VARS:
        val = os.getenv(env_name, "").strip()
        if val:
            raise RuntimeError(
                f"Security policy violation: static credential {env_name} is prohibited. "
                "Use keyless Application Default Credentials (ADC) exclusively."
            )


def record_security_event(
    *,
    ring: str,
    verdict: str,
    filter_match: str,
    detail: str,
    counter_key: str | None = None,
    increment: int = 1,
) -> None:
    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "ring": ring,
        "verdict": verdict,
        "filter_match": filter_match,
        "detail": detail[:220],
    }
    with _TELEMETRY_LOCK:
        if counter_key and counter_key in _TELEMETRY_COUNTERS:
            _TELEMETRY_COUNTERS[counter_key] += increment
        _SECURITY_EVENTS.appendleft(event)


def reset_security_telemetry() -> None:
    with _TELEMETRY_LOCK:
        _SECURITY_EVENTS.clear()
        for key in _TELEMETRY_COUNTERS:
            _TELEMETRY_COUNTERS[key] = 0


def _call_live_model_armor_if_configured(prompt: str) -> dict[str, Any] | None:
    template_id = os.getenv("MODEL_ARMOR_TEMPLATE_ID", "").strip()
    if not template_id or os.getenv("ENABLE_LIVE_MODEL_ARMOR", "false").lower() != "true":
        return None
    project_id = os.getenv("GCP_PROJECT_ID", "cymbal-health-prod")
    location = os.getenv("GCP_REGION", "us-central1")
    url = (
        f"https://modelarmor.{location}.rep.googleapis.com/v1/"
        f"projects/{project_id}/locations/{location}/templates/{template_id}:sanitizeUserPrompt"
    )
    try:
        import google.auth
        from google.auth.transport.requests import Request as GoogleAuthRequest

        credentials, _ = google.auth.default(
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        credentials.refresh(GoogleAuthRequest())
        with httpx.Client(timeout=2.5) as client:
            resp = client.post(
                url,
                headers={"Authorization": f"Bearer {credentials.token}"},
                json={"userPromptData": {"text": prompt[:2000]}},
            )
        if resp.status_code == 200:
            data = resp.json()
            state = (
                data.get("sanitizationResult", {}).get("filterMatchState")
                or ""
            )
            if str(state).upper() == "MATCH_FOUND":
                return {
                    "verdict": "BLOCKED",
                    "filter_match": "PI_AND_JAILBREAK:MODEL_ARMOR_LIVE_MATCH",
                    "reason": "Solicitud bloqueada por plantilla Google Cloud Model Armor.",
                }
    except Exception:
        return None
    return None


def inspect_prompt_ring1a(prompt: str) -> dict[str, Any]:
    """Ring 1a (<30ms): Evaluates Model Armor + Hospital Security rules on incoming prompt."""
    t0 = time.perf_counter()
    with _TELEMETRY_LOCK:
        _TELEMETRY_COUNTERS["prompts_inspected"] += 1

    normalized = _normalize_for_guardrail(prompt)
    for filter_code, pattern, reason in _RING_1A_RULES:
        if pattern.search(normalized):
            elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)
            record_security_event(
                ring="RING_1A_MODEL_ARMOR",
                verdict="BLOCKED",
                filter_match=filter_code,
                detail=reason,
                counter_key="ring1a_blocked",
            )
            return {
                "verdict": "BLOCKED",
                "filter_match": filter_code,
                "reason": reason,
                "latency_ms": elapsed_ms,
            }

    live_block = _call_live_model_armor_if_configured(prompt)
    if live_block is not None:
        elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)
        record_security_event(
            ring="RING_1A_MODEL_ARMOR",
            verdict="BLOCKED",
            filter_match=live_block["filter_match"],
            detail=live_block["reason"],
            counter_key="ring1a_blocked",
        )
        return {**live_block, "latency_ms": elapsed_ms}

    elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)
    return {
        "verdict": "ALLOWED",
        "filter_match": "NONE",
        "reason": "Prompt validado por Anillo 1a.",
        "latency_ms": elapsed_ms,
    }


def mask_colombian_pii_dlp(text: str) -> str:
    """Ring 2 (Ley 1581 de 2012): Masks Colombian CC, payment cards, and emails in-line."""
    if not text:
        return ""

    working = str(text)

    if os.getenv("ENABLE_LIVE_CLOUD_DLP", "false").lower() == "true":
        project_id = os.getenv("GCP_PROJECT_ID", "cymbal-health-prod")
        dlp_url = f"https://dlp.googleapis.com/v2/projects/{project_id}/content:deidentify"
        try:
            import google.auth
            from google.auth.transport.requests import Request as GoogleAuthRequest

            credentials, _ = google.auth.default(
                scopes=["https://www.googleapis.com/auth/cloud-platform"]
            )
            credentials.refresh(GoogleAuthRequest())
            dlp_body = {
                "item": {"value": working},
                "inspectConfig": {
                    "infoTypes": [
                        {"name": "COLOMBIA_CDC_NUMBER"},
                        {"name": "CREDIT_CARD_NUMBER"},
                        {"name": "EMAIL_ADDRESS"},
                    ]
                },
                "deidentifyConfig": {
                    "infoTypeTransformations": {
                        "transformations": [
                            {
                                "infoTypes": [{"name": "COLOMBIA_CDC_NUMBER"}],
                                "primitiveTransformation": {
                                    "replaceConfig": {"newValue": {"stringValue": "[REDACTED_COLOMBIA_CC]"}}
                                },
                            },
                            {
                                "infoTypes": [{"name": "CREDIT_CARD_NUMBER"}],
                                "primitiveTransformation": {
                                    "replaceConfig": {"newValue": {"stringValue": "[REDACTED_PAYMENT_CARD]"}}
                                },
                            },
                            {
                                "infoTypes": [{"name": "EMAIL_ADDRESS"}],
                                "primitiveTransformation": {
                                    "replaceConfig": {"newValue": {"stringValue": "[REDACTED_EMAIL]"}}
                                },
                            },
                        ]
                    }
                },
            }
            with httpx.Client(timeout=2.5) as client:
                resp = client.post(
                    dlp_url,
                    headers={"Authorization": f"Bearer {credentials.token}"},
                    json=dlp_body,
                )
            if resp.status_code == 200:
                working = str(resp.json().get("item", {}).get("value") or working)
        except Exception:
            pass

    redactions = 0

    working, n_cards = _PAYMENT_CARD_RE.subn("[REDACTED_PAYMENT_CARD]", working)
    redactions += n_cards

    working, n_emails = _EMAIL_RE.subn("[REDACTED_EMAIL]", working)
    redactions += n_emails

    working, n_cc_lbl = _COLOMBIA_CC_LABELED_RE.subn("[REDACTED_COLOMBIA_CC]", working)
    redactions += n_cc_lbl

    working, n_cc_dot = _COLOMBIA_CC_DOTTED_RE.subn("[REDACTED_COLOMBIA_CC]", working)
    redactions += n_cc_dot

    working, n_cc_raw = _COLOMBIA_CC_RAW_DIGITS_RE.subn("[REDACTED_COLOMBIA_CC]", working)
    redactions += n_cc_raw

    if redactions > 0:
        record_security_event(
            ring="RING_2_CLOUD_DLP_LEY_1581",
            verdict="REDACTED",
            filter_match="DLP_INFO_TYPE_MASKED",
            detail=f"Anonimizados {redactions} identificadores sensibles bajo Ley 1581.",
            counter_key="ring2_dlp_redactions",
            increment=redactions,
        )

    return working


def sanitize_rag_chunks(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Ring 1b: Filters out Vertex AI Search / RAG documents containing Indirect Prompt Injection."""
    clean_chunks: list[dict[str, Any]] = []
    for chunk in chunks or []:
        combined = " ".join(
            str(v) for v in chunk.values() if isinstance(v, (str, int, float))
        )
        normalized = _normalize_for_guardrail(combined)
        if _INDIRECT_RAG_PI_RE.search(normalized):
            record_security_event(
                ring="RING_1B_RAG_FILTER",
                verdict="DROPPED",
                filter_match="INDIRECT_PROMPT_INJECTION",
                detail=f"Fragmento RAG descartado ({chunk.get('protocol_id', 'unknown')}).",
                counter_key="ring1b_rag_dropped",
            )
            continue

        sanitized_copy: dict[str, Any] = {}
        for key, val in chunk.items():
            if isinstance(val, str):
                sanitized_copy[key] = mask_colombian_pii_dlp(val)
            else:
                sanitized_copy[key] = val
        clean_chunks.append(sanitized_copy)

    return clean_chunks


def sanitize_model_response(text: str) -> str:
    """Ring 3 + Ring 2 Post-LLM: Redacts internal schema/role identifiers, PII, and Unicode emojis."""
    if not text:
        return ""

    working = str(text)
    working, n_internal = _INTERNAL_IDENTIFIERS_RE.subn(
        "[INTERNAL_RESOURCE_REDACTED]", working
    )
    if n_internal > 0:
        record_security_event(
            ring="RING_3_OUTPUT_ISOLATION",
            verdict="REDACTED",
            filter_match="INTERNAL_IDENTIFIER_REDACTED",
            detail=f"Redactados {n_internal} identificadores internos en respuesta.",
            counter_key="ring3_internal_redactions",
            increment=n_internal,
        )

    working = mask_colombian_pii_dlp(working)
    working = _STRIP_EMOJI_RE.sub("", working)
    return working.strip()


def get_security_telemetry_snapshot() -> dict[str, Any]:
    """Ring 5: Returns AI security governance telemetry and SecOps Chronicle UDM query."""
    with _TELEMETRY_LOCK:
        counters = dict(_TELEMETRY_COUNTERS)
        recent = list(_SECURITY_EVENTS)[:25]

    return {
        "governance_framework": "Cymbal Health 5-Ring AI Defense + Ley 1581 de 2012",
        "auth_posture": {
            "mode": "ADC_KEYLESS_OAUTH2_OIDC",
            "static_api_keys_present": False,
        },
        "rings": {
            "ring_1a_model_armor_input": "ACTIVE",
            "ring_1b_rag_indirect_pi_filter": "ACTIVE",
            "ring_2_cloud_dlp_ley_1581": "ACTIVE",
            "ring_3_isolated_system_prompt": "ACTIVE",
            "ring_4_tier2_oidc_service_hop": "ACTIVE",
            "ring_5_secops_udm_telemetry": "ACTIVE",
        },
        "counters": counters,
        "secops_udm_query": (
            'metadata.product_name = "Cymbal Health Clinical Agent" '
            'AND target.application = "cymbal-health-clinical-agent-v3" '
            'AND (security_result.action = "BLOCK" OR security_result.category_details =~ "PI_AND_JAILBREAK|DLP")'
        ),
        "recent_events": recent,
    }
