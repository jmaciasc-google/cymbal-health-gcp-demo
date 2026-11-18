"""Vertex AI Search (`discoveryengine`) RAG connector for Cymbal Health clinical protocols.

Connects via 100% keyless Application Default Credentials (ADC) under Least Privilege:
- Service Account: `cymbal-health-agent-sa`
- IAM Role: `roles/discoveryengine.viewer` ONLY on Data Store
  `cymbal-health-clinical-protocols-ds` (seeded from private bucket
  `cymbal-health-protocols-<project_number>`).
- Deterministic Offline Fallback: Searches the local Markdown corpus in
  `docs/clinical-protocols/*.md` when running offline, in CI `pytest`, or prior
  to initial Discovery Engine document indexing.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import os
from pathlib import Path
import re
from typing import Any

PROTOCOLS_DIR = Path(__file__).resolve().parent.parent / "docs" / "clinical-protocols"


@dataclass
class ProtocolChunk:
    doc_id: str
    protocol_code: str
    title: str
    cups_codes: list[str]
    snippet: str
    source_uri: str
    retrieval_mode: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def get_datastore_metadata() -> dict[str, Any]:
    project_id = os.getenv("GCP_PROJECT_ID", "cymbal-health-prod")
    project_number = os.getenv("GCP_PROJECT_NUMBER", "123456789012")
    location = os.getenv("VERTEX_SEARCH_LOCATION", "global")
    datastore_id = os.getenv(
        "VERTEX_SEARCH_DATASTORE_ID", "cymbal-health-clinical-protocols-ds"
    )
    protocols_bucket = os.getenv(
        "PROTOCOLS_BUCKET", f"cymbal-health-protocols-{project_number}"
    )
    return {
        "engine": "Google Cloud Vertex AI Search (Discovery Engine v1)",
        "projectId": project_id,
        "location": location,
        "dataStoreId": datastore_id,
        "servingConfig": (
            f"projects/{project_id}/locations/{location}/collections/default_collection"
            f"/dataStores/{datastore_id}/servingConfigs/default_search"
        ),
        "sourceBucket": protocols_bucket,
        "iamRole": "roles/discoveryengine.viewer",
        "authMode": "ADC_KEYLESS",
    }


def _load_local_protocol_corpus() -> list[dict[str, Any]]:
    docs: list[dict[str, Any]] = []
    if not PROTOCOLS_DIR.exists():
        return docs
    for md_path in sorted(PROTOCOLS_DIR.glob("*.md")):
        raw = md_path.read_text(encoding="utf-8")
        title_match = re.search(r"^#\s+(.+)$", raw, re.MULTILINE)
        code_match = re.search(r"\bPROT-[A-Z]+-\d{4}-\d{2}\b", raw)
        cups_found = sorted(set(re.findall(r"\b(?:88|89|90|92)\d{4}\b", raw)))
        docs.append(
            {
                "doc_id": md_path.stem,
                "protocol_code": code_match.group(0) if code_match else md_path.stem[:16],
                "title": title_match.group(1).strip() if title_match else md_path.stem,
                "cups_codes": cups_found,
                "content": raw,
                "source_uri": f"clinical-protocols/{md_path.name}",
            }
        )
    return docs


def _search_local_protocols(query: str, top_k: int = 2) -> list[ProtocolChunk]:
    corpus = _load_local_protocol_corpus()
    if not corpus:
        return []

    tokens = [
        tok
        for tok in re.findall(r"[a-z0-9]{3,}", query.lower())
        if tok not in {"para", "cual", "cuales", "como", "del", "las", "los", "con", "una", "por", "que"}
    ]
    scored: list[tuple[int, dict[str, Any]]] = []
    for doc in corpus:
        haystack = f"{doc['title']} {' '.join(doc['cups_codes'])} {doc['content']}".lower()
        score = 0
        for tok in tokens:
            if tok in doc["cups_codes"]:
                score += 12
            elif tok in doc["title"].lower():
                score += 5
            elif tok in haystack:
                score += 2
        scored.append((score, doc))

    scored.sort(key=lambda pair: pair[0], reverse=True)
    selected = [doc for score, doc in scored if score > 0][:top_k]
    if not selected:
        selected = [corpus[0]]

    chunks: list[ProtocolChunk] = []
    for doc in selected:
        # Build clean concise clinical excerpt without Markdown headings noise
        clean_lines = [
            line.strip()
            for line in doc["content"].splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
        snippet = " ".join(clean_lines)[:620]
        chunks.append(
            ProtocolChunk(
                doc_id=doc["doc_id"],
                protocol_code=doc["protocol_code"],
                title=doc["title"],
                cups_codes=doc["cups_codes"],
                snippet=snippet,
                source_uri=doc["source_uri"],
                retrieval_mode="local_protocol_mirror",
            )
        )
    return chunks


def search_vertex_clinical_protocols(query: str, top_k: int = 2) -> list[ProtocolChunk]:
    """Queries Vertex AI Search Data Store via ADC, falling back cleanly to local corpus."""
    live_rag = os.getenv("ENABLE_LIVE_VERTEX_SEARCH", "false").lower() == "true"
    meta = get_datastore_metadata()

    if live_rag:
        try:
            import google.auth
            from google.auth.transport.requests import Request as GoogleAuthRequest
            import httpx

            credentials, detected_project = google.auth.default(
                scopes=["https://www.googleapis.com/auth/cloud-platform"]
            )
            credentials.refresh(GoogleAuthRequest())
            project_id = os.getenv("GCP_PROJECT_ID", detected_project or meta["projectId"])
            location = meta["location"]
            datastore_id = meta["dataStoreId"]
            endpoint = (
                f"https://discoveryengine.googleapis.com/v1/projects/{project_id}"
                f"/locations/{location}/collections/default_collection"
                f"/dataStores/{datastore_id}/servingConfigs/default_search:search"
            )
            payload: dict[str, Any] = {
                "query": query,
                "pageSize": top_k,
                "contentSearchSpec": {
                    "snippetSpec": {"returnSnippet": True},
                    "extractiveContentSpec": {"maxExtractiveAnswerCount": 2},
                },
            }
            with httpx.Client(timeout=6.0) as client:
                resp = client.post(
                    endpoint,
                    headers={"Authorization": f"Bearer {credentials.token}"},
                    json=payload,
                )
                if resp.status_code == 200:
                    results = resp.json().get("results", [])
                    live_chunks: list[ProtocolChunk] = []
                    for item in results[:top_k]:
                        doc = item.get("document", {})
                        derived = doc.get("derivedStructData", {}) or doc.get("structData", {})
                        extractive = derived.get("extractive_answers", [])
                        snippets = derived.get("snippets", [])
                        text_piece = ""
                        if extractive and isinstance(extractive[0], dict):
                            text_piece = str(extractive[0].get("content", ""))
                        elif snippets and isinstance(snippets[0], dict):
                            text_piece = str(snippets[0].get("snippet", ""))
                        if not text_piece:
                            continue
                        title = str(derived.get("title") or doc.get("id") or "Protocolo Clinico")
                        code_match = re.search(r"\bPROT-[A-Z]+-\d{4}-\d{2}\b", text_piece + " " + title)
                        cups_found = sorted(set(re.findall(r"\b(?:88|89|90|92)\d{4}\b", text_piece)))
                        live_chunks.append(
                            ProtocolChunk(
                                doc_id=str(doc.get("id", "ds-doc")),
                                protocol_code=code_match.group(0) if code_match else "PROT-CYMBAL-DS",
                                title=title,
                                cups_codes=cups_found,
                                snippet=text_piece[:620],
                                source_uri=str(derived.get("link", f"datastore://{datastore_id}")),
                                retrieval_mode="vertex_ai_search_discoveryengine",
                            )
                        )
                    if live_chunks:
                        return live_chunks
        except Exception:
            pass

    return _search_local_protocols(query, top_k=top_k)
