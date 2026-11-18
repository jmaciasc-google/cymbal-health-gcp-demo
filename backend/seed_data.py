"""Synthetic Colombian healthcare clinical authorization dataset for Cymbal Health IPS.

All records use synthetic patient identifiers masked under Ley 1581 de 2012,
authentic Colombian CUPS procedure codes, and CIE-10 diagnostic classifications.
"""

from __future__ import annotations

from typing import Any

SEED_CLINICAL_ORDERS: list[dict[str, Any]] = [
    {
        "order_code": "ORD-2026-1041",
        "folio_number": "AUT-2026-008941",
        "patient_alias": "M. Rodriguez Vargas",
        "document_masked": "CC ***4821",
        "eps_name": "EPS Sanitas - Contributivo",
        "specialty": "Cardiologia Clinica",
        "cups_code": "881234",
        "cie10_code": "I10X - Hipertension esencial primaria",
        "procedure_name": "Ecocardiograma Transtoracico Doppler Color",
        "center_city": "Bogota",
        "attending_physician": "Dr. Alejandro Morales Pineda (RM 110284719)",
        "status": "AUTORIZADA",
        "priority": "ALTA",
        "support_pdf_object": "soportes/2026/11/ORD-2026-1041.pdf",
        "created_at": "2026-11-21 08:15 COT",
        "clinical_summary": (
            "Paciente en seguimiento cardiovascular por hipertension arterial estadio II con "
            "disnea de medianos esfuerzos. Se solicita ecocardiograma transtoracico Doppler "
            "para cuantificar fraccion de eyeccion ventricular izquierda y descartar hipertrofia."
        ),
        "patient_preparation": (
            "Presentarse 20 minutos antes de la cita con documento de identidad original y "
            "ultimo electrocardiograma de 12 derivaciones. No requiere ayuno previo. "
            "Continuar medicacion antihipertensiva habitual segun prescripcion."
        ),
        "confidential": 0,
    },
    {
        "order_code": "ORD-2026-1042",
        "folio_number": "AUT-2026-008942",
        "patient_alias": "C. Restrepo Giraldo",
        "document_masked": "CC ***9104",
        "eps_name": "EPS Sura - Contributivo",
        "specialty": "Medicina Interna",
        "cups_code": "903895",
        "cie10_code": "E785 - Hiperlipidemia mixta en estudio",
        "procedure_name": "Panel Metabolico Basal y Perfil Lipidico Completo",
        "center_city": "Pereira",
        "attending_physician": "Dra. Camila Henao Salazar (RM 66104829)",
        "status": "PENDIENTE_FIRMA",
        "priority": "MEDIA",
        "support_pdf_object": "soportes/2026/11/ORD-2026-1042.pdf",
        "created_at": "2026-11-21 09:05 COT",
        "clinical_summary": (
            "Control trimestral de programa de riesgo cardiometabolico en sede Eje Cafetero. "
            "Requiere determinacion serica de colesterol LDL, HDL, trigliceridos, glucemia "
            "basal y creatinina para ajuste de meta terapeutica con estatinas."
        ),
        "patient_preparation": (
            "Ayuno estricto de 10 a 12 horas (solo se permite ingesta moderada de agua pura). "
            "Evitar consumo de alcohol o ejercicio fisico intenso durante las 24 horas previas "
            "a la puncion venosa en laboratorio clinico."
        ),
        "confidential": 0,
    },
    {
        "order_code": "ORD-2026-1043",
        "folio_number": "AUT-2026-008943",
        "patient_alias": "L. Gomez Castellanos",
        "document_masked": "CC ***3319",
        "eps_name": "Compensar EPS - Contributivo",
        "specialty": "Neurologia Clinica",
        "cups_code": "883101",
        "cie10_code": "G439 - Cefalea cronica con signos de alerta",
        "procedure_name": "Resonancia Nuclear Magnetica de Cerebro Simple",
        "center_city": "Bogota",
        "attending_physician": "Dr. Mauricio Villamizar Duarte (RM 110391504)",
        "status": "AUTORIZADA",
        "priority": "ALTA",
        "support_pdf_object": "soportes/2026/11/ORD-2026-1043.pdf",
        "created_at": "2026-11-21 10:22 COT",
        "clinical_summary": (
            "Cuadro de cefalea hemicraneana progresiva de 6 semanas de evolucion asociada a "
            "fosfenos transitorios. Examen neurologico focal sin deficit motor; se indica "
            "neuroimagen por resonancia magnetica simple para descartar lesion estructural."
        ),
        "patient_preparation": (
            "Retirar todos los objetos metalicos, joyas, relojes y protesis removibles antes "
            "de ingresar al resonador. Diligenciar encuesta de seguridad magnetica (ausencia "
            "de marcapasos no condicional o implante ferromagnetico). No requiere ayuno."
        ),
        "confidential": 0,
    },
    {
        "order_code": "ORD-2026-1044",
        "folio_number": "AUT-2026-008944",
        "patient_alias": "A. Vargas Ospina",
        "document_masked": "CC ***7740",
        "eps_name": "EPS Sura - Contributivo",
        "specialty": "Oncologia Clinica",
        "cups_code": "921801",
        "cie10_code": "C349 - Neoplasia pulmonar en estadificacion",
        "procedure_name": "Tomografia PET-CT Corporal Total con 18F-FDG",
        "center_city": "Medellin",
        "attending_physician": "Dra. Juliana Arboleda Mejia (RM 051298431)",
        "status": "EN_REVISION",
        "priority": "ALTA",
        "support_pdf_object": "soportes/2026/11/ORD-2026-1044.pdf",
        "created_at": "2026-11-22 11:40 COT",
        "clinical_summary": (
            "Solicitud respaldada por Junta Medica Oncologica con confirmacion histopatologica "
            "previa para estadificacion metabolica ganglionar mediastinica y definicion de "
            "esquema quirurgico versus terapia sistemica dirigida."
        ),
        "patient_preparation": (
            "Ayuno minimo de 6 horas antes de la inyeccion del radiofarmaco. Glucemia capilar "
            "previa obligatoria menor a 180 mg/dL. Dieta baja en carbohidratos y reposo fisico "
            "durante las 24 horas previas al estudio."
        ),
        "confidential": 0,
    },
    {
        "order_code": "ORD-2026-1045",
        "folio_number": "AUT-2026-008945",
        "patient_alias": "D. Morales Caicedo",
        "document_masked": "CC ***6052",
        "eps_name": "Nueva EPS - Subsidiado",
        "specialty": "Endocrinologia",
        "cups_code": "890343",
        "cie10_code": "E119 - Diabetes mellitus tipo 2 alto riesgo renal",
        "procedure_name": "Junta Interdisciplinaria y Autorizacion Terapia Biologica",
        "center_city": "Cali",
        "attending_physician": "Dr. Andres Felipe Velasco (RM 76094182)",
        "status": "AUTORIZADA",
        "priority": "MEDIA",
        "support_pdf_object": "soportes/2026/11/ORD-2026-1045.pdf",
        "created_at": "2026-11-22 14:10 COT",
        "clinical_summary": (
            "Falla terapeutica documentada a doble esquema oral con HbA1c en 8.9% y albuminuria "
            "persistente. Cumple criterios de escalonamiento farmacologico y registro en "
            "Cuenta de Alto Costo sin cobro de cuota moderadora."
        ),
        "patient_preparation": (
            "Asistir con bitacora de glucometrias de los ultimos 14 dias y resultados vigentes "
            "de hemoglobina glicosilada y tasa de filtracion glomerular. Dispensacion sujeta a "
            "cadena de frio controlada entre 2 C y 8 C."
        ),
        "confidential": 0,
    },
    # Restricted records excluded from clinical_orders_public_v (Ley 1581 / Bioethics Committee)
    {
        "order_code": "ORD-2026-9901",
        "folio_number": "RES-2026-000101",
        "patient_alias": "RESERVA_LEY_1581_A",
        "document_masked": "CC 1020754321 [RESERVA LEGAL]",
        "eps_name": "Fondo Especial Reservado",
        "specialty": "Junta Medica Bioetica",
        "cups_code": "890502",
        "cie10_code": "Z719 - Expediente clinico protegido",
        "procedure_name": "Auditoria Historia Clinica Protegida Nivel 4",
        "center_city": "Bogota",
        "attending_physician": "Comite Nacional de Etica Medica (RM 11000011)",
        "status": "RESTRINGIDA",
        "priority": "ALTA",
        "support_pdf_object": "restringido/2026/11/ORD-2026-9901.pdf",
        "created_at": "2026-11-20 18:00 COT",
        "clinical_summary": (
            "REGISTRO SENSIBLE PROTEGIDO LEY 1581: Historia clinica bajo reserva estricta "
            "de comite de etica hospitalaria. Excluida de consultas generales."
        ),
        "patient_preparation": "Acceso exclusivo presencial por auditor medico autorizado.",
        "confidential": 1,
    },
    {
        "order_code": "ORD-2026-9902",
        "folio_number": "RES-2026-000102",
        "patient_alias": "RESERVA_LEY_1581_B",
        "document_masked": "CC 79845120 [RESERVA LEGAL]",
        "eps_name": "Fondo Especial Reservado",
        "specialty": "Comite Pericial Clinico",
        "cups_code": "890503",
        "cie10_code": "Z048 - Dictamen medico reservado",
        "procedure_name": "Dictamen Pericial Interdisciplinario bajo Reserva",
        "center_city": "Pereira",
        "attending_physician": "Junta Pericial Regional (RM 66000219)",
        "status": "RESTRINGIDA",
        "priority": "ALTA",
        "support_pdf_object": "restringido/2026/11/ORD-2026-9902.pdf",
        "created_at": "2026-11-20 19:30 COT",
        "clinical_summary": (
            "REGISTRO SENSIBLE PROTEGIDO LEY 1581: Dictamen pericial reservado excluido "
            "de la vista autorizada clinical_orders_public_v."
        ),
        "patient_preparation": "Documento reservado bajo custodia legal.",
        "confidential": 1,
    },
]

DEFAULT_PREFILLED_ORDER: dict[str, str] = {
    "patient_alias": "P. Cardenas Montoya",
    "document_masked": "1032489120",
    "eps_name": "EPS Sanitas - Contributivo",
    "specialty": "Cardiologia Clinica",
    "center_city": "Bogota",
    "cups_code": "895001",
    "cie10_code": "I499 - Arritmia cardiaca en estudio",
    "procedure_name": "Monitoreo Electrocardiografico Continuo Holter 24 Horas",
    "priority": "ALTA",
    "attending_physician": "Dra. Natalia Gomez Arango (RM 110492810)",
    "clinical_summary": (
        "Episodios recurrentes de palpitaciones rapidas y presincope documentados en "
        "consulta especializada. ECG de reposo sin bloqueo AV agudo; se ordena registro "
        "ambulatorio continuo de 24 horas para estratificacion arritmica."
    ),
    "patient_preparation": (
        "Asistir con ropa comoda de dos piezas, piel limpia en torax sin cremas ni lociones "
        "y traer reporte de electrocardiograma basal previo. Mantener actividades cotidianas "
        "registrando cualquier sintoma en la bitacora del equipo."
    ),
}
