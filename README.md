# Cymbal Health — Plataforma de Autorizaciones Clinicas y Asistente ADK (`v2.0`)

Plataforma hospitalaria de **Cymbal Health IPS** sobre **Google Cloud** que integra gestion de autorizaciones medicas (**CUPS / CIE-10**), emision de ordenes PDF firmadas y el asistente clinico **`cymbal-clinical-agent`** construido con **Google Agent Development Kit (ADK)**, **Vertex AI Search** y defensa en tiempo de ejecucion de **5 anillos**.

---

## 1. Capacidades de `v2.0`

- **Dual-Datastore Read-Only bajo Minimo Privilegio:**
  1. **Vertex AI Search (`cymbal-health-clinical-protocols-ds`):** Recuperacion aumentada (RAG) sobre 6 protocolos oficiales de autorizacion clinica y codigos CUPS usando `roles/discoveryengine.viewer`.
  2. **Cloud SQL for PostgreSQL 15 (`clinical_orders_public_v`):** Consulta parametrizada de solo lectura mediante **IAM Database Authentication** y rol `cymbal_agent_readonly` (`SELECT`-only).
- **Defensa Runtime de 5 Anillos (`<30 ms`):**
  1. **Model Armor:** Inspeccion en linea de prompts de usuario, fragmentos recuperados desde Vertex AI Search (*Indirect Prompt Injection*) y respuesta generada.
  2. **Cloud DLP (Ley 1581 de 2012):** Anonimizacion de Cedula Colombiana (`[REDACTED_COLOMBIA_CC]`), tarjetas y correos antes de invocar el modelo.
  3. **Herramientas Tipadas ADK:** `get_order_status` y `search_clinical_protocol_rag` sin generacion libre de SQL.
  4. **Aislamiento N-Tier Sin Llaves:** `INGRESS_TRAFFIC_INTERNAL_ONLY` + tokens **OIDC** entre microservicios + **ADC** (`0%` API Keys) + contenedor sin root (`UID 10001`).
  5. **Observabilidad Forense:** Logs estructurados en **Cloud Logging** con correlacion UDM hacia **Google SecOps**.

---

## 2. Ejecucion Local y Pruebas

```bash
# Ejecutar suite completa de pruebas (UI limpia, PDF clinico, RAG, 5 anillos, OIDC y MCP)
pytest tests/ -q

# Iniciar el portal Cymbal Health v2.0
uvicorn backend.app:app --port 8080

# Iniciar el servidor gobernado github-backlog-mcp
uvicorn mcp_backlog_server.server:app --port 8090
```
