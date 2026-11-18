---
name: code-to-cloud-triage
description: Correlates verified Google CodeMender source findings (CWE-89 SQLi, CWE-918 SSRF) in Cymbal Health with Wiz CLI v1 (wizcli scan dir / wizcli scan container-image) and Cloud Run Least Privilege posture to block Toxic Combinations in PR #2.
---

# Skill: Code-to-Cloud Triage & Blast Radius Analysis (Cymbal Health)

## Proposito
Conecta los hallazgos verificados empiricamente en codigo por **Google CodeMender (`CM_PLAIN=true cm`)** con el analisis de infraestructura y contenedor de **Wiz Code (`wizcli v1.83.0`)** y **Artifact Registry** sobre **Cymbal Health** (`cymbal-health-web-portal` y `cymbal-health-clinical-agent`).

## Cuando Usar Esta Skill
- Al auditar el Pull Request `#2` (`demo/pr2-vulnerable-change`) mediante la herramienta MCP `list_pr_security_findings` en `github-backlog-mcp`.
- Inmediatamente despues de ejecutar `evaluate-codemender-finding` para priorizar la remediacion unificada de codigo, dependencias e IAM.

---

## Evaluacion de Combinacion Toxica en PR #2

```text
[Exposicion Ingress INGRESS_TRAFFIC_ALL en terraform/pr2_quick_debug_iam.tf]
        |
        +---> [Hallazgo Codigo: CM-SSRF-002 (CWE-918 en POST /api/orders/{code}/notify-eps)]
        |            |
        |            v
        |     [Acceso a Metadata Server 169.254.169.254 -> Robo de Token OAuth2]
        |
        +---> [Hallazgo IaC: WIZ-IAC-IAM-001 (roles/editor a nivel de proyecto)]
        |            |
        |            v
        |     [Movimiento lateral hacia Cloud SQL cymbal-health-pg-main y Vertex AI Search]
        |
        +---> [Hallazgo Codigo: CM-SQLI-001 (CWE-89 en GET /api/orders/search)]
        |            |
        |            v
        |     [Exfiltracion de registros reservados Ley 1581 (confidential = 1)]
        |
        +---> [Hallazgo SCA: AR-CVE-2024-26130 (cryptography 41.0.3 / urllib3 1.26.15)]
```

## Matriz de Remediacion Obligatoria (`demo/pr2-remediated`)

| ID Hallazgo | Motor | Severidad | Remediacion Verificada |
| :--- | :--- | :--- | :--- |
| `CM-SQLI-001` | CodeMender (`cm verify --plain`) | CRITICAL | Parametrizar `SELECT` con `?` exclusivamente sobre `clinical_orders_public_v`. |
| `CM-SSRF-002` | CodeMender (`cm verify --plain`) | CRITICAL | Exigir `https://`, validar contra allowlist EAPB y bloquear `169.254.0.0/16` / RFC1918. |
| `WIZ-IAC-IAM-001` | Wiz CLI v1 (`wizcli scan dir .`) | CRITICAL | Eliminar `terraform/pr2_quick_debug_iam.tf` y preservar las 4 SAs dedicadas. |
| `AR-CVE-2024-26130` | Artifact Registry + `wizcli scan container-image` | HIGH | Actualizar `requirements.txt` a `cryptography==44.0.1` y `urllib3==2.2.3`. |
