"""Hospital-grade pure-Python structured PDF-1.4 medical authorization generator.

Renders an authentic Colombian diagnostic & clinical procedure authorization form
(`CYMBAL HEALTH IPS - RED DE DIAGNOSTICO ESPECIALIZADO`) using geometric rectangles,
shaded section headers, crisp grid lines, CUPS/CIE-10 clinical coding table,
word-wrapped medical justification, patient preparation box, and a stylized geometric
physician signature block with SHA-256 verification seal. Zero external binary
dependencies and zero cloud/infrastructure jargon on the medical document.
"""

from __future__ import annotations

import hashlib
import textwrap
from typing import Any


def _pdf_escape(text: str) -> str:
    clean = (
        str(text or "")
        .encode("latin-1", errors="replace")
        .decode("latin-1")
        .replace("\\", "\\\\")
        .replace("(", "\\(")
        .replace(")", "\\)")
    )
    return clean


class _PdfCanvas:
    """Minimal structured PDF-1.4 content stream builder (US Letter: 612 x 792 pt)."""

    def __init__(self) -> None:
        self.ops: list[str] = []

    def rect_fill_stroke(
        self,
        x: float,
        y: float,
        w: float,
        h: float,
        *,
        fill_rgb: tuple[float, float, float] | None = None,
        stroke_rgb: tuple[float, float, float] | None = None,
        line_width: float = 0.75,
    ) -> None:
        self.ops.append("q")
        self.ops.append(f"{line_width:.2f} w")
        if fill_rgb is not None and stroke_rgb is not None:
            self.ops.append(f"{fill_rgb[0]:.3f} {fill_rgb[1]:.3f} {fill_rgb[2]:.3f} rg")
            self.ops.append(f"{stroke_rgb[0]:.3f} {stroke_rgb[1]:.3f} {stroke_rgb[2]:.3f} RG")
            self.ops.append(f"{x:.2f} {y:.2f} {w:.2f} {h:.2f} re B")
        elif fill_rgb is not None:
            self.ops.append(f"{fill_rgb[0]:.3f} {fill_rgb[1]:.3f} {fill_rgb[2]:.3f} rg")
            self.ops.append(f"{x:.2f} {y:.2f} {w:.2f} {h:.2f} re f")
        elif stroke_rgb is not None:
            self.ops.append(f"{stroke_rgb[0]:.3f} {stroke_rgb[1]:.3f} {stroke_rgb[2]:.3f} RG")
            self.ops.append(f"{x:.2f} {y:.2f} {w:.2f} {h:.2f} re S")
        self.ops.append("Q")

    def line(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        *,
        rgb: tuple[float, float, float] = (0.80, 0.84, 0.89),
        line_width: float = 0.6,
    ) -> None:
        self.ops.append("q")
        self.ops.append(f"{line_width:.2f} w")
        self.ops.append(f"{rgb[0]:.3f} {rgb[1]:.3f} {rgb[2]:.3f} RG")
        self.ops.append(f"{x1:.2f} {y1:.2f} m {x2:.2f} {y2:.2f} l S")
        self.ops.append("Q")

    def text(
        self,
        x: float,
        y: float,
        value: str,
        *,
        font: str = "F1",
        size: float = 9.0,
        rgb: tuple[float, float, float] = (0.07, 0.11, 0.18),
    ) -> None:
        escaped = _pdf_escape(value)
        self.ops.append("BT")
        self.ops.append(f"/{font} {size:.2f} Tf")
        self.ops.append(f"{rgb[0]:.3f} {rgb[1]:.3f} {rgb[2]:.3f} rg")
        self.ops.append(f"1 0 0 1 {x:.2f} {y:.2f} Tm")
        self.ops.append(f"({escaped}) Tj")
        self.ops.append("ET")

    def paragraph(
        self,
        x: float,
        y_top: float,
        text_val: str,
        *,
        width_chars: int = 96,
        max_lines: int = 4,
        leading: float = 12.5,
        font: str = "F1",
        size: float = 8.8,
        rgb: tuple[float, float, float] = (0.12, 0.16, 0.23),
    ) -> None:
        wrapped = textwrap.wrap(str(text_val or "").strip(), width=width_chars)[:max_lines]
        for idx, line_str in enumerate(wrapped):
            self.text(x, y_top - idx * leading, line_str, font=font, size=size, rgb=rgb)

    def draw_medical_cross_emblem(self, x: float, y: float) -> None:
        # White rounded-feel emblem tile with geometric medical cross
        self.rect_fill_stroke(x, y, 32, 32, fill_rgb=(1.0, 1.0, 1.0))
        self.rect_fill_stroke(x + 13, y + 6, 6, 20, fill_rgb=(0.08, 0.36, 0.72))
        self.rect_fill_stroke(x + 6, y + 13, 20, 6, fill_rgb=(0.08, 0.36, 0.72))

    def draw_physician_signature_stroke(self, x: float, y: float) -> None:
        # Crisp stylized ink signature curve using cubic Bezier operators
        self.ops.append("q")
        self.ops.append("1.15 w")
        self.ops.append("0.09 0.26 0.55 RG")
        self.ops.append(
            f"{x:.1f} {y:.1f} m "
            f"{x + 18:.1f} {y + 18:.1f} {x + 30:.1f} {y - 6:.1f} {x + 48:.1f} {y + 12:.1f} c "
            f"{x + 60:.1f} {y + 22:.1f} {x + 68:.1f} {y - 2:.1f} {x + 86:.1f} {y + 9:.1f} c "
            f"{x + 104:.1f} {y + 16:.1f} {x + 122:.1f} {y + 2:.1f} {x + 148:.1f} {y + 6:.1f} c S"
        )
        self.ops.append("0.75 w")
        self.ops.append(f"{x + 12:.1f} {y - 2:.1f} m {x + 135:.1f} {y + 3:.1f} l S")
        self.ops.append("Q")

    def build_bytes(self) -> bytes:
        return "\n".join(self.ops).encode("latin-1")


def build_hospital_medical_pdf(order: dict[str, Any]) -> bytes:
    """Builds a complete precision-formatted PDF-1.4 Colombian clinical authorization order."""
    c = _PdfCanvas()

    navy = (0.06, 0.20, 0.42)
    accent_blue = (0.10, 0.45, 0.91)
    section_bg = (0.93, 0.96, 0.99)
    subtle_bg = (0.975, 0.982, 0.992)
    border_gray = (0.76, 0.81, 0.87)
    muted_text = (0.36, 0.42, 0.50)
    dark_text = (0.07, 0.11, 0.18)

    order_code = str(order.get("order_code", "ORD-2026-1041"))
    folio = str(order.get("folio_number") or f"AUT-{order_code.replace('ORD-', '')}")
    status = str(order.get("status", "AUTORIZADA")).upper()
    priority = str(order.get("priority", "MEDIA")).upper()
    cups_code = str(order.get("cups_code") or "895001")
    cie10_code = str(order.get("cie10_code") or "Z018 - Control clinico especializado")
    eps_name = str(order.get("eps_name") or "EPS Sanitas - Regimen Contributivo")
    physician = str(
        order.get("attending_physician") or "Dr. Alejandro Morales Pineda (RM 110284719)"
    )
    prep_text = str(
        order.get("patient_preparation")
        or (
            "Presentarse 20 minutos antes de la hora programada con documento de identidad "
            "original y orden medica vigente. Seguir indicaciones clinicas del servicio."
        )
    )
    seal_hash = hashlib.sha256(
        f"{order_code}|{folio}|{cups_code}|{physician}".encode("utf-8")
    ).hexdigest()[:24].upper()

    # Outer page frame
    c.rect_fill_stroke(34, 36, 544, 720, stroke_rgb=border_gray, line_width=0.9)

    # Top Institutional Banner
    c.rect_fill_stroke(34, 686, 544, 70, fill_rgb=navy)
    c.rect_fill_stroke(34, 682, 544, 4, fill_rgb=accent_blue)
    c.draw_medical_cross_emblem(48, 705)

    c.text(88, 731, "CYMBAL HEALTH IPS - RED DE DIAGNOSTICO ESPECIALIZADO", font="F2", size=10.0, rgb=(1, 1, 1))
    c.text(88, 716, "NIT: 901.482.310-6  |  Codigo Habilitacion REPS: 1100109482-01", font="F1", size=8.2, rgb=(0.84, 0.90, 0.98))
    c.text(88, 703, "Direccion Medica Nacional - Sistema Integrado de Ordenamiento Clinico", font="F1", size=8.0, rgb=(0.76, 0.85, 0.96))

    # Right Folio Card inside Header
    c.rect_fill_stroke(414, 694, 152, 54, fill_rgb=(0.98, 0.99, 1.0))
    c.text(422, 735, "AUTORIZACION MEDICA", font="F2", size=7.8, rgb=navy)
    c.text(422, 721, f"Orden: {order_code}", font="F2", size=9.4, rgb=accent_blue)
    c.text(422, 709, f"Folio: {folio}", font="F3", size=7.8, rgb=dark_text)
    status_rgb = (0.07, 0.45, 0.20) if status == "AUTORIZADA" else (0.65, 0.36, 0.02)
    c.text(422, 698, f"Estado: {status}", font="F2", size=7.8, rgb=status_rgb)

    # SECTION 1: Patient & Affiliation Box (y = 582..670)
    c.rect_fill_stroke(46, 650, 520, 18, fill_rgb=section_bg, stroke_rgb=border_gray, line_width=0.7)
    c.text(54, 656, "1. IDENTIFICACION DEL AFILIADO Y ENTIDAD RESPONSABLE DE PAGO", font="F2", size=8.5, rgb=navy)
    c.rect_fill_stroke(46, 582, 520, 68, stroke_rgb=border_gray, line_width=0.7)
    c.line(46, 616, 566, 616, rgb=border_gray)
    c.line(235, 582, 235, 650, rgb=border_gray)
    c.line(415, 582, 415, 650, rgb=border_gray)

    c.text(54, 637, "PACIENTE (PROTECCION LEY 1581)", font="F2", size=7.0, rgb=muted_text)
    c.text(54, 624, str(order.get("patient_alias", "N/A")), font="F2", size=9.2, rgb=dark_text)

    c.text(243, 637, "DOCUMENTO DE IDENTIDAD", font="F2", size=7.0, rgb=muted_text)
    c.text(243, 624, str(order.get("document_masked", "CC ***0000")), font="F3", size=9.0, rgb=dark_text)

    c.text(423, 637, "FECHA Y HORA EMISION", font="F2", size=7.0, rgb=muted_text)
    c.text(423, 624, str(order.get("created_at", "2026-11-21 08:00 COT")), font="F1", size=8.6, rgb=dark_text)

    c.text(54, 603, "ASEGURADOR / PLAN DE BENEFICIOS (EAPB)", font="F2", size=7.0, rgb=muted_text)
    c.text(54, 590, eps_name, font="F1", size=8.8, rgb=dark_text)

    c.text(243, 603, "SEDE REGIONAL ASIGNADA", font="F2", size=7.0, rgb=muted_text)
    c.text(243, 590, f"Cymbal IPS Sede {order.get('center_city', 'Bogota')}", font="F1", size=8.8, rgb=dark_text)

    c.text(423, 603, "AMBITO DE ATENCION", font="F2", size=7.0, rgb=muted_text)
    c.text(423, 590, "Ambulatorio / Telemedicina", font="F1", size=8.6, rgb=dark_text)

    # SECTION 2: Clinical Coding & Procedure Table (CUPS / CIE-10) (y = 472..570)
    c.rect_fill_stroke(46, 552, 520, 18, fill_rgb=section_bg, stroke_rgb=border_gray, line_width=0.7)
    c.text(54, 558, "2. ORDENAMIENTO MEDICO Y CODIFICACION NORMATIVA (CUPS / CIE-10)", font="F2", size=8.5, rgb=navy)
    c.rect_fill_stroke(46, 472, 520, 80, stroke_rgb=border_gray, line_width=0.7)

    # Table sub-header row
    c.rect_fill_stroke(46, 534, 520, 18, fill_rgb=subtle_bg, stroke_rgb=border_gray, line_width=0.6)
    c.line(112, 500, 112, 552, rgb=border_gray)
    c.line(152, 500, 152, 552, rgb=border_gray)
    c.line(392, 500, 392, 552, rgb=border_gray)
    c.line(500, 500, 500, 552, rgb=border_gray)
    c.line(46, 500, 566, 500, rgb=border_gray)

    c.text(52, 540, "COD. CUPS", font="F2", size=7.2, rgb=muted_text)
    c.text(118, 540, "CANT", font="F2", size=7.2, rgb=muted_text)
    c.text(158, 540, "PROCEDIMIENTO / TECNOLOGIA EN SALUD", font="F2", size=7.2, rgb=muted_text)
    c.text(398, 540, "ESPECIALIDAD", font="F2", size=7.2, rgb=muted_text)
    c.text(506, 540, "PRIORIDAD", font="F2", size=7.2, rgb=muted_text)

    c.text(54, 515, cups_code, font="F3", size=9.2, rgb=navy)
    c.text(126, 515, "01", font="F3", size=9.0, rgb=dark_text)
    proc_lines = textwrap.wrap(str(order.get("procedure_name", "")), width=38)[:2]
    if len(proc_lines) == 1:
        c.text(158, 515, proc_lines[0], font="F2", size=8.6, rgb=dark_text)
    elif len(proc_lines) >= 2:
        c.text(158, 520, proc_lines[0], font="F2", size=8.3, rgb=dark_text)
        c.text(158, 508, proc_lines[1], font="F2", size=8.3, rgb=dark_text)

    c.text(397, 515, str(order.get("specialty", ""))[:23], font="F1", size=8.0, rgb=dark_text)
    prio_rgb = (0.72, 0.14, 0.12) if priority == "ALTA" else navy
    c.text(508, 515, priority, font="F2", size=8.5, rgb=prio_rgb)

    # CIE-10 diagnosis strip at bottom of Section 2
    c.text(54, 483, "DIAGNOSTICO PRINCIPAL CIE-10:", font="F2", size=7.6, rgb=muted_text)
    c.text(192, 483, cie10_code, font="F2", size=8.6, rgb=dark_text)
    c.text(415, 483, "VIGENCIA ORDEN: 60 DIAS", font="F2", size=7.4, rgb=muted_text)

    # SECTION 3: Clinical Summary & Medical Justification (y = 358..460)
    c.rect_fill_stroke(46, 442, 520, 18, fill_rgb=section_bg, stroke_rgb=border_gray, line_width=0.7)
    c.text(54, 448, "3. RESUMEN DE HISTORIA CLINICA Y JUSTIFICACION DE PERTINENCIA MEDICA", font="F2", size=8.5, rgb=navy)
    c.rect_fill_stroke(46, 358, 520, 84, stroke_rgb=border_gray, line_width=0.7)
    c.paragraph(
        56,
        426,
        str(order.get("clinical_summary", "")),
        width_chars=94,
        max_lines=5,
        leading=13.0,
        font="F1",
        size=8.8,
        rgb=dark_text,
    )

    # SECTION 4: Patient Preparation & Instructions (y = 256..346)
    c.rect_fill_stroke(46, 328, 520, 18, fill_rgb=section_bg, stroke_rgb=border_gray, line_width=0.7)
    c.text(54, 334, "4. INDICACIONES CLINICAS Y PREPARACION PREVIA DEL PACIENTE", font="F2", size=8.5, rgb=navy)
    c.rect_fill_stroke(46, 256, 520, 72, fill_rgb=subtle_bg, stroke_rgb=border_gray, line_width=0.7)
    c.paragraph(
        56,
        312,
        prep_text,
        width_chars=94,
        max_lines=4,
        leading=13.0,
        font="F1",
        size=8.6,
        rgb=dark_text,
    )

    # SECTION 5: Digital Physician Signature & Institutional Verification (y = 92..242)
    c.rect_fill_stroke(46, 224, 520, 18, fill_rgb=section_bg, stroke_rgb=border_gray, line_width=0.7)
    c.text(54, 230, "5. FIRMA MEDICA DIGITAL Y VALIDACION INSTITUCIONAL", font="F2", size=8.5, rgb=navy)
    c.rect_fill_stroke(46, 94, 520, 130, stroke_rgb=border_gray, line_width=0.7)
    c.line(312, 94, 312, 224, rgb=border_gray)

    # Left Signature Box
    c.draw_physician_signature_stroke(74, 172)
    c.line(64, 152, 290, 152, rgb=border_gray, line_width=0.8)
    c.text(64, 138, physician, font="F2", size=8.5, rgb=dark_text)
    c.text(64, 125, f"Especialidad: {order.get('specialty', 'Medicina Especializada')}", font="F1", size=8.0, rgb=muted_text)
    c.text(64, 112, "Firma electronica certificada - Ley 527 de 1999", font="F1", size=7.5, rgb=muted_text)

    # Right Verification & Audit Seal Box
    c.rect_fill_stroke(326, 156, 226, 54, fill_rgb=subtle_bg, stroke_rgb=border_gray, line_width=0.6)
    c.text(334, 197, "SELLO DE VERIFICACION CRIPTOGRAFICA", font="F2", size=7.3, rgb=navy)
    c.text(334, 183, f"SHA-256: {seal_hash}", font="F3", size=7.6, rgb=dark_text)
    c.text(334, 170, "Validado en Registro Nacional REPS / MinSalud", font="F1", size=7.6, rgb=muted_text)

    c.text(326, 138, "LINEA DE PROGRAMACION DE CITAS:", font="F2", size=7.4, rgb=muted_text)
    c.text(326, 125, "Bogota (601) 742-8900  |  Nacional 01-8000-914820", font="F1", size=8.0, rgb=dark_text)
    c.text(326, 112, "Portal Pacientes: autorizaciones.cymbal-health.co", font="F1", size=7.8, rgb=accent_blue)

    # Legal Footer
    c.line(46, 78, 566, 78, rgb=border_gray, line_width=0.5)
    c.text(
        46,
        64,
        "CONFIDENCIALIDAD MEDICA: Este soporte clinico contiene datos sensibles protegidos por la Ley Estatutaria 1581 de 2012",
        font="F1",
        size=7.1,
        rgb=muted_text,
    )
    c.text(
        46,
        52,
        "y la Ley 23 de 1981 (Etica Medica). Prohibida su reproduccion o divulgacion sin autorizacion expresa del titular o autoridad.",
        font="F1",
        size=7.1,
        rgb=muted_text,
    )

    stream_bytes = c.build_bytes()

    objects: list[bytes] = [
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n",
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n",
        (
            b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Resources << /Font << /F1 4 0 R /F2 5 0 R /F3 6 0 R >> >> "
            b"/Contents 7 0 R >>\nendobj\n"
        ),
        b"4 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>\nendobj\n",
        b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>\nendobj\n",
        b"6 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Courier /Encoding /WinAnsiEncoding >>\nendobj\n",
        (
            f"7 0 obj\n<< /Length {len(stream_bytes)} >>\nstream\n".encode("ascii")
            + stream_bytes
            + b"\nendstream\nendobj\n"
        ),
    ]

    pdf = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for obj in objects:
        offsets.append(len(pdf))
        pdf.extend(obj)

    xref_pos = len(pdf)
    pdf.extend(f"xref\n0 {len(offsets)}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for off in offsets[1:]:
        pdf.extend(f"{off:010d} 00000 n \n".encode("ascii"))

    pdf.extend(
        (
            f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\n"
            f"startxref\n{xref_pos}\n%%EOF\n"
        ).encode("ascii")
    )
    return bytes(pdf)
