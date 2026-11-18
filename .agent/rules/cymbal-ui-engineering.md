---
trigger: always_on
description: Reglas obligatorias de UX minimalista (0% emojis, modales limpios sin botones de prueba) y seguridad Least Privilege de 5 anillos para Cymbal Health v2.0.
---

# Regla de Ingenieria y UX: Cymbal Health

Al crear o modificar codigo en `backend/`, `frontend/`, `mcp_backlog_server/`, `Dockerfile` o `terraform/`, cumple sin excepcion estas directrices:

1. **Cero Emojis (`0% Emojis`):**
   - Nunca insertes emojis Unicode en plantillas HTML, hojas CSS, scripts JS, respuestas de API, logs (`CM_PLAIN=true`), pruebas o archivos Markdown.
   - Usa exclusivamente etiquetas CSS tipograficas e iconos `<svg>` geometricos en linea (`stroke="currentColor"`).

2. **Interfaz Minimalista Basada en Modales y Sin Botones de Prueba:**
   - Manten las tarjetas KPI de la vista principal entre **3 y 5 palabras**.
   - Toda interaccion secundaria —incluyendo el asistente `cymbal-clinical-agent`— debe abrirse en un modal limpio (`class="modal-backdrop"`, `role="dialog"`, `aria-modal="true"`).
   - Queda prohibido agregar chips de ataque, botones de prueba rapida o conmutadores de demostracion dentro de la interfaz clinica.

3. **Autenticacion Sin Llaves (`0% Static Keys`) y Dual-Datastore Least Privilege:**
   - Prohibido declarar `GEMINI_API_KEY`, `GOOGLE_API_KEY` o archivos JSON de credenciales.
   - Invoca Vertex AI Gemini, Vertex AI Search (`discoveryengine`), Model Armor, Cloud DLP, Cloud Storage y Secret Manager unicamente mediante **Application Default Credentials (ADC)**.
   - El agente `cymbal-clinical-agent` solo ejecuta herramientas tipadas (`get_order_status` con `SELECT` parametrizado sobre `clinical_orders_public_v` y `search_clinical_protocol_rag` con `roles/discoveryengine.viewer` sobre `cymbal-health-clinical-protocols-ds`).

4. **Defensa de 5 Anillos y Prevencion de SQLi / SSRF:**
   - Pasa todo prompt por `inspect_and_sanitize_prompt`, todo chunk RAG por `sanitize_rag_chunks` y toda salida por `sanitize_model_response`.
   - Cualquier integracion HTTP saliente debe exigir `https://`, lista blanca explicita de dominios EAPB y bloqueo estricto de `169.254.169.254`, `metadata.google.internal`, loopback y RFC1918.
