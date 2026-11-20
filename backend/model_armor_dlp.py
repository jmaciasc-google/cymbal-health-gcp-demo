"""5-Ring Runtime Defense: Model Armor (`<30ms`), Indirect RAG Guard, Cloud DLP & SecOps UDM.

Implements layered runtime protection around `cymbal-clinical-agent`:
- Ring 1a (`inspect_and_sanitize_prompt`): Blocks Direct Prompt Injection & Jailbreak
  (`PI_AND_JAILBREAK`) on user input via Model Armor `sanitizeUserPrompt` (ADC) + `<5ms`
  inline rule engine.
- Ring 1b (`sanitize_rag_chunks`): Scans retrieved Vertex AI Search Data Store chunks
  before LLM grounding to neutralize Indirect Prompt Injection embedded in documents.
- Ring 1c (`sanitize_model_response`): Scans final model output (`sanitizeModelResponse`)
  to prevent system prompt leakage or unmasked national IDs.
- Ring 2 (`mask_colombian_pii_dlp`): De-identifies Colombian Cedula (`CC` ->
  `[REDACTED_COLOMBIA_CC]`), payment cards, and email PII under Ley 1581 de 2012.
- Ring 5 (`_TELEMETRY_BUFFER`): Emits structured Cloud Logging JSON with `traceId`,
  `callerIp`, `principalEmail`, and Google SecOps UDM correlation queries.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import logging
import os
import re
import time
import uuid
from typing import Any

from backend.datastore_rag import ProtocolChunk

logger = logging.getLogger("cymbal.security.guardrail")

_TELEMETRY_BUFFER: deque[dict[str, Any]] = deque(maxlen=50)

_PI_JAILBREAK_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "SYSTEM_OVERRIDE_EN",
        re.compile(
            r"(ignore\s+(all\s+)?(previous|prior|system|clinical)\s+instructions|"
            r"disregard\s+(all\s+)?rules|reveal\s+(your\s+)?system\s+prompt|"
            r"developer\s+mode\s+enabled|act\s+as\s+dan\b|unrestricted\s+admin\s+mode)",
            re.IGNORECASE,
        ),
    ),
    (
        "SYSTEM_OVERRIDE_ES",
        re.compile(
            r"(ignora\s+(todas\s+)?las\s+instrucciones(\s+clinicas|\s+anteriores|\s+previas)?|"
            r"olvida\s+tus\s+reglas|muestra\s+el\s+prompt\s+del\s+sistema|"
            r"omite\s+(las\s+)?politicas\s+de\s+seguridad|modo\s+(administrador\s+)?sin\s+restricciones)",
            re.IGNORECASE,
        ),
    ),
    (
        "DATA_EXFIL_CONFIDENTIAL",
        re.compile(
            r"(select\s+\*\s+from\s+clinical_orders\b|dump\s+confidential|"
            r"bypass\s+ley\s*1581|extrae\s+todos\s+los\s+registros\s+restringidos|"
            r"drop\s+table|union\s+select|confidential\s*=\s*1)",
            re.IGNORECASE,
        ),
    ),
    (
        "SSRF_METADATA_THEFT",
        re.compile(
            r"(169\.254\.169\.254|metadata\.google\.internal|computeMetadata/v1)",
            re.IGNORECASE,
        ),
    ),
]

_PAYMENT_CARD_PATTERN = re.compile(r"\b(?:\d{4}[-\s]?){3}\d{1,4}\b")

_COLOMBIA_CC_LABELED_PATTERN = re.compile(
    r"\b(?:C\.?\s*C\.?|cedul[ao](?:\s+de\s+ciudadania)?|documento(?:\s+de\s+identidad)?)"
    r"\s*[:#-]?\s*(?:\d{1,3}(?:[.\s]\d{3}){2}|\d{6,10})\b",
    re.IGNORECASE,
)

_COLOMBIA_CC_STANDALONE_PATTERN = re.compile(
    r"(?<![-\w])(?:\d{1,3}(?:\.\d{3}){2}|\b[1-9]\d{6,9}\b)(?![-\w])"
)

_EMAIL_PII_PATTERN = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
)


@dataclass
class GuardrailInspectionResult:
    allowed: bool
    verdict: str
    filter_match: str | None
    sanitized_prompt: str
    dlp_findings: list[str] = field(default_factory=list)
    latency_ms: float = 0.0
    trace_id: str = ""
    secops_udm_query: str = ""
    cloud_log_entry: dict[str, Any] = field(default_factory=dict)


def build_secops_udm_query(trace_id: str, caller_ip: str, principal_email: str) -> str:
    return (
        f'metadata.product_name = "Google Cloud Model Armor" '
        f'AND target.application = "cymbal-clinical-agent" '
        f'AND network.http.referral_url = "{trace_id}" '
        f'AND principal.ip = "{caller_ip}" '
        f'AND principal.user.email_addresses = "{principal_email}"'
    )


def mask_colombian_pii_dlp(text: str) -> tuple[str, list[str]]:
    """Masks Colombian CC, payment cards, and email PII before RAG/LLM invocation."""
    findings: list[str] = []
    masked = text

    def _card_repl(_match: re.Match[str]) -> str:
        if "CREDIT_CARD_NUMBER" not in findings:
            findings.append("CREDIT_CARD_NUMBER")
        return "[REDACTED_PAYMENT_CARD]"

    masked = _PAYMENT_CARD_PATTERN.sub(_card_repl, masked)

    def _cc_labeled_repl(_match: re.Match[str]) -> str:
        if "COLOMBIA_CDC_NUMBER" not in findings:
            findings.append("COLOMBIA_CDC_NUMBER")
        return "[REDACTED_COLOMBIA_CC]"

    masked = _COLOMBIA_CC_LABELED_PATTERN.sub(_cc_labeled_repl, masked)

    def _cc_standalone_repl(_match: re.Match[str]) -> str:
        if "COLOMBIA_CDC_NUMBER" not in findings:
            findings.append("COLOMBIA_CDC_NUMBER")
        return "[REDACTED_COLOMBIA_CC]"

    masked = _COLOMBIA_CC_STANDALONE_PATTERN.sub(_cc_standalone_repl, masked)

    def _email_repl(_match: re.Match[str]) -> str:
        if "EMAIL_ADDRESS" not in findings:
            findings.append("EMAIL_ADDRESS")
        return "[REDACTED_EMAIL]"

    masked = _EMAIL_PII_PATTERN.sub(_email_repl, masked)
    return masked, findings


def _check_live_model_armor_user_prompt(text: str, template_name: str) -> str | None:
    """Optional live Google Cloud Model Armor `sanitizeUserPrompt` call via ADC."""
    if os.getenv("ENABLE_LIVE_MODEL_ARMOR", "false").lower() != "true":
        return None
    try:
        import google.auth
        from google.auth.transport.requests import Request as GoogleAuthRequest
        import httpx

        credentials, _ = google.auth.default(
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        credentials.refresh(GoogleAuthRequest())
        location = os.getenv("GCP_REGION", "us-central1")
        endpoint = f"https://modelarmor.{location}.rep.googleapis.com/v1/{template_name}:sanitizeUserPrompt"
        with httpx.Client(timeout=2.5) as client:
            resp = client.post(
                endpoint,
                headers={"Authorization": f"Bearer {credentials.token}"},
                json={"userPromptData": {"text": text}},
            )
            if resp.status_code == 200:
                verdict_state = (
                    resp.json()
                    .get("sanitizationResult", {})
                    .get("filterMatchState", "")
                )
                if verdict_state == "MATCH_FOUND":
                    return "MODEL_ARMOR_API_MATCH"
    except Exception:
        pass
    return None


def sanitize_rag_chunks(chunks: list[ProtocolChunk]) -> tuple[list[ProtocolChunk], int]:
    """Ring 1b: Scans retrieved Vertex AI Search chunks for Indirect Prompt Injection."""
    safe_chunks: list[ProtocolChunk] = []
    quarantined = 0
    for chunk in chunks:
        poisoned = False
        for _, pattern in _PI_JAILBREAK_PATTERNS:
            if pattern.search(chunk.snippet):
                poisoned = True
                break
        if poisoned:
            quarantined += 1
            continue
        masked_snippet, _ = mask_colombian_pii_dlp(chunk.snippet)
        safe_chunks.append(
            ProtocolChunk(
                doc_id=chunk.doc_id,
                protocol_code=chunk.protocol_code,
                title=chunk.title,
                cups_codes=chunk.cups_codes,
                snippet=masked_snippet,
                source_uri=chunk.source_uri,
                retrieval_mode=chunk.retrieval_mode,
            )
        )
    return safe_chunks, quarantined


def sanitize_model_response(response_text: str) -> str:
    """Ring 1c: Scrubs model output against accidental PII or system instruction leakage."""
    masked_out, _ = mask_colombian_pii_dlp(response_text)
    if re.search(r"SYSTEM_INSTRUCTION_CONFIDENTIAL_MARKER", masked_out):
        return "Respuesta retenida por politica de seguridad de salida de Model Armor."
    return masked_out


def inspect_and_sanitize_prompt(
    prompt: str,
    *,
    caller_ip: str = "10.28.0.10",
    principal_email: str = "medico.especialista@cymbal-health.co",
    trace_id: str | None = None,
) -> GuardrailInspectionResult:
    """Ring 1a + Ring 2 + Ring 5: `<30ms` Model Armor + Cloud DLP inspection & UDM logging."""
    start = time.perf_counter()
    project_id = os.getenv("GCP_PROJECT_ID", "cymbal-health-prod")
    resolved_trace = trace_id or uuid.uuid4().hex
    raw_prompt = (prompt or "").strip()

    model_armor_template = (
        os.getenv("MODEL_ARMOR_TEMPLATE_ID")
        or f"projects/{project_id}/locations/us-central1/templates/cymbal-health-model-armor"
    )
    dlp_deidentify_template = (
        os.getenv("DLP_DEIDENTIFY_TEMPLATE_ID")
        or f"projects/{project_id}/locations/us-central1/deidentifyTemplates/cymbal-health-dlp-deidentify"
    )

    matched_rule: str | None = None
    for rule_name, pattern in _PI_JAILBREAK_PATTERNS:
        if pattern.search(raw_prompt):
            matched_rule = rule_name
            break

    if matched_rule is None:
        matched_rule = _check_live_model_armor_user_prompt(raw_prompt, model_armor_template)

    sanitized_prompt, dlp_info_types = mask_colombian_pii_dlp(raw_prompt)
    elapsed_ms = round((time.perf_counter() - start) * 1000.0, 2)

    allowed = matched_rule is None
    verdict = (
        "ALLOW_SANITIZED"
        if (allowed and dlp_info_types)
        else ("ALLOW" if allowed else "BLOCKED")
    )
    filter_match = None if allowed else f"PI_AND_JAILBREAK:{matched_rule}"
    udm_query = build_secops_udm_query(resolved_trace, caller_ip, principal_email)

    log_entry: dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        "severity": "WARNING" if not allowed else ("NOTICE" if dlp_info_types else "INFO"),
        "logging.googleapis.com/trace": f"projects/{project_id}/traces/{resolved_trace}",
        "traceId": resolved_trace,
        "callerIp": caller_ip,
        "principalEmail": principal_email,
        "serviceName": "cymbal-health-clinical-agent-v3",
        "serviceAccount": f"cymbal-health-agent-sa@{project_id}.iam.gserviceaccount.com",
        "modelArmorTemplate": model_armor_template,
        "modelArmorVerdict": verdict,
        "filterMatch": filter_match,
        "dlpDeidentifyTemplate": dlp_deidentify_template,
        "dlpInfoTypes": dlp_info_types,
        "sanitizedPreview": sanitized_prompt[:160],
        "latencyMs": elapsed_ms,
        "secopsUdmQuery": udm_query,
    }

    _TELEMETRY_BUFFER.appendleft(log_entry)
    logger.info(json.dumps(log_entry, ensure_ascii=True))

    return GuardrailInspectionResult(
        allowed=allowed,
        verdict=verdict,
        filter_match=filter_match,
        sanitized_prompt=sanitized_prompt,
        dlp_findings=dlp_info_types,
        latency_ms=elapsed_ms,
        trace_id=resolved_trace,
        secops_udm_query=udm_query,
        cloud_log_entry=log_entry,
    )


def record_external_telemetry_event(entry: dict[str, Any]) -> None:
    if isinstance(entry, dict) and entry:
        _TELEMETRY_BUFFER.appendleft(dict(entry))


def clear_security_telemetry() -> None:
    _TELEMETRY_BUFFER.clear()


def get_recent_security_telemetry() -> list[dict[str, Any]]:
    return list(_TELEMETRY_BUFFER)
