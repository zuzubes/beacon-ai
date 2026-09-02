"""
Minimal PDF export helpers for Beacon AI final analysis reports.
"""

from __future__ import annotations

import io
import re

from textwrap import wrap


def _escape(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _linkify(value: str) -> str:
    def repl(match: re.Match[str]) -> str:
        label = _escape(match.group(1))
        url = _escape(match.group(2))
        return f'<a href="{url}" color="#4F46E5">{label}</a>'

    value = _escape(value)
    return re.sub(r"\[([^\]]+)\]\(([^)]+)\)", repl, value)


def _fallback_pdf(markdown_text: str, title: str) -> bytes:
    lines = [title, ""]
    for raw_line in markdown_text.splitlines():
        line = raw_line.strip()
        if not line:
            lines.append("")
            continue
        if line.startswith("# "):
            lines.extend(["", line[2:].upper(), ""])
            continue
        if line.startswith("## "):
            lines.extend(["", line[3:], ""])
            continue
        if line.startswith("### "):
            lines.append(line[4:])
            continue
        if line.startswith("- "):
            lines.append(f"• {line[2:]}")
            continue
        if line.startswith("|"):
            lines.append(line.replace("|", "  "))
            continue
        lines.extend(wrap(line, width=90))

    def _escape_pdf(text: str) -> str:
        return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    lines_per_page = 44
    pages = [lines[i : i + lines_per_page] for i in range(0, len(lines), lines_per_page)] or [[]]
    output = io.BytesIO()
    output.write(b"%PDF-1.4\n")
    xref_positions = []
    page_object_numbers = []
    content_object_numbers = []
    catalog_obj = 1
    pages_obj = 2
    font_obj = 3
    next_obj = 4

    def _write_obj(data: bytes) -> None:
        xref_positions.append(output.tell())
        output.write(data)

    _write_obj(b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n")
    page_object_numbers = list(range(next_obj, next_obj + len(pages)))
    next_obj += len(pages)
    content_object_numbers = list(range(next_obj, next_obj + len(pages)))
    next_obj += len(pages)
    kids = " ".join(f"{obj} 0 R" for obj in page_object_numbers)
    _write_obj(f"2 0 obj << /Type /Pages /Kids [{kids}] /Count {len(pages)} >> endobj\n".encode("utf-8"))
    _write_obj(b"3 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n")
    for page_obj, content_obj, page_lines in zip(page_object_numbers, content_object_numbers, pages):
        stream_lines = [
            "BT",
            "/F1 12 Tf",
            "72 770 Td",
        ]
        first = True
        for line in page_lines:
            safe = _escape_pdf(line)
            if first:
                stream_lines.append(f"({safe}) Tj")
                first = False
            else:
                stream_lines.append("0 -14 Td")
                stream_lines.append(f"({safe}) Tj")
        stream_lines.append("ET")
        stream = "\n".join(stream_lines).encode("utf-8")
        _write_obj(
            (
                f"{page_obj} 0 obj << /Type /Page /Parent {pages_obj} 0 R /MediaBox [0 0 612 792] "
                f"/Resources << /Font << /F1 {font_obj} 0 R >> >> /Contents {content_obj} 0 R >> endobj\n"
            ).encode("utf-8")
        )
        _write_obj(
            (
                f"{content_obj} 0 obj << /Length {len(stream)} >> stream\n"
            ).encode("utf-8")
            + stream
            + b"\nendstream endobj\n"
        )

    xref_start = output.tell()
    output.write(f"xref\n0 {next_obj}\n".encode("utf-8"))
    output.write(b"0000000000 65535 f \n")
    for pos in xref_positions:
        output.write(f"{pos:010d} 00000 n \n".encode("utf-8"))
    output.write(
        b"trailer << /Size "
        + str(next_obj).encode("utf-8")
        + b" /Root 1 0 R >>\nstartxref\n"
        + str(xref_start).encode("utf-8")
        + b"\n%%EOF"
    )
    return output.getvalue()


def markdown_to_pdf_bytes(markdown_text: str, title: str) -> bytes:
    try:
        from reportlab.lib import colors  # type: ignore
        from reportlab.lib.enums import TA_LEFT  # type: ignore
        from reportlab.lib.pagesizes import letter  # type: ignore
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet  # type: ignore
        from reportlab.lib.units import inch  # type: ignore
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle  # type: ignore
    except Exception:  # noqa: BLE001
        return _fallback_pdf(markdown_text, title)

    def _table_from_lines(lines: list[str], styles: dict[str, ParagraphStyle]) -> Table | None:
        cleaned = [line.strip() for line in lines if line.strip()]
        if len(cleaned) < 2:
            return None
        header = [cell.strip() for cell in cleaned[0].strip("|").split("|")]
        rows = []
        for line in cleaned[2:]:
            rows.append([cell.strip() for cell in line.strip("|").split("|")])
        data = [[Paragraph(_linkify(cell), styles["table_cell"]) for cell in header]]
        for row in rows:
            data.append([Paragraph(_linkify(cell), styles["table_cell"]) for cell in row])
        table = Table(data, repeatRows=1, hAlign="LEFT")
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EEF2FF")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#0F172A")),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                    ("LEADING", (0, 0), (-1, -1), 10.5),
                    ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#CBD5E1")),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.white),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 5),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        return table

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=0.65 * inch,
        rightMargin=0.65 * inch,
        topMargin=0.65 * inch,
        bottomMargin=0.65 * inch,
        title=title,
        author="Beacon AI",
    )

    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="ReportTitle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=22,
            leading=26,
            textColor=colors.HexColor("#0F172A"),
            alignment=TA_LEFT,
            spaceAfter=12,
        )
    )
    styles.add(
        ParagraphStyle(
            name="SectionHeading",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=17,
            textColor=colors.HexColor("#0F172A"),
            spaceBefore=10,
            spaceAfter=6,
        )
    )
    styles.add(
        ParagraphStyle(
            name="SubHeading",
            parent=styles["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=13,
            textColor=colors.HexColor("#334155"),
            spaceBefore=8,
            spaceAfter=4,
        )
    )
    styles.add(
        ParagraphStyle(
            name="BodyTextBeacon",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=9.2,
            leading=13,
            textColor=colors.HexColor("#334155"),
            spaceAfter=5,
        )
    )
    styles.add(
        ParagraphStyle(
            name="BulletBeacon",
            parent=styles["BodyTextBeacon"],
            leftIndent=12,
            firstLineIndent=-8,
        )
    )
    styles.add(
        ParagraphStyle(
            name="TableCell",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=8.3,
            leading=10,
            textColor=colors.HexColor("#334155"),
        )
    )

    story = []
    lines = markdown_text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        if not line.strip():
            story.append(Spacer(1, 0.08 * inch))
            i += 1
            continue

        if line.startswith("# "):
            story.append(Paragraph(_linkify(line[2:].strip()), styles["ReportTitle"]))
            i += 1
            continue
        if line.startswith("## "):
            story.append(Spacer(1, 0.04 * inch))
            story.append(Paragraph(_linkify(line[3:].strip()), styles["SectionHeading"]))
            i += 1
            continue
        if line.startswith("### "):
            story.append(Paragraph(_linkify(line[4:].strip()), styles["SubHeading"]))
            i += 1
            continue

        if line.startswith("|") and i + 1 < len(lines) and lines[i + 1].strip().startswith("|"):
            table_lines = [line]
            i += 1
            while i < len(lines) and lines[i].strip().startswith("|"):
                table_lines.append(lines[i])
                i += 1
            table = _table_from_lines(table_lines, styles)
            if table is not None:
                story.append(table)
                story.append(Spacer(1, 0.08 * inch))
            continue

        if line.startswith("- "):
            story.append(Paragraph(f"• {_linkify(line[2:].strip())}", styles["BulletBeacon"]))
            i += 1
            continue

        numbered = re.match(r"^\d+\.\s+(.*)$", line)
        if numbered:
            story.append(Paragraph(_linkify(numbered.group(1)), styles["BulletBeacon"]))
            i += 1
            continue

        story.append(Paragraph(_linkify(line), styles["BodyTextBeacon"]))
        i += 1

    def _footer(canvas, doc_obj):  # noqa: ANN001
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#64748B"))
        canvas.drawString(doc_obj.leftMargin, 0.42 * inch, "Beacon AI")
        canvas.drawRightString(
            letter[0] - doc_obj.rightMargin,
            0.42 * inch,
            f"Page {doc_obj.page}",
        )
        canvas.restoreState()

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buffer.getvalue()
