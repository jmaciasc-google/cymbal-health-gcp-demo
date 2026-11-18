# CONTEXT.md — Cymbal Health Architecture, Dual-Datastore RAG & 5-Ring Security (v2.0)

## 1. Proposito del Sistema
**Cymbal Health** es una plataforma hospitalaria de autorizaciones clinicas, codificacion normativa **CUPS / CIE-10**, emision de soportes PDF firmados y asistencia clinica gobernada con **Google Agent Development Kit (ADK)** sobre **Google Cloud**.

---

## 2. Estandar Obligatorio de UX y Construccion de Software
1. **Cero Emojis (`0% Emojis`):** Prohibido el uso de caracteres Unicode de emoji en HTML, CSS, JavaScript, Python, logs (`CM_PLAIN=true`), comentarios o documentacion Markdown. Solo se emplean indicadores CSS tipograficos e iconos SVG geometricos monocromaticos.
2. **Interfaz Clinica Limpia y Basada en Modales:**
   - La vista principal conserva etiquetas de resumen de **3 a 5 palabras** y una tabla operativa despejada.
   - Crear una orden, visualizar un soporte PDF o consultar a **`cymbal-clinical-agent`** abre siempre un modal accesible (`role="dialog"`, `aria-modal="true"`).
   - Queda prohibido incluir botones de prueba rapida, chips de ataques simulados o conmutadores de depuracion en la interfaz de usuario.

---

## 3. Arquitectura Well-Architected y Dual-Datastore Read-Only (`v2.0`)

```text
[Profesionales de Salud / Auditores IPS]
        |
        v  HTTPS (TLS Gestionado + IP Global)
[Global External Application Load Balancer + Cloud Armor WAF]
        |
        v  INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER
[Tier 1 Cloud Run: cymbal-health-web-portal] (SA: cymbal-health-portal-sa, UID 10001)
        |
        +---> [Cloud SQL PostgreSQL 15: cymbal-health-pg-main] (IP Privada + IAM DB Auth)
        +---> [Cloud Storage Privado: cymbal-health-soportes-*] (Ordenes PDF CUPS/CIE-10)
        |
        v  Token OIDC firmado + INGRESS_TRAFFIC_INTERNAL_ONLY
[Tier 2 Cloud Run: cymbal-health-clinical-agent] (Google ADK, SA: cymbal-health-agent-sa)
        |
        +---> [Anillos 1 y 2: Model Armor (<30 ms) + Cloud DLP Ley 1581]
        +---> [Datastore A: Vertex AI Search (cymbal-health-clinical-protocols-ds, roles/discoveryengine.viewer)]
        +---> [Datastore B: Cloud SQL Vista clinical_orders_public_v (Rol cymbal_agent_readonly SELECT-only)]
        +---> [Modelo: Vertex AI Gemini via ADC (0% API Keys)]
```

---

## 4. Defensa en 5 Anillos e Invariantes de Minimo Privilegio
1. **Anillo 1 (Model Armor `<30 ms`):** Inspecciona el prompt del usuario (`sanitizeUserPrompt`), analiza cada fragmento recuperado desde **Vertex AI Search** contra *Indirect Prompt Injection* y sanea la respuesta final (`sanitizeModelResponse`).
2. **Anillo 2 (Cloud DLP — Ley 1581):** Anonimiza en linea documentos nacionales (`COLOMBIA_CDC_NUMBER` -> `[REDACTED_COLOMBIA_CC]`), tarjetas de pago y correos antes de contactar a RAG o al modelo.
3. **Anillo 3 (Aislamiento ADK):** `system_instruction` inmutable y herramientas tipadas Pydantic (`get_order_status`, `search_clinical_protocol_rag`) sin generacion libre de SQL.
4. **Anillo 4 (Minimo Privilegio e Identidades):** `1 Componente = 1 Service Account` (`cymbal-health-{portal,agent,mcp,cicd}-sa`), `0%` roles primitivos (`roles/owner`, `roles/editor`, `roles/viewer`), `0%` llaves estaticas, contenedores no-root (`UID 10001:10001`) y bloqueo de SSRF hacia rangos privados o `169.254.169.254`.
5. **Anillo 5 (Trazabilidad Forense):** Registros JSON estructurados en **Cloud Logging** con `traceId`, `callerIp`, `principalEmail` y consulta UDM directa hacia **Google SecOps**.
