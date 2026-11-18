# Estandar de Experiencia de Usuario (UX) y Construccion de Software -- Cymbal Health

**Organizacion:** Cymbal Health -- Ingenieria de Plataforma y Diseno de Producto  
**Cumplimiento Automatico:** Codificado en `CONTEXT.md`, `.agent/rules/` y validado en `pytest` / Cloud Build.

---

## 1. Principios de Diseno de Interfaz Clinica Minimalista

Todo modulo web, componente nuevo o asistente agentico construido para **Cymbal Health** (ya sea por desarrolladores humanos o mediante agentes en **Gemini Enterprise** y **Antigravity**) debe respetar sin excepcion estas cuatro reglas visuales:

1. **Cero Emojis (`0% Emojis` en Absoluto):**
   * Queda prohibido incluir emojis Unicode o pictogramas decorativos en HTML, CSS, JavaScript, respuestas del agente clinico, codigo Python, plantillas Terraform, logs de consola (`CM_PLAIN=true`), mensajes de commit y documentacion tecnica.
   * Los estados clinicos y de seguridad se comunican unicamente mediante **insignias tipograficas CSS** de alto contraste (`AUTORIZADA`, `PENDIENTE`, `EN AUDITORIA`, `BLOQUEADO`) e **iconografia geometrica SVG monocromatica en linea (`stroke="currentColor"`)**.
2. **Cero Botones de Prueba o Artefactos Demo en la Interfaz:**
   * Prohibido incluir selectores artificiales de version (`v1/v2`), botones de simulacion de ataque, chips preconfigurados de Prompt Injection o visores de demostracion en el portal clinico. La interfaz debe ser 100% indistinguible de un sistema hospitalario real en produccion.
3. **Densidad Minima de Texto y Ordenes Medicas Hospitalarias Reales:**
   * La vista principal muestra unicamente barra superior institucional, indicadores operativos concisos (**3 a 5 palabras maximo** por etiqueta) y la tabla estructurada de ordenes clinicas con codigos **CUPS** y **CIE-10**.
   * Todo soporte descargable debe renderizarse como una **orden medica hospitalaria PDF vectorial** con membrete institucional, NIT/REPS sinteticos, recuadros estructurados de afiliado, ordenamiento CUPS/CIE-10, preparacion del paciente y firma medica digital, sin exponer rutas internas `gs://`.
4. **Arquitectura de Interaccion Basada en Modales / Pop-ups:**
   * Toda accion secundaria abre en una **ventana modal limpia (`role="dialog"`, `aria-modal="true"`)** con cierre por tecla `Escape` y preservacion del contexto de la tabla inferior:
     * **Modal 1 (`v1.0` y `v2.0`):** Formulario de nueva orden clinica pre-diligenciado con valores clinicos validos listos para radicar en un clic.
     * **Modal 2 (`v1.0` y `v2.0`):** Detalle estructurado de orden medica y acceso directo al soporte PDF hospitalario.
     * **Modal 3 (`v2.0` unicamente):** Asistente Clinico-Administrativo ADK (`Asistente clinico IA`) limpio bajo demanda, respaldado por Vertex AI Search y Model Armor + Cloud DLP.

---

## 2. Sistema Visual y Accesibilidad

* **Paleta Corporativa:** Fondo base `#F8FAFC`, superficies `#FFFFFF`, bordes sutiles `#E2E8F0`, texto primario `#0F172A`, texto secundario `#475569`, acento clinico primario `#1A73E8` y estados semanticos sobrios (`#137333` exito, `#B06000` advertencia, `#C5221F` bloqueo).
* **Tipografia:** `Inter` / `Google Sans` / `system-ui` para interfaz y `Roboto Mono` / `monospace` para identificadores de orden (`ORD-2026-...`), codigos CUPS/CIE-10 y `traceId`.
* **Accesibilidad:** Contraste minimo WCAG AA (`4.5:1`), navegacion completa por teclado y foco visible en controles interactivos.

---

## 3. Evolucion Gobernada por Ramas (`main` -> `PR #1` -> `PR #2`)

* **Rama `main` (`v1.0` Base Pura):** Contiene exclusivamente el portal transaccional de autorizaciones clinicas sin dependencias ni endpoints de agentes IA.
* **`PR #1` (`v2.0` Agente Seguro con Plan Mode):** Agrega el agente ADK, el Data Store de protocolos CUPS en Vertex AI Search y los 5 anillos de defensa runtime pasando el 100% de las validaciones en Cloud Build.
* **`PR #2` (Control de Regresiones DevSecOps):** Cualquier intento posterior de relajar permisos IAM o introducir vulnerabilidades de codigo es bloqueado automaticamente antes del merge.
