# CONTEXT.md — Cymbal Health Clinical Authorizations Portal & AI Auditor (v3.0)

## 1. Proposito del Sistema
**Cymbal Health** es una plataforma hospitalaria de gestion de autorizaciones clinicas, codificacion normativa **CUPS / CIE-10**, emision de soportes medicos firmados en PDF y auditoria asistida por IA segura (`cymbal-clinical-agent`) sobre **Google Cloud**.

---

## 2. Estandar Obligatorio de UX y Construccion de Software
1. **Cero Emojis (`0% Emojis`):** Prohibido el uso de emojis Unicode en HTML, CSS, JavaScript, Python, logs, comentarios o documentacion Markdown. Solo se utilizan indicadores CSS tipograficos e iconos SVG geometricos monocromaticos.
2. **Texto Minimo en Pantalla:** La vista principal mantiene etiquetas de resumen de **3 a 5 palabras** y una tabla operativa limpia sin bloques densos de texto.
3. **Interaccion por Modales:** La emision de nuevas autorizaciones (`#modal-new-order`), la visualizacion de ordenes PDF (`#modal-order-detail`) y el asistente clinico de auditoria (`#modal-clinical-agent`) se abren en ventanas modales accesibles (`role="dialog"`, `aria-modal="true"`) sin chips precargados ni botones de ataques simulados.

---

## 3. Arquitectura de Minimo Privilegio y Defensa IA en 5 Anillos
1. **Perimetro y Computo Serverless de Dos Capas:**
   - **Tier 1 (`cymbal-health-web-portal-v1`):** Global External Application Load Balancer + Cloud Armor WAF delante de Cloud Run (`INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER`), incluye webhook asegurador `POST /api/orders/{order_code}/notify-eps` restringido a HTTPS y lista blanca `ALLOWED_EPS_WEBHOOK_HOSTS`.
   - **Tier 2 (`cymbal-health-clinical-agent-v3`):** Microservicio interno (`--ingress=internal`, `--no-allow-unauthenticated`) construido con `google-adk==2.14.1` y `google-genai==2.34.0` (`gemini-2.5-flash`, `vertexai=True`, `max_output_tokens=1024`, `thinking_budget=0`).
2. **Identidades Dedicadas y Cero Credenciales Estaticas (`0% Static Keys`):**
   - Autenticacion 100% basada en **Application Default Credentials (ADC)**, **IAM Database Authentication** hacia Cloud SQL PostgreSQL 15, **OAuth2 ADC** hacia Vertex AI Search (`cymbal-health-clinical-protocols-ds`) y **OIDC ID Tokens** (`Authorization: Bearer <id_token>`) entre Tier 1 y Tier 2.
3. **Defensa IA en 5 Anillos y Cumplimiento Ley 1581 de 2012:**
   - **Anillo 1a y 1b:** Model Armor + reglas hospitalarias (`<30ms`, HTTP `403` ante Jailbreak, SQLi, volcados masivos `BULK_EXFILTRATION_DUMP`, enumeracion de esquemas y SSRF) + sanitizacion de fragmentos RAG (`sanitize_rag_chunks`).
   - **Anillo 2 y 3:** Cloud DLP en linea (`[REDACTED_COLOMBIA_CC]`, `[REDACTED_PAYMENT_CARD]`, `[REDACTED_EMAIL]`), politica SQL `Deny-by-Default` (`LIMIT 3`) sobre `clinical_orders_public_v` (`confidential = 0`) y redaccion de recursos internos (`[INTERNAL_RESOURCE_REDACTED]`).
   - **Anillo 4 y 5:** Salto autenticado OIDC (`X-Cymbal-Internal-Hop: 1`), descriptor A2A (`/.well-known/agent.json`, `/api/agent/card`) y telemetria UDM para Google SecOps (`/api/security/telemetry`).
