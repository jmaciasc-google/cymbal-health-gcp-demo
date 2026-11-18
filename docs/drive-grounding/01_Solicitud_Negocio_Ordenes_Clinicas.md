# Solicitud de Negocio: Asistente Clinico-Administrativo para Triaje de Ordenes y Protocolos CUPS

**Organizacion:** Cymbal Health -- Direccion de Operaciones Clinicas y Telesalud  
**Codigo de Iniciativa:** CH-2026-ORD-042  
**Referencia de Backlog Objetivo:** GitHub Issue `#42` (via servidor gobernado `github-backlog-mcp`)  
**Clasificacion de Datos:** Informacion Clinica y Datos Personales Sensibles (Ley Estatutaria 1581 de 2012)

---

## 1. Contexto Operativo Actual (`Cymbal Health v1.0` en `main`)

La plataforma **Cymbal Health Web Portal (`v1.0`)** opera en produccion procesando ordenes medicas ambulatorias con codigos **CUPS** y diagnosticos **CIE-10**, autorizaciones de laboratorio de alta complejidad y soportes clinicos hospitalarios en formato PDF vectorial para afiliados en Colombia.

Hoy los coordinadores medicos enfrentan tres cuellos de botella operativos:
1. **Tiempo elevado de revision manual:** Validar la pertinencia clinica entre el codigo CUPS, el diagnostico CIE-10, las guias clinicas vigentes y el soporte adjunto toma en promedio **14 minutos por orden**.
2. **Riesgo de exposicion de datos sensibles:** Consultar notas completas incrementa la exposicion innecesaria de numeros de Cedula de Ciudadania (`CC`) y datos de copago.
3. **Saturacion visual en pantalla:** Los operadores trabajan sobre cientos de ordenes por turno y exigen interfaces limpias sin paneles laterales fijos ni botones de prueba.

---

## 2. Objetivo Funcional (`Evolucion a Cymbal Health v2.0` mediante `PR #1`)

Incorporar un **Asistente Clinico-Administrativo basado en IA Agentica (`cymbal-clinical-agent`)** construido con **Google Agent Development Kit (ADK)** que permita al coordinador medico:

1. Consultar en lenguaje natural el resumen clinico, estado de autorizacion y preparacion del paciente de cualquier orden activa sobre la vista de solo lectura `clinical_orders_public_v` en **Cloud SQL PostgreSQL 15**.
2. Fundamentar cada validacion de codigos **CUPS** y **CIE-10** contra las **6 guias de autorizacion clinica** indexadas en un **Vertex AI Search Data Store (`cymbal-health-clinical-protocols-ds`)** respaldado por el bucket privado `cymbal-health-protocols`.
3. Abrir toda interaccion con el agente exclusivamente dentro de un **modal/pop-up limpio bajo demanda** (`Asistente clinico IA`), sin botones de prueba ni chips de ataque en la interfaz.

---

## 3. Criterios de Aceptacion de Producto y Seguridad

| ID | Dimension | Criterio de Aceptacion Obligatorio |
| :--- | :--- | :--- |
| **CA-01** | **UX Minimalista** | Cero emojis en interfaz, botones, respuestas del agente y registros. Cero botones de demostracion o presets de ataque en UI. |
| **CA-02** | **Interaccion en Modal** | El asistente `cymbal-clinical-agent`, el detalle de orden, el visor de PDF hospitalario y el formulario pre-diligenciado de nueva orden abren siempre en ventana modal superpuesta. |
| **CA-03** | **Dual Datastore Read-Only** | El agente se ejecuta en `INGRESS_TRAFFIC_INTERNAL_ONLY` con `cymbal-health-agent-sa`, accediendo solo con `SELECT` a `clinical_orders_public_v`, `roles/discoveryengine.viewer` sobre `cymbal-health-clinical-protocols-ds` y `roles/storage.objectViewer` en Cloud Storage. |
| **CA-04** | **Cero Llaves Estaticas** | Prohibido el uso de `GEMINI_API_KEY`, llaves JSON de Service Account o contrasenas SQL en codigo o variables de entorno. |
| **CA-05** | **Defensa 5 Anillos Ley 1581** | Inspeccion en linea (`<30ms`) con **Model Armor** (sobre prompt de usuario, chunks recuperados de Vertex AI Search y salida final) y **Cloud DLP** para enmascarar Cedulas Colombianas (`[REDACTED_COLOMBIA_CC]`) antes de invocar al modelo. |
| **CA-06** | **Gobierno de Backlog** | El Product Manager genera el PRD desde **Gemini Enterprise** y registra la historia tecnica en GitHub (`Issue #42`) invocando `github-backlog-mcp` registrado en **Agent Registry**. |

---

## 4. Indicadores de Exito Esperados (KPIs)

* Reduccion del tiempo medio de validacion de ordenes clinicas de **14 minutos a menos de 90 segundos**.
* **0 incidentes** de exposicion de credenciales estaticas o acceso de escritura del agente sobre bases transaccionales o corpus clinicos.
* **0% falsos positivos** en bloqueos de seguridad del pipeline CI/CD gracias a verificacion empirica previa al despliegue.
