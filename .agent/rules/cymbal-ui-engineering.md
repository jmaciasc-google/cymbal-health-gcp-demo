---
trigger: always_on
description: Estandar obligatorio de UX minimalista (0% emojis, modales limpios sin botones de prueba) y seguridad Least Privilege para Cymbal Health.
---

# Regla de Ingenieria y UX: Cymbal Health

Al crear o modificar codigo en este repositorio, cumple estrictamente estas directrices:

1. **Cero Emojis (`0% Emojis`):**
   - Nunca insertes emojis Unicode en plantillas HTML, hojas CSS, scripts JS, codigo Python, logs o archivos Markdown.
   - Emplea unicamente insignias CSS limpias e iconos `<svg>` geometricos en linea.

2. **Interfaz Hospitalaria Minimalista y Limpia:**
   - Manten las etiquetas de tarjetas KPI entre **3 y 5 palabras**.
   - Toda interaccion secundaria (formularios, visores PDF o futuros asistentes clinicos) debe abrirse en un modal limpio (`class="modal-backdrop"`, `role="dialog"`, `aria-modal="true"`).
   - Nunca agregues botones de prueba rapida, chips de ataques simulados ni conmutadores de depuracion en la interfaz de usuario.

3. **Minimo Privilegio Estricto y Cero Credenciales Estaticas:**
   - Prohibido usar `GEMINI_API_KEY`, `GOOGLE_API_KEY`, llaves JSON o contrasenas SQL en texto plano; utiliza exclusivamente **Application Default Credentials (ADC)**, **IAM Database Authentication** y tokens **OIDC** entre microservicios.
   - Usa consultas SQL 100% parametrizadas sobre `clinical_orders_public_v` y contenedores no-root (`UID 10001:10001`).
