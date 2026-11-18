# Protocolo Normativo PROT-TELE-2026-05: Telemedicina, Reserva de Historia Clinica y Ley 1581

- **Codigo de Protocolo:** `PROT-TELE-2026-05`
- **Alcance:** Todos los servicios de Telesalud, Ordenamiento Digital y Asistentes Clinicos — Cymbal Health IPS
- **Marco Regulatorio Colombiano:** Ley 1419 de 2010, Resolucion 2654 de 2019 (Ministerio de Salud), Ley 23 de 1981 y Ley Estatutaria 1581 de 2012 (Proteccion de Datos Personales).

## 1. Reglas de Privacidad y Tratamiento de Datos Sensibles de Salud
1. **Enmascaramiento Obligatorio de Identificadores Nacionales:** Ningun asistente automatizado, canal de soporte ni consulta analitica puede almacenar, transmitir a modelos generativos externos o mostrar el numero completo de **Cedula de Ciudadania (`CC`)**, tarjeta de identidad o medio de pago. Todo identificador detectado debe ser sustituido en linea por marcadores de anonimizacion (`[REDACTED_COLOMBIA_CC]`).
2. **Segregacion de Expedientes bajo Reserva Legal (`confidential = 1`):** Los casos sometidos a Comite de Bioetica, juntas periciales o proteccion especial permanecen excluidos de la vista operativa `clinical_orders_public_v`. Los sistemas de consulta automatizada operan bajo rol de base de datos estrictamente `SELECT` sobre `clinical_orders_public_v`.
3. **Validez de la Orden Medica Emitida por Telemedicina:** Toda autorizacion generada en modalidad de telemedicina interactiva debe incluir nombre completo del profesional, numero de **Registro Medico Nacional (RETHUS)**, codificacion **CUPS / CIE-10** y sello de verificacion criptografica conforme a la Ley 527 de 1999.
4. **Custodia y Retencion:** La historia clinica electronica y sus anexos diagnosticos deben conservarse de forma integra y privada por un periodo minimo de **15 anos** contados a partir de la ultima atencion.
