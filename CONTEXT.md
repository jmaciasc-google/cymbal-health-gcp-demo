# CONTEXT.md — Cymbal Health Clinical Authorizations Portal (v1.0)

## 1. Proposito del Sistema
**Cymbal Health** es una plataforma hospitalaria de gestion de autorizaciones clinicas, codificacion normativa **CUPS / CIE-10** y emision de soportes medicos firmados en PDF sobre **Google Cloud**.

---

## 2. Estandar Obligatorio de UX y Construccion de Software
1. **Cero Emojis (`0% Emojis`):** Prohibido el uso de emojis Unicode en HTML, CSS, JavaScript, Python, logs, comentarios o documentacion Markdown. Solo se utilizan indicadores CSS tipograficos e iconos SVG geometricos monocromaticos.
2. **Texto Minimo en Pantalla:** La vista principal mantiene etiquetas de resumen de **3 a 5 palabras** y una tabla operativa limpia sin bloques densos de texto.
3. **Interaccion por Modales:** La emision de nuevas autorizaciones, la visualizacion de ordenes PDF y cualquier extension futura deben abrirse en ventanas modales accesibles (`role="dialog"`, `aria-modal="true"`) sin saturar ni recargar la vista principal, y sin botones de prueba ni conmutadores artificiales en la interfaz clinica.

---

## 3. Arquitectura Base (`v1.0`) e Invariantes de Minimo Privilegio
1. **Perimetro y Computo Serverless:**
   - **Global External Application Load Balancer + Cloud Armor WAF** delante de **Cloud Run (`cymbal-health-web-portal`)** configurado con `INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER`.
2. **Identidades Dedicadas y Cero Credenciales Estaticas (`0% Static Keys`):**
   - Service Account dedicada `cymbal-health-portal-sa` (sin roles primitivos `roles/owner`, `roles/editor`, `roles/viewer` ni Service Accounts predeterminadas).
   - Autenticacion 100% basada en **Application Default Credentials (ADC)** e **IAM Database Authentication** hacia **Cloud SQL for PostgreSQL 15** (`cymbal-health-pg-main`, solo IP privada) y **Cloud Storage** privado (`public_access_prevention = enforced`, `uniform_bucket_level_access = true`).
3. **Proteccion de Datos Sensibles (Ley 1581 de 2012):**
   - Consultas SQL 100% parametrizadas sobre la vista autorizada `clinical_orders_public_v` (`confidential = 0`).
   - Enmascaramiento automatico de documentos de identidad (`CC ***XXXX`) y contenedores sin privilegios (`USER 10001:10001` con `HEALTHCHECK`).
