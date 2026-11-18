# Politica Corporativa de Seguridad de la Informacion, Minimo Privilegio e IA Responsable

**Organizacion:** Cymbal Health -- Oficina del CISO y Cumplimiento Normativo  
**Marcos Regulatorios:** ISO/IEC 27001:2022 - Ley Estatutaria 1581 de 2012 (Proteccion de Datos Personales en Colombia)  
**Alcance:** Obligatorio para todo codigo de aplicacion, infraestructura Terraform, pipelines CI/CD y agentes de IA (incluidos **Gemini Enterprise** y **Antigravity**).

---

## 1. Las 6 Reglas Innegociables de Minimo Privilegio (*Least Privilege End-to-End*)

Ningun Pull Request ni despliegue a produccion sera aprobado si incumple cualquiera de los siguientes controles:

1. **Prohibicion Absoluta de Roles Primitivos y Service Accounts Predeterminadas:**
   * Queda estrictamente prohibido otorgar `roles/owner`, `roles/editor` o `roles/viewer`, asi como emplear la cuenta predeterminada de Compute Engine (`*-compute@developer.gserviceaccount.com`) o la cuenta global heredada de Cloud Build.
2. **Segregacion Estricta de Identidades (`1 Componente = 1 Service Account`):**
   * `cymbal-health-portal-sa`: Exclusiva para el portal web Tier 1. Sin acceso a Vertex AI, Discovery Engine ni Secret Manager.
   * `cymbal-health-agent-sa`: Exclusiva para el agente clinico ADK Tier 2. Acceso de **solo lectura** a la vista `clinical_orders_public_v` y al Data Store de protocolos clinicos `cymbal-health-clinical-protocols-ds` (`roles/discoveryengine.viewer`); prohibido insertar, modificar o eliminar registros medicos o archivos en Cloud Storage.
   * `cymbal-health-mcp-sa`: Exclusiva para el servidor MCP de backlog. Acceso restringido unicamente al secreto `cymbal-health-github-pat`.
   * `cymbal-health-cicd-sa`: Exclusiva para Cloud Build. Permiso `roles/iam.serviceAccountUser` acotado unicamente a las tres Service Accounts de aplicacion de Cymbal Health.
3. **IAM a Nivel de Recurso (*Resource-Level Bindings*):**
   * Todo permiso sobre buckets de Cloud Storage (`soportes` y `protocols`), secretos de Secret Manager, invocacion OIDC de servicios Cloud Run, repositorios de Artifact Registry, topicos de Pub/Sub e impersonacion de Service Accounts debe declararse directamente sobre el recurso especifico, nunca a nivel global del proyecto.
4. **Cero Credenciales Estaticas (`0% API Keys`, `0% JSON Keys`, `0% Contrasenas SQL`):**
   * Toda autenticacion hacia Vertex AI, Vertex AI Search (`discoveryengine`), Model Armor, Cloud DLP, Cloud Storage y Secret Manager debe usar **Application Default Credentials (ADC)**.
   * La conexion a Cloud SQL debe usar **IAM Database Authentication** (`CLOUD_IAM_SERVICE_ACCOUNT`) y el agente `cymbal-clinical-agent` solo puede consultar `clinical_orders_public_v` (`GRANT SELECT` exclusivo; `REVOKE INSERT, UPDATE, DELETE, TRUNCATE`).
   * Se exige el cumplimiento de las politicas organizacionales `constraints/iam.disableServiceAccountKeyCreation` y `constraints/run.allowedIngress`.
5. **Consultas Parametrizadas y Contenedores Endurecidos:**
   * Prohibida toda interpolacion de cadenas (`f-strings` o concatenacion) en sentencias SQL (`CWE-89`) y llamadas HTTP salientes sin validacion de destino (`CWE-918` hacia `169.254.169.254`).
   * Todo contenedor debe ejecutarse sin privilegios de superusuario (`USER appuser`, `UID 10001:10001`).
6. **Defensa Runtime de 5 Anillos y Proteccion de Datos Personales (Ley 1581 de 2012):**
   * Todo prompt de usuario, fragmento recuperado desde **Vertex AI Search (`cymbal-health-clinical-protocols-ds`)** y respuesta final del modelo debe atravesar en linea (`<30ms`) **Google Cloud Model Armor** (`PI_AND_JAILBREAK`, `MALICIOUS_URI`, `SDP`, `RAI`) y **Sensitive Data Protection (Cloud DLP)** para redactar numeros de Cedula de Ciudadania Colombiana (`[REDACTED_COLOMBIA_CC]`) y tarjetas de pago antes de llegar al modelo fundacional.

---

## 2. Auditoria Continua y Trazabilidad Forense

* **Registros Data Access Obligatorios:** Se mantienen activos los registros `ADMIN_READ`, `DATA_READ` y `DATA_WRITE` en Cloud Audit Logs sobre Vertex AI, Discovery Engine (`discoveryengine.googleapis.com`), Model Armor, Cloud DLP, Cloud SQL y Secret Manager para garantizar visibilidad completa de `callerIp`, `principalEmail` y `traceId`.
* **Respuesta ante Desvios en Consola:** Cualquier cambio manual fuera de Terraform ("ClickOps") es transmitido en tiempo real via `Cloud Audit Logs -> Pub/Sub` hacia **Wiz Cloud** y **Google SecOps**, debiendo revertirse de inmediato mediante infraestructura como codigo.
