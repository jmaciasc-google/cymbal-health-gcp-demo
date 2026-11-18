---
name: evaluate-codemender-finding
description: Evaluates, verifies in an isolated sandbox with zero false positives, and patches CWE-89 SQLi and CWE-918 SSRF findings discovered by Google CodeMender (CM_PLAIN=true cm) in Cymbal Health PR #2.
---

# Skill: Evaluate CodeMender Finding (Cymbal Health)

## Proposito
Guia a **Google Antigravity** durante la verificacion empirica en sandbox y el parcheo seguro de las vulnerabilidades introducidas en el **PR `#2`** (`demo/pr2-vulnerable-change`), garantizando `0% Falsos Positivos` y cumplimiento estricto de `CONTEXT.md`.

## Variables de Entorno Requeridas
- `CM_PLAIN=true` (o bandera `--plain` para salida limpia sin emojis ni glifos Unicode).

---

## Procedimiento Paso a Paso

### Paso 1: Deteccion Semantica (`cm --plain find`)
1. Leer `CONTEXT.md` y `.codemender/config.yaml`.
2. Ejecutar escaneo diferencial sobre la rama del PR `#2`:
   ```bash
   CM_PLAIN=true cm --plain find . --diff
   ```
3. Identificar los dos hallazgos criticos en Python:
   - `CM-SQLI-001` (`CWE-89` SQL Injection en `backend/db.py` `search_orders`).
   - `CM-SSRF-002` (`CWE-918` Server-Side Request Forgery en `backend/app.py` `POST /api/orders/{order_code}/notify-eps`).

### Paso 2: Verificacion Empirica en Sandbox (`cm --plain verify`)
```bash
CM_PLAIN=true cm --plain verify
```
- **PoC `CM-SQLI-001`:** `?q=' OR '1'='1 --` evade `confidential = 0` y expone `ORD-2026-9901` y `ORD-2026-9902`.
- **PoC `CM-SSRF-002`:** `callback_url="http://169.254.169.254/computeMetadata/v1/instance/service-accounts/default/token"` alcanza el endpoint de metadatos sin validacion de host ni esquema.

### Paso 3: Sintesis del Parche y Regresion (`cm --plain fix`)
1. Reemplazar la concatenacion SQL por consulta parametrizada (`?`) sobre `clinical_orders_public_v`.
2. Proteger `notify-eps` exigiendo `https://`, dominios EAPB autorizados y rechazo de IPs privadas, loopback y link-local (`169.254.0.0/16`).
3. Ejecutar la suite completa de pruebas:
   ```bash
   pytest tests/ -q
   ```
