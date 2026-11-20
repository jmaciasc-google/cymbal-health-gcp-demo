"""Keyless Vertex AI Search (Discovery Engine v1) RAG connector for Cymbal Health IPS.

Queries Data Store `cymbal-health-clinical-protocols-ds` in location `global`
using Google Application Default Credentials (OAuth2 ADC - zero static API keys),
with a deterministic local clinical corpus fallback covering the 6 official
Colombian CUPS / CIE-10 / Ley 1581 protocols.
"""

from __future__ import annotations

import os
import re
import unicodedata
from typing import Any

import httpx

CLINICAL_PROTOCOLS_CORPUS: list[dict[str, Any]] = [
    {
        "protocol_id": "PROT-CARD-2026-01",
        "title": "Protocolo de Cardiologia No Invasiva: Holter 24h y Ecocardiograma Doppler",
        "specialty": "Cardiologia Clinica",
        "cups_codes": ["895001", "881234"],
        "cie10_codes": ["I499", "I10X"],
        "content": (
            "Protocolo PROT-CARD-2026-01 (CUPS 895001 Monitoreo Electrocardiografico Continuo "
            "Holter 24 Horas; CUPS 881234 Ecocardiograma Transtoracico Doppler Color). "
            "Pertinencia clinica: indicado en palpitaciones recurrentes, presincope o sincope "
            "en estudio (CIE-10 I499) con electrocardiograma basal previo de 12 derivaciones, "
            "y en hipertension arterial estadio II con disnea de esfuerzo (CIE-10 I10X) para "
            "cuantificar fraccion de eyeccion ventricular izquierda (FEVI) e hipertrofia. "
            "Preparacion del paciente: no requiere ayuno; para Holter asistir con ropa de dos "
            "piezas, piel limpia en torax sin lociones y registrar sintomas en bitacora."
        ),
    },
    {
        "protocol_id": "PROT-NEURO-2026-02",
        "title": "Protocolo de Neuroimagen Avanzada: Resonancia Magnetica Cerebral",
        "specialty": "Neurologia Clinica",
        "cups_codes": ["883101", "883102"],
        "cie10_codes": ["G439", "G409"],
        "content": (
            "Protocolo PROT-NEURO-2026-02 (CUPS 883101 Resonancia Nuclear Magnetica de Cerebro "
            "Simple; CUPS 883102 Resonancia Cerebral con Gadolinio). Pertinencia clinica: "
            "indicado en cefalea subaguda o cronica con signos de bandera roja como fosfenos "
            "persistentes, empeoramiento progresivo o hallazgos focales (CIE-10 G439). "
            "Preparacion y seguridad: retirar objetos metalicos, joyas y protesis removibles; "
            "diligenciar encuesta de seguridad ferromagnetica descartando marcapasos no "
            "condicional. Para CUPS 883102 exigir tasa de filtracion glomerular vigente."
        ),
    },
    {
        "protocol_id": "PROT-ONCO-2026-03",
        "title": "Protocolo de Medicina Nuclear Oncologica: Tomografia PET-CT con 18F-FDG",
        "specialty": "Oncologia Clinica",
        "cups_codes": ["921801"],
        "cie10_codes": ["C349", "C809"],
        "content": (
            "Protocolo PROT-ONCO-2026-03 (CUPS 921801 Tomografia por Emision de Positrones "
            "PET-CT Corporal Total con 18F-FDG). Pertinencia clinica: requiere confirmacion "
            "histopatologica previa y acta formal de Junta Medica Oncologica para estadificacion "
            "ganglionar mediastinica o sistemica en neoplasia pulmonar (CIE-10 C349). "
            "Preparacion obligatoria: ayuno minimo de 6 horas, dieta baja en carbohidratos, "
            "reposo fisico 24 horas antes y glucemia capilar previa estrictamente menor a 180 mg/dL."
        ),
    },
    {
        "protocol_id": "PROT-FARM-2026-04",
        "title": "Protocolo de Junta Interdisciplinaria y Terapia Biologica de Alto Costo",
        "specialty": "Endocrinologia",
        "cups_codes": ["890343"],
        "cie10_codes": ["E119", "E112"],
        "content": (
            "Protocolo PROT-FARM-2026-04 (CUPS 890343 Junta Interdisciplinaria y Autorizacion "
            "de Terapia Biologica / Escalonamiento Farmacologico). Pertinencia clinica: "
            "indicado en diabetes mellitus tipo 2 de alto riesgo cardiorrenal (CIE-10 E119) "
            "con falla terapeutica documentada a doble esquema oral, HbA1c igual o mayor a 8.0% "
            "y albuminuria persistente. Incluye registro en Cuenta de Alto Costo sin cobro de "
            "cuota moderadora, bitacora de glucometrias de 14 dias y cadena de frio de 2 C a 8 C."
        ),
    },
    {
        "protocol_id": "PROT-TELE-2026-05",
        "title": "Protocolo de Telemedicina, Bioetica y Proteccion de Datos Ley 1581 de 2012",
        "specialty": "Auditoria y Gobernanza Clinica",
        "cups_codes": ["890201", "890502"],
        "cie10_codes": ["Z719", "Z048"],
        "content": (
            "Protocolo PROT-TELE-2026-05 (Gobernanza de Historia Clinica bajo Ley Estatutaria "
            "1581 de 2012, Ley 23 de 1981 y Resolucion 2654 de 2019). Todo soporte clinico debe "
            "enmascarar documentos nacionales de identidad (CC) y proteger datos sensibles del "
            "afiliado. Los expedientes calificados bajo reserva de Comite de Bioetica o Dictamen "
            "Pericial estan excluidos de consultas operativas y asistentes automatizados. "
            "Queda estrictamente prohibida la extraccion o volcado masivo de registros clinicos."
        ),
    },
    {
        "protocol_id": "PROT-LAB-2026-06",
        "title": "Protocolo de Laboratorio Cardiometabolico: Panel Basal y Perfil Lipidico",
        "specialty": "Medicina Interna",
        "cups_codes": ["903895"],
        "cie10_codes": ["E785", "E780"],
        "content": (
            "Protocolo PROT-LAB-2026-06 (CUPS 903895 Panel Metabolico Basal y Perfil Lipidico "
            "Completo: colesterol total, HDL, LDL, trigliceridos, glucemia basal y creatinina). "
            "Pertinencia clinica: control trimestral de programa de riesgo cardiometabolico y "
            "ajuste de terapia con estatinas en hiperlipidemia mixta (CIE-10 E785). "
            "Preparacion del paciente: ayuno estricto de 10 a 12 horas (solo agua pura) y "
            "abstencion de alcohol o ejercicio fisico intenso durante las 24 horas previas."
        ),
    },
]


def _normalize_search_text(raw: str) -> str:
    decomposed = unicodedata.normalize("NFKD", str(raw or ""))
    ascii_only = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return ascii_only.lower()


def get_datastore_config() -> dict[str, str]:
    """Returns Discovery Engine Data Store configuration using neutral environment defaults."""
    project_id = os.getenv("GCP_PROJECT_ID", "cymbal-health-prod")
    location = os.getenv("VERTEX_SEARCH_LOCATION", "global")
    datastore_id = os.getenv(
        "VERTEX_SEARCH_DATASTORE_ID", "cymbal-health-clinical-protocols-ds"
    )
    endpoint = (
        f"https://discoveryengine.googleapis.com/v1/projects/{project_id}"
        f"/locations/{location}/collections/default_collection"
        f"/dataStores/{datastore_id}/servingConfigs/default_search:search"
    )
    return {
        "project_id": project_id,
        "location": location,
        "datastore_id": datastore_id,
        "endpoint": endpoint,
    }


def _is_live_vertex_search_enabled() -> bool:
    explicit = os.getenv("ENABLE_LIVE_VERTEX_SEARCH", "").strip().lower()
    if explicit == "true":
        return True
    if explicit == "false":
        return False
    return bool(os.getenv("K_SERVICE"))


def _search_local_protocols(query: str, max_results: int = 3) -> list[dict[str, Any]]:
    norm_q = _normalize_search_text(query)
    tokens = [tok for tok in re.findall(r"[a-z0-9-]+", norm_q) if len(tok) >= 3]
    if not tokens:
        return [dict(doc) for doc in CLINICAL_PROTOCOLS_CORPUS[:max_results]]

    scored: list[tuple[int, dict[str, Any]]] = []
    for doc in CLINICAL_PROTOCOLS_CORPUS:
        haystack = _normalize_search_text(
            " ".join(
                [
                    doc["protocol_id"],
                    doc["title"],
                    doc["specialty"],
                    " ".join(doc["cups_codes"]),
                    " ".join(doc["cie10_codes"]),
                    doc["content"],
                ]
            )
        )
        score = 0
        for code in doc["cups_codes"]:
            if code.lower() in norm_q:
                score += 12
        for cie in doc["cie10_codes"]:
            if cie.lower() in norm_q:
                score += 10
        if doc["protocol_id"].lower() in norm_q:
            score += 15
        for tok in tokens:
            if tok in haystack:
                score += 2
        if score > 0:
            scored.append((score, dict(doc)))

    if not scored:
        return [dict(doc) for doc in CLINICAL_PROTOCOLS_CORPUS[:max_results]]

    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [item for _, item in scored[:max_results]]


def query_vertex_ai_search(query: str, max_results: int = 3) -> dict[str, Any]:
    """Queries Vertex AI Search (`discoveryengine.googleapis.com/v1`) via OAuth2 ADC with local fallback."""
    cfg = get_datastore_config()
    clean_query = (query or "").strip()[:400]
    safe_limit = max(1, min(int(max_results), 5))

    if _is_live_vertex_search_enabled() and clean_query:
        try:
            import google.auth
            from google.auth.transport.requests import Request as GoogleAuthRequest

            credentials, _ = google.auth.default(
                scopes=["https://www.googleapis.com/auth/cloud-platform"]
            )
            credentials.refresh(GoogleAuthRequest())
            payload = {
                "query": clean_query,
                "pageSize": safe_limit,
                "queryExpansionSpec": {"condition": "AUTO"},
                "spellCorrectionSpec": {"mode": "AUTO"},
            }
            with httpx.Client(timeout=4.0) as client:
                resp = client.post(
                    cfg["endpoint"],
                    headers={
                        "Authorization": f"Bearer {credentials.token}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
            if resp.status_code == 200:
                body = resp.json()
                raw_results = body.get("results") or []
                parsed_chunks: list[dict[str, Any]] = []
                for idx, entry in enumerate(raw_results[:safe_limit], start=1):
                    doc = entry.get("document") or {}
                    struct_data = doc.get("structData") or doc.get("derivedStructData") or {}
                    snippets = struct_data.get("snippets") or []
                    snippet_text = ""
                    if snippets and isinstance(snippets[0], dict):
                        snippet_text = str(snippets[0].get("snippet") or "")
                    content_text = (
                        str(struct_data.get("content") or "")
                        or snippet_text
                        or str(struct_data.get("extractive_answers") or "")
                    )
                    if content_text:
                        parsed_chunks.append(
                            {
                                "protocol_id": str(
                                    struct_data.get("protocol_id")
                                    or doc.get("id")
                                    or f"VAIS-DOC-{idx}"
                                ),
                                "title": str(
                                    struct_data.get("title")
                                    or "Protocolo Clinico Cymbal Health"
                                ),
                                "specialty": str(
                                    struct_data.get("specialty") or "Auditoria Medica"
                                ),
                                "cups_codes": list(struct_data.get("cups_codes") or []),
                                "cie10_codes": list(struct_data.get("cie10_codes") or []),
                                "content": content_text,
                            }
                        )
                if parsed_chunks:
                    return {
                        "source": "vertex-ai-search-live",
                        "datastore_id": cfg["datastore_id"],
                        "location": cfg["location"],
                        "chunks": parsed_chunks,
                    }
        except Exception:
            pass

    fallback_chunks = _search_local_protocols(clean_query, max_results=safe_limit)
    return {
        "source": "local-corpus-fallback",
        "datastore_id": cfg["datastore_id"],
        "location": cfg["location"],
        "chunks": fallback_chunks,
    }
