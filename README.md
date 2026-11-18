# Cymbal Health — Plataforma de Autorizaciones Clinicas (`v1.0`)

Portal clinico-administrativo de **Cymbal Health IPS** para gestion de ordenamiento medico (**CUPS / CIE-10**) y emision de soportes de autorizacion en formato PDF estructurado sobre **Google Cloud**.

---

## 1. Arquitectura de Produccion (`v1.0`)

- **Borde Global:** Global External Application Load Balancer + Google Cloud Armor WAF (`sqli`, `xss`, `rce`, `lfi` y control de tasa).
- **Aplicacion Serverless:** Google Cloud Run (`cymbal-health-web-portal`) con `INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER`, contenedor sin root (`UID 10001:10001`) y Service Account dedicada (`cymbal-health-portal-sa`).
- **Persistencia Privada:** Cloud SQL for PostgreSQL 15 (`cymbal-health-pg-main`) con IP privada exclusiva e **IAM Database Authentication**, mas bucket privado de **Cloud Storage** (`public_access_prevention = enforced` y `uniform_bucket_level_access = true`) accedido mediante **Application Default Credentials (ADC)**.
- **Cumplimiento Ley 1581 de 2012:** Consultas parametrizadas sobre la vista autorizada `clinical_orders_public_v` y enmascaramiento de documentos nacionales (`CC ***XXXX`).

---

## 2. Ejecucion Local y Pruebas

```bash
# Ejecutar pruebas funcionales, de seguridad, PDF estructurado y cero emojis
pytest tests/ -q

# Iniciar el portal Cymbal Health v1.0 localmente
uvicorn backend.app:app --port 8080
```
