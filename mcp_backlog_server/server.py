"""`github-backlog-mcp` server for Gemini Enterprise & Antigravity IDE governance.

Cloud Run service: `cymbal-health-backlog-mcp`
Dedicated Identity: `cymbal-health-mcp-sa`
- Ingress: `INGRESS_TRAFFIC_INTERNAL_ONLY` + OIDC verification (`invoker_iam_disabled = false`)
- Secret Access: `roles/secretmanager.secretAccessor` ONLY on `cymbal-health-github-pat`
  via Application Default Credentials (ADC) — zero static secrets in code or image.
- Exposes MCP tools:
  1. `create_github_issue`
  2. `get_github_issue_42`
  3. `list_pr_security_findings` (PR #1 clean v2.0 deploy vs PR #2 Wiz Code + CodeMender CWE-89/CWE-918 gate)
"""

from __future__ import annotations

import json
import os
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from mcp_backlog_server import MCP_SERVER_NAME, MCP_SERVICE_NAME, MCP_VERSION

app = FastAPI(
    title="Cymbal Health - Governed GitHub Backlog MCP Server",
    version=MCP_VERSION,
)

ISSUE_42_CANONICAL: dict[str, Any] = {
    "issue_number": 42,
    "repository": os.getenv("GITHUB_REPO", "cymbal-health/cymbal-health-gcp-demo"),
    "title": (
        "Habilitar cymbal-clinical-agent (Google ADK + Vertex AI Search) en modal "
        "minimalista bajo Ley 1581 y Least Privilege"
    ),
    "state": "OPEN",
    "labels": [
        "feature-adk",
        "vertex-ai-search",
        "least-privilege",
        "ley-1581",
        "ux-modal-zero-emoji",
    ],
    "grounding_sources": [
        "01_Solicitud_Negocio_Ordenes_Clinicas.md",
        "02_Arquitectura_Referencia_Cymbal_GCP.md",
        "03_Politica_Seguridad_ISO27001_Ley1581.md",
        "04_Estandar_UX_Ingenieria_Cymbal.md",
    ],
    "acceptance_criteria": [
        "Exponer el asistente cymbal-clinical-agent dentro de un modal limpio en v2.0 sin botones de prueba ni conmutadores artificiales y con 0% emojis.",
        "Conectar el agente bajo Minimo Privilegio tanto al Data Store de Vertex AI Search (cymbal-health-clinical-protocols-ds con roles/discoveryengine.viewer) como a la vista de solo lectura clinical_orders_public_v (rol SQL cymbal_agent_readonly).",
        "Autenticar hacia Vertex AI Gemini, Vertex AI Search, Model Armor y Cloud DLP 100% via ADC con la Service Account dedicada cymbal-health-agent-sa (0% API keys) e invocacion OIDC desde cymbal-health-portal-sa.",
        "Aplicar defensa de 5 anillos: Model Armor (<30ms) sobre prompt del usuario, chunks recuperados de RAG y salida del modelo, mas Cloud DLP para anonimizar Cedula Colombiana (CC -> [REDACTED_COLOMBIA_CC]).",
        "Registrar el descriptor en Agent Registry (/api/agent/card) con ingress INGRESS_TRAFFIC_INTERNAL_ONLY y emitir telemetria forense para Google SecOps.",
    ],
}

_CREATED_ISSUES: dict[int, dict[str, Any]] = {42: dict(ISSUE_42_CANONICAL)}


def _read_github_pat_from_secret_manager() -> str | None:
    if os.getenv("ENABLE_LIVE_GITHUB_MCP", "false").lower() != "true":
        return None
    project_id = os.getenv("GCP_PROJECT_ID", "cymbal-health-prod")
    secret_id = os.getenv("GITHUB_PAT_SECRET_ID", "cymbal-health-github-pat")
    from google.cloud import secretmanager  # type: ignore[import-untyped]

    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("utf-8").strip()


def tool_create_github_issue(
    title: str,
    body: str,
    labels: list[str] | None = None,
    issue_number: int = 42,
) -> dict[str, Any]:
    _ = _read_github_pat_from_secret_manager()
    record = {
        "issue_number": issue_number,
        "repository": os.getenv("GITHUB_REPO", "cymbal-health/cymbal-health-gcp-demo"),
        "title": title.strip(),
        "body": body.strip(),
        "state": "OPEN",
        "labels": labels or ["feature-adk", "vertex-ai-search", "least-privilege", "ley-1581"],
        "auth_source": "secretmanager:cymbal-health-github-pat:adc",
        "grounding_sources": ISSUE_42_CANONICAL["grounding_sources"],
    }
    _CREATED_ISSUES[issue_number] = record
    return record


def tool_get_github_issue_42() -> dict[str, Any]:
    return _CREATED_ISSUES.get(42, dict(ISSUE_42_CANONICAL))


def tool_list_pr_security_findings(
    pr_number: int = 2, stage: str = "demo/pr2-vulnerable-change"
) -> dict[str, Any]:
    """Returns Cloud Build Shift-Left gate findings for PR #1 (clean) or PR #2 (vulnerable vs remediated)."""
    if pr_number == 1 or stage in ("backup/v2-safe-agent", "demo/pr2-remediated", "remediated"):
        return {
            "pr_number": pr_number,
            "stage": stage,
            "gate_status": "PASSED",
            "blocking_findings_count": 0,
            "scanners": {
                "artifact_registry": "CLEAN (0 Critical/High CVEs in requirements.txt)",
                "wizcli_v1": "PASSED (wizcli scan dir & wizcli scan container-image: 0 primitive roles, UID 10001 verified)",
                "codemender_sandbox": "PASSED (CM_PLAIN=true cm verify: 0 exploitable CWE-89/CWE-918 findings, pytest 100% green)",
            },
            "findings": [],
        }

    return {
        "pr_number": pr_number,
        "stage": "demo/pr2-vulnerable-change",
        "gate_status": "BLOCKED",
        "blocking_findings_count": 4,
        "findings": [
            {
                "id": "WIZ-IAC-IAM-001",
                "engine": "Wiz Code (wizcli v1.83.0 - wizcli scan dir .)",
                "severity": "CRITICAL",
                "category": "IAM_LEAST_PRIVILEGE_AND_PUBLIC_INGRESS",
                "file": "terraform/pr2_quick_debug_iam.tf",
                "summary": (
                    "Violacion de Minimo Privilegio en PR #2: concesion de rol primitivo "
                    "roles/editor a nivel de proyecto combinada con ingress INGRESS_TRAFFIC_ALL "
                    "(Toxic Combination hacia Cloud SQL cymbal-health-pg-main y Vertex AI Search)."
                ),
                "remediation": (
                    "Eliminar terraform/pr2_quick_debug_iam.tf y conservar exclusivamente las "
                    "Service Accounts dedicadas con bindings por recurso e ingress privado."
                ),
            },
            {
                "id": "AR-CVE-2024-26130",
                "engine": "Artifact Registry Vulnerability Scanning + wizcli scan container-image",
                "severity": "HIGH",
                "category": "SCA_DEPENDENCY_CVE",
                "file": "requirements.txt",
                "summary": (
                    "Dependencias degradadas con CVEs activos en PR #2: cryptography==41.0.3 "
                    "(CVE-2024-26130) y urllib3==1.26.15 (CVE-2023-45803)."
                ),
                "remediation": (
                    "Restaurar cryptography==44.0.1 y urllib3==2.2.3 en requirements.txt."
                ),
            },
            {
                "id": "CM-SQLI-001",
                "engine": "Google CodeMender (CM_PLAIN=true cm verify - gemini-3.8-flash-cyber)",
                "severity": "CRITICAL",
                "cwe": "CWE-89",
                "verification_status": "VERIFIED_EXPLOITABLE_IN_SANDBOX",
                "false_positive_probability": 0.0,
                "file": "backend/db.py",
                "endpoint": "GET /api/orders/search?q=",
                "summary": (
                    "SQL Injection verificada empiricamente en sandbox aislado: el payload "
                    "\"' OR '1'='1 --\" evade confidential = 0 y exfiltra registros protegidos "
                    "por Ley 1581 (ORD-2026-9901, ORD-2026-9902)."
                ),
                "remediation": (
                    "Parametrizar la consulta con marcadores (?) exclusivamente sobre la vista "
                    "clinical_orders_public_v."
                ),
            },
            {
                "id": "CM-SSRF-002",
                "engine": "Google CodeMender (CM_PLAIN=true cm verify - gemini-3.8-flash-cyber)",
                "severity": "CRITICAL",
                "cwe": "CWE-918",
                "verification_status": "VERIFIED_EXPLOITABLE_IN_SANDBOX",
                "false_positive_probability": 0.0,
                "file": "backend/app.py",
                "endpoint": "POST /api/orders/{order_code}/notify-eps",
                "summary": (
                    "Server-Side Request Forgery (SSRF) verificada en sandbox: callback_url "
                    "sin validacion permite solicitar http://169.254.169.254/computeMetadata/v1/ "
                    "para sustraer tokens OAuth2 de la Service Account en Cloud Run."
                ),
                "remediation": (
                    "Exigir esquema HTTPS estricto, validar contra lista blanca de dominios "
                    "EAPB autorizados y bloquear rangos link-local (169.254.0.0/16), loopback y RFC1918."
                ),
            },
        ],
    }


MCP_TOOLS_MANIFEST: list[dict[str, Any]] = [
    {
        "name": "create_github_issue",
        "description": "Creates a governed GitHub backlog issue from Gemini Enterprise PRD grounding.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "body": {"type": "string"},
                "labels": {"type": "array", "items": {"type": "string"}},
                "issue_number": {"type": "integer", "default": 42},
            },
            "required": ["title", "body"],
        },
    },
    {
        "name": "get_github_issue_42",
        "description": "Fetches canonical GitHub Issue #42 with Vertex AI Search RAG and Least Privilege criteria.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "list_pr_security_findings",
        "description": "Lists Wiz Code v1, Google CodeMender, and Artifact Registry findings on PR #2.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "pr_number": {"type": "integer", "default": 2},
                "stage": {
                    "type": "string",
                    "enum": [
                        "backup/v2-safe-agent",
                        "demo/pr2-vulnerable-change",
                        "demo/pr2-remediated",
                    ],
                    "default": "demo/pr2-vulnerable-change",
                },
            },
        },
    },
]


class JsonRpcRequest(BaseModel):
    jsonrpc: str = "2.0"
    id: int | str | None = None
    method: str
    params: dict[str, Any] = Field(default_factory=dict)


class CreateIssueRestPayload(BaseModel):
    title: str = Field(..., min_length=5, max_length=200)
    body: str = Field(..., min_length=5, max_length=8000)
    labels: list[str] | None = None
    issue_number: int = 42


def dispatch_mcp_rpc(req: JsonRpcRequest) -> dict[str, Any]:
    if req.method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req.id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": MCP_SERVER_NAME, "version": MCP_VERSION},
            },
        }

    if req.method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": req.id,
            "result": {"tools": MCP_TOOLS_MANIFEST},
        }

    if req.method == "tools/call":
        tool_name = req.params.get("name")
        args = req.params.get("arguments") or {}
        if tool_name == "create_github_issue":
            out = tool_create_github_issue(
                title=str(args.get("title", "")),
                body=str(args.get("body", "")),
                labels=args.get("labels"),
                issue_number=int(args.get("issue_number", 42)),
            )
        elif tool_name == "get_github_issue_42":
            out = tool_get_github_issue_42()
        elif tool_name == "list_pr_security_findings":
            out = tool_list_pr_security_findings(
                pr_number=int(args.get("pr_number", 2)),
                stage=str(args.get("stage", "demo/pr2-vulnerable-change")),
            )
        else:
            return {
                "jsonrpc": "2.0",
                "id": req.id,
                "error": {"code": -32601, "message": f"Unknown MCP tool: {tool_name}"},
            }
        return {
            "jsonrpc": "2.0",
            "id": req.id,
            "result": {
                "content": [{"type": "text", "text": json.dumps(out, ensure_ascii=True)}],
                "structuredContent": out,
                "isError": False,
            },
        }

    return {
        "jsonrpc": "2.0",
        "id": req.id,
        "error": {"code": -32601, "message": f"Unsupported method: {req.method}"},
    }


@app.get("/healthz")
def healthz() -> dict[str, Any]:
    project_id = os.getenv("GCP_PROJECT_ID", "cymbal-health-prod")
    return {
        "status": "ok",
        "server": MCP_SERVER_NAME,
        "service": MCP_SERVICE_NAME,
        "service_account": f"cymbal-health-mcp-sa@{project_id}.iam.gserviceaccount.com",
        "secret_binding": "cymbal-health-github-pat (resource-level secretAccessor via ADC)",
    }


@app.post("/mcp")
def mcp_jsonrpc_endpoint(req: JsonRpcRequest) -> dict[str, Any]:
    return dispatch_mcp_rpc(req)


@app.post("/messages")
def mcp_sse_messages_endpoint(req: JsonRpcRequest) -> dict[str, Any]:
    return dispatch_mcp_rpc(req)


@app.get("/sse")
def mcp_sse_stream() -> StreamingResponse:
    def _event_gen() -> Any:
        endpoint_event = json.dumps({"endpoint": "/messages", "server": MCP_SERVER_NAME})
        yield f"event: endpoint\ndata: {endpoint_event}\n\n"

    return StreamingResponse(_event_gen(), media_type="text/event-stream")


@app.get("/api/tools")
def rest_list_tools() -> dict[str, Any]:
    return {"server": MCP_SERVER_NAME, "tools": MCP_TOOLS_MANIFEST}


@app.post("/api/issues", status_code=201)
def rest_create_issue(payload: CreateIssueRestPayload) -> dict[str, Any]:
    return tool_create_github_issue(
        title=payload.title,
        body=payload.body,
        labels=payload.labels,
        issue_number=payload.issue_number,
    )


@app.get("/api/issues/42")
def rest_get_issue_42() -> dict[str, Any]:
    return tool_get_github_issue_42()


@app.get("/api/prs/{pr_number}/security-findings")
def rest_get_pr_findings(
    pr_number: int, stage: str = "demo/pr2-vulnerable-change"
) -> dict[str, Any]:
    if pr_number < 1:
        raise HTTPException(status_code=400, detail="Invalid PR number.")
    return tool_list_pr_security_findings(pr_number=pr_number, stage=stage)
