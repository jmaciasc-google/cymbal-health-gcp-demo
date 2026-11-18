# Arquitectura de Referencia Oficial en Google Cloud -- Cymbal Health

**Organizacion:** Cymbal Health -- Comite de Arquitectura Cloud e Inteligencia Artificial  
**Marco de Diseno:** Google Cloud Well-Architected Framework (Seguridad, Confiabilidad, Optimizacion de Costos y Excelencia Operativa)  
**Region Primaria:** `us-central1` (`global` para Vertex AI Search)

---

## 1. Topologia N-Tier Serverless y Fronteras de Confianza

La plataforma **Cymbal Health** evoluciona desde un portal transaccional `v1.0` puro en `main` hacia una arquitectura `v2.0` agentica (`PR #1`) en **dos niveles de aislamiento** conectada a una red VPC dedicada (`10.28.0.0/24`) mediante **Direct VPC Egress**:

1. **Borde Global y Defensa Perimetral:**
   * **Global External Application Load Balancer (`EXTERNAL_MANAGED`)** con certificado TLS administrado y redireccion HTTP a HTTPS.
   * **Google Cloud Armor WAF** adjunto al Backend Service bloqueando en el borde reglas preconfiguradas OWASP (`sqli-v33-stable`, `xss-v33-stable`, `rce-v33-stable`, `lfi-v33-stable`) y aplicando limite de tasa por IP (`120 req/60s`).
2. **Tier 1 -- Presentacion y API Transaccional (`cymbal-health-web-portal`):**
   * Servicio **Cloud Run v2** configurado con `ingress = "INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER"`, impidiendo cualquier acceso directo a la URL `.run.app` que intente evadir Cloud Armor.
   * Ejecuta bajo la identidad dedicada `cymbal-health-portal-sa` e invoca al Tier 2 adjuntando tokens **OIDC** firmados por Google Cloud.
3. **Tier 2 -- Servicios Internos de IA y Herramientas MCP (`cymbal-health-clinical-agent` y `cymbal-health-backlog-mcp`):**
   * Servicios **Cloud Run v2** estrictamente privados (`ingress = "INGRESS_TRAFFIC_INTERNAL_ONLY"`, `invoker_iam_disabled = false`).
   * `cymbal-health-clinical-agent` implementa el agente clinico con **Google Agent Development Kit (ADK)**, registrado y gobernado en **Agent Registry**, consumiendo modelos **Gemini en Vertex AI** via **Application Default Credentials (ADC)**.
   * `cymbal-health-backlog-mcp` expone herramientas MCP autorizadas hacia el repositorio de ingenieria leyendo su token exclusivamente desde **Secret Manager** en memoria.
4. **Capa Dual de Datos Privados (`0% IPs Publicas`, Segregacion de Lectura):**
   * **Cloud SQL para PostgreSQL 15 (`cymbal-health-pg-main`):** Configurado con `ipv4_enabled = false` sobre **Private Service Access (`10.28.16.0/20`)**, cifrado TLS obligatorio (`ENCRYPTED_ONLY`) y autenticacion sin contrasenas mediante `cloudsql.iam_authentication = "on"`. El agente consulta unicamente `clinical_orders_public_v` con el rol `cymbal_agent_readonly` (`SELECT`-only).
   * **Vertex AI Search Data Store (`cymbal-health-clinical-protocols-ds`):** Motor RAG empresarial (`discoveryengine.googleapis.com`) alimentado desde el bucket privado `cymbal-health-protocols-<project_number>` con las 6 guias clinicas CUPS/CIE-10. `cymbal-health-agent-sa` posee exclusivamente `roles/discoveryengine.viewer` y `roles/storage.objectViewer`.
   * **Cloud Storage (`cymbal-health-soportes-<project_number>`):** Almacen privado de ordenes PDF hospitalarias vectoriales con `public_access_prevention = "enforced"` y `uniform_bucket_level_access = true`.

---

## 2. Pipeline CI/CD Shift-Left (`<75 segundos`) y Evolucion Gobernada (`PR #1 -> PR #2`)

Todo cambio generado por desarrolladores o agentes en **Cloud Workstations + Antigravity** atraviesa Pull Requests auditados en paralelo por **Cloud Build (2nd Gen)** usando la identidad dedicada `cymbal-health-cicd-sa`:

* **`PR #1` (Despliegue Limpio de `v2.0`):** Incorpora el agente ADK, el Data Store de Vertex AI Search y la defensa de 5 anillos respetando el estandar Least Privilege -> aprueba los 4 gates y despliega sin caida.
* **`PR #2` (Cambio Vulnerable Bloqueado y Auto-Remediado):** Si un cambio posterior introduce `roles/editor`, `INGRESS_TRAFFIC_ALL`, paquetes con CVE, SQL Injection (`CWE-89`) o SSRF (`CWE-918`), es detenido en `<75s` por **Artifact Registry**, **Wiz Code (`wizcli v1.83.0`)** y **Google CodeMender (`cm --plain`)** antes de tocar produccion.

---

## 3. Observabilidad, Deteccion en Tiempo Real y FinOps

* **Defensa de 5 Anillos y Trazabilidad Forense:** Model Armor inspecciona prompts directos, fragmentos RAG de Vertex AI Search (anti-Indirect Prompt Injection) y salidas del modelo; Cloud DLP enmascara PII colombiana (`COLOMBIA_CDC_NUMBER`); Cloud Logging emite JSON estructurado con `traceId`, `callerIp` y consulta UDM para **Google SecOps**.
* **Deteccion de Desvios Manuales ("ClickOps"):** Un sink dedicado (`cymbal-health-wiz-audit-sink`) transmite eventos `Admin Activity` y `Data Access` (incluyendo `discoveryengine.googleapis.com`) hacia **Pub/Sub (`cymbal-health-wiz-audit-topic`)** para **Wiz Cloud**.
* **Eficiencia Financiera:** Escalamiento `min_instance_count = 0` (*Scale-to-Zero*) combinado con **Committed Use Discounts (CUDs)** y limites de gasto por usuario en el pool compartido de tokens de **Gemini Enterprise**.
