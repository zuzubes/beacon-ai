"""Branded PDF export for Beacon AI final analysis reports."""

from __future__ import annotations

import io
import re
from dataclasses import dataclass
from pathlib import Path
from textwrap import wrap

ROOT_DIR = Path(__file__).resolve().parent.parent
LOGO_PATH = ROOT_DIR / "assets" / "beacon-ai-logo.png"


@dataclass(frozen=True)
class ReportContext:
    title: str
    meta: list[tuple[str, str]]
    lead: str


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
        return f'<a href="{url}" color="#1D4ED8">{label}</a>'

    value = _escape(value)
    return re.sub(r"\[([^\]]+)\]\(([^)]+)\)", repl, value)


def _split_report_preamble(report_markdown: str) -> ReportContext:
    lines = [line.rstrip() for line in report_markdown.splitlines()]
    title = "Beacon AI analysis"
    meta: list[tuple[str, str]] = []
    lead_lines: list[str] = []

    for idx, line in enumerate(lines):
        if idx == 0 and line.startswith("# "):
            title = line[2:].strip() or title
            continue
        if line.startswith("**") and "**:" in line:
            match = re.match(r"^\*\*(.+?)\*\*:\s*(.+)$", line)
            if match:
                meta.append((match.group(1).strip(), match.group(2).strip()))
                continue
        if line.startswith("## "):
            break
        if line.strip():
            lead_lines.append(line.strip())

    lead = " ".join(lead_lines).strip()
    return ReportContext(title=title, meta=meta, lead=lead)


def _split_sections(combined_markdown: str) -> list[tuple[str, str]]:
    lines = combined_markdown.splitlines()
    sections: list[tuple[str, str]] = []
    current_title: str | None = None
    buffer: list[str] = []

    for line in lines:
        if line.startswith("## "):
            if current_title is not None:
                sections.append((current_title, "\n".join(buffer).strip()))
            current_title = line[3:].strip()
            buffer = []
            continue
        if current_title is None:
            continue
        buffer.append(line)

    if current_title is not None:
        sections.append((current_title, "\n".join(buffer).strip()))

    return sections


def _section_body(sections: list[tuple[str, str]], name: str) -> str:
    for title, body in sections:
        if title == name:
            return body
    return ""


def _count_items(block: str) -> int:
    return sum(1 for line in block.splitlines() if line.strip().startswith(("- ", "* ")))


def _count_table_rows(block: str) -> int:
    lines = [line for line in block.splitlines() if line.strip().startswith("|")]
    if len(lines) < 3:
        return 0
    return max(0, len(lines) - 2)


def _fallback_pdf(markdown_text: str, title: str) -> bytes:
    try:
        import subprocess
        from functools import lru_cache

        from PIL import Image, ImageDraw, ImageFont, ImageOps
    except Exception:  # noqa: BLE001
        return b""

    context = _split_report_preamble(markdown_text)
    sections = _split_sections(markdown_text)

    def _meta_lookup(label: str) -> str:
        normalized = {key.strip().lower(): value.strip() for key, value in context.meta}
        return normalized.get(label.strip().lower(), "")

    page_w, page_h = 1275, 1650
    cover_bg = "#0F172A"
    cover_bg_2 = "#111D36"
    paper = "#FBF8F1"
    ink = "#0F172A"
    slate = "#475569"
    muted = "#64748B"
    line = "#D8E1EA"
    gold = "#B88A1D"
    blue = "#1D4ED8"
    soft_blue = "#EEF2FF"

    left = 84
    right = 84
    top = 92
    bottom = 86
    content_w = page_w - left - right

    def _safe_fc_match(query: str) -> str | None:
        try:
            import subprocess

            result = subprocess.check_output(
                ["fc-match", "-f", "%{file}\n", query],
                stderr=subprocess.DEVNULL,
                text=True,
            ).strip()
            return result or None
        except Exception:
            return None

    @lru_cache(maxsize=None)
    def _font(name: str, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        path = _safe_fc_match(name)
        if path:
            try:
                return ImageFont.truetype(path, size=size)
            except Exception:
                pass
        return ImageFont.load_default()

    def _fit_lines(draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> list[str]:
        words = re.split(r"\s+", text.strip())
        if not words or words == [""]:
            return [""]
        lines: list[str] = []
        current = words[0]
        for word in words[1:]:
            trial = f"{current} {word}"
            if draw.textlength(trial, font=font) <= max_width:
                current = trial
            else:
                lines.append(current)
                current = word
        lines.append(current)
        return lines

    def _draw_paragraph(
        draw: ImageDraw.ImageDraw,
        x: int,
        y: int,
        text: str,
        font,
        fill: str,
        max_width: int,
        *,
        line_gap: int = 8,
        bullet: str | None = None,
        bullet_color: str | None = None,
        indent: int = 0,
    ) -> int:
        text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
        text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"\1", text)
        text = text.replace("`", "")
        lines = _fit_lines(draw, text, font, max_width - indent)
        line_h = font.size + line_gap if getattr(font, "size", 0) else 16
        if bullet:
            draw.text((x, y), bullet, font=font, fill=bullet_color or fill)
            x += indent
        for idx, line_text in enumerate(lines):
            draw.text((x, y), line_text, font=font, fill=fill)
            y += line_h
        return y

    def _draw_rule(draw: ImageDraw.ImageDraw, y: int, color: str = line, width: int = 1) -> None:
        draw.rectangle([left, y, page_w - right, y + width - 1], fill=color)

    def _wrap_paragraphs(block: str) -> list[str]:
        paras = []
        buffer: list[str] = []
        for raw in block.splitlines():
            stripped = raw.strip()
            if not stripped:
                if buffer:
                    paras.append(" ".join(buffer).strip())
                    buffer = []
                continue
            if stripped in {"---", "***", "___"}:
                if buffer:
                    paras.append(" ".join(buffer).strip())
                    buffer = []
                continue
            buffer.append(stripped)
        if buffer:
            paras.append(" ".join(buffer).strip())
        return paras

    def _parse_table(block: str) -> list[list[str]]:
        rows = []
        for raw in block.splitlines():
            stripped = raw.strip()
            if not stripped.startswith("|"):
                continue
            cells = [cell.strip() for cell in stripped.strip("|").split("|")]
            if cells and all(re.fullmatch(r":?-{3,}:?", cell.replace(" ", "")) for cell in cells):
                continue
            rows.append(cells)
        return rows

    def _table_rows_for_section(body: str) -> list[list[str]]:
        rows: list[list[str]] = []
        current: list[str] = []
        for raw in body.splitlines():
            if raw.strip().startswith("|"):
                current.append(raw)
            else:
                if current:
                    rows.extend(_parse_table("\n".join(current)))
                    current = []
        if current:
            rows.extend(_parse_table("\n".join(current)))
        return rows

    def _estimate_row_height(draw: ImageDraw.ImageDraw, row: list[str], widths: list[int], font) -> int:
        heights = []
        for cell, width in zip(row, widths):
            lines = _fit_lines(draw, cell, font, max(40, width - 16))
            heights.append(len(lines))
        return max(heights, default=1) * (font.size + 7) + 14

    def _render_table(
        draw: ImageDraw.ImageDraw,
        y: int,
        rows: list[list[str]],
        *,
        title: str | None = None,
    ) -> int:
        if not rows:
            return y
        ncols = max(len(r) for r in rows)
        widths = [int(content_w / ncols) for _ in range(ncols)]
        widths[-1] += content_w - sum(widths)
        header_font = _font("Arial:style=Bold", 13)
        body_font = _font("Arial", 12)
        if title:
            y = _draw_paragraph(draw, left, y, title, _font("Arial:style=Bold", 12), gold, content_w, line_gap=6)
            y += 2
        header_h = _estimate_row_height(draw, rows[0], widths, header_font)
        if y + header_h > page_h - bottom:
            return -1
        x0 = left
        x = x0
        y0 = y
        for w, cell in zip(widths, rows[0]):
            draw.rounded_rectangle([x, y0, x + w, y0 + header_h], radius=6, fill=soft_blue, outline=line)
            lines = _fit_lines(draw, cell, header_font, max(40, w - 16))
            text_y = y0 + 6
            for line_text in lines:
                draw.text((x + 8, text_y), line_text, font=header_font, fill=ink)
                text_y += header_font.size + 4
            x += w
        y += header_h
        for row_index, row in enumerate(rows[1:], start=1):
            if len(row) < ncols:
                row = row + [""] * (ncols - len(row))
            row_h = _estimate_row_height(draw, row, widths, body_font)
            if y + row_h > page_h - bottom:
                return -1
            x = x0
            fill = "#FFFFFF" if row_index % 2 else "#FAFCFF"
            for w, cell in zip(widths, row):
                draw.rectangle([x, y, x + w, y + row_h], fill=fill, outline=line)
                lines = _fit_lines(draw, cell, body_font, max(40, w - 16))
                text_y = y + 6
                for line_text in lines:
                    draw.text((x + 8, text_y), line_text, font=body_font, fill=slate)
                    text_y += body_font.size + 4
                x += w
            y += row_h
        return y + 8

    def _new_content_page(page_no: int) -> tuple[Image.Image, ImageDraw.ImageDraw, int]:
        img = Image.new("RGB", (page_w, page_h), paper)
        draw = ImageDraw.Draw(img)
        draw.rectangle([0, 0, page_w, 58], fill="#F3F6FB")
        draw.rectangle([0, 0, 7, page_h], fill=gold)
        draw.text((left, 18), "BEACON AI", font=_font("Arial:style=Bold", 15), fill=ink)
        draw.text((page_w - right - 150, 18), "Executive report", font=_font("Arial", 13), fill=muted)
        draw.text((page_w - right - 28, 18), f"{page_no}", font=_font("Arial:style=Bold", 13), fill=ink)
        _draw_rule(draw, 60)
        draw.text((left, page_h - 40), "Internal executive analysis", font=_font("Arial", 11), fill=muted)
        draw.text((page_w - right - 160, page_h - 40), "Beacon AI", font=_font("Arial:style=Bold", 11), fill=muted)
        return img, draw, 92

    def _render_cover() -> Image.Image:
        img = Image.new("RGB", (page_w, page_h), cover_bg)
        draw = ImageDraw.Draw(img)
        draw.rectangle([0, 0, page_w, 112], fill=cover_bg_2)
        draw.rectangle([0, 0, 16, page_h], fill=gold)
        draw.line([page_w - 190, 118, page_w - 84, 118], fill=blue, width=4)
        logo_y = 78
        if LOGO_PATH.exists():
            try:
                logo = Image.open(LOGO_PATH).convert("RGBA")
                logo = ImageOps.contain(logo, (76, 76))
                img.paste(logo, (left, logo_y), logo)
            except Exception:
                pass
        draw.text((left + 98, 82), "Beacon AI executive analysis", font=_font("Arial:style=Bold", 14), fill="#CBD5E1")
        title_y = 260
        title_lines = _fit_lines(draw, context.title, _font("Times New Roman:style=Bold", 58), 930)
        for line_text in title_lines:
            draw.text((left, title_y), line_text, font=_font("Times New Roman:style=Bold", 58), fill="#FFFFFF")
            title_y += 68
        lead = context.lead or "A concise executive report on macro, mega, and sub-trend movement, designed for leadership review and immediate action."
        lead_y = title_y + 16
        for para in _wrap_paragraphs(lead)[:2]:
            lead_y = _draw_paragraph(draw, left, lead_y, para, _font("Arial", 22), "#E5EEF9", 930, line_gap=8)
            lead_y += 8
        stats = [
            ("Industry / Sector", _meta_lookup("Industry") or ""),
            ("Geographic scope", _meta_lookup("Geographic scope") or ""),
            ("Time range", _meta_lookup("Time range") or ""),
            ("Sections", str(len(sections))),
        ]
        card_y = 1175
        card_w = 255
        card_h = 120
        gap = 24
        for idx, (label, value) in enumerate(stats):
            col = idx % 2
            row = idx // 2
            x = left + col * (card_w + gap)
            y = card_y + row * (card_h + gap)
            draw.rounded_rectangle([x, y, x + card_w, y + card_h], radius=18, fill="#FFFFFF", outline="#223559", width=2)
            draw.text((x + 18, y + 16), label.upper(), font=_font("Arial:style=Bold", 12), fill=muted)
            draw.text((x + 18, y + 52), value or "n/a", font=_font("Arial:style=Bold", 18), fill=ink)
        footer_note = "Prepared for leadership review. The report compresses the trend hierarchy, weak signals, scenarios, and strategic implications into a single decision-ready memo."
        note_y = 1500
        for para in _wrap_paragraphs(footer_note):
            note_y = _draw_paragraph(draw, left, note_y, para, _font("Arial", 20), "#E5EEF9", 930, line_gap=7)
        draw.text((left, 1560), "Beacon AI", font=_font("Arial:style=Bold", 13), fill="#CBD5E1")
        return img

    def _render_section(draw: ImageDraw.ImageDraw, y: int, title_text: str, body: str, page_no: int) -> tuple[int, Image.Image | None, ImageDraw.ImageDraw | None]:
        section_title_font = _font("Times New Roman:style=Bold", 32)
        body_font = _font("Arial", 18)
        small_font = _font("Arial", 16)
        subheading_font = _font("Arial:style=Bold", 16)

        heading_h = 56
        min_block_h = 96
        if y + heading_h + min_block_h > page_h - bottom:
            return -1, None, None
        draw.text((left, y), title_text, font=section_title_font, fill=ink)
        _draw_rule(draw, y + 42, gold, width=4)
        y += 60

        if title_text == "Weak Signals":
            bullets = [line[2:].strip() for line in body.splitlines() if line.strip().startswith(("- ", "* "))]
            for item in bullets or [body]:
                y = _draw_paragraph(draw, left + 8, y, item, small_font, slate, content_w - 16, line_gap=6, bullet="-", indent=18)
                y += 10
            return y, None, None

        if title_text == "Scenarios":
            rows = _parse_table(body)
            if rows and len(rows) > 1:
                new_y = _render_table(draw, y, rows)
                if new_y != -1:
                    return new_y, None, None
        rows = _parse_table(body)
        if rows and len(rows) > 1 and title_text not in {"Weak Signals", "Scenarios"}:
            new_y = _render_table(draw, y, rows)
            if new_y != -1:
                return new_y, None, None

        paras: list[str] = []
        buffer: list[str] = []
        for raw in body.splitlines():
            stripped = raw.strip()
            if not stripped:
                if buffer:
                    paras.append(" ".join(buffer).strip())
                    buffer = []
                continue
            if stripped in {"---", "***", "___"}:
                if buffer:
                    paras.append(" ".join(buffer).strip())
                    buffer = []
                continue
            if stripped.startswith("### "):
                if buffer:
                    paras.append(" ".join(buffer).strip())
                    buffer = []
                y = _draw_paragraph(draw, left, y, stripped[4:].strip(), subheading_font, blue, content_w, line_gap=6)
                y += 4
                continue
            if stripped.startswith("#### "):
                if buffer:
                    paras.append(" ".join(buffer).strip())
                    buffer = []
                y = _draw_paragraph(draw, left, y, stripped[5:].strip(), _font("Arial:style=Bold", 14), muted, content_w, line_gap=5)
                y += 2
                continue
            if stripped.startswith(("- ", "* ")):
                if buffer:
                    paras.append(" ".join(buffer).strip())
                    buffer = []
                y = _draw_paragraph(draw, left + 8, y, stripped[2:].strip(), body_font, slate, content_w - 16, line_gap=7, bullet="-", indent=18)
                y += 6
                continue
            if re.match(r"^\d+\.\s+", stripped):
                if buffer:
                    paras.append(" ".join(buffer).strip())
                    buffer = []
                number_text = re.sub(r"^\d+\.\s+", "", stripped)
                y = _draw_paragraph(draw, left + 8, y, number_text, body_font, slate, content_w - 16, line_gap=7, bullet=stripped.split(".", 1)[0] + ".", indent=22)
                y += 6
                continue
            if stripped.startswith("|"):
                if buffer:
                    paras.append(" ".join(buffer).strip())
                    buffer = []
                table_rows = _parse_table(raw)
                if table_rows and len(table_rows) > 1:
                    new_y = _render_table(draw, y, table_rows)
                    if new_y == -1:
                        return -1, None, None
                    y = new_y
                continue
            buffer.append(stripped)
        if buffer:
            paras.append(" ".join(buffer).strip())

        for para in paras:
            if para:
                y = _draw_paragraph(draw, left, y, para, body_font, slate, content_w, line_gap=8)
                y += 6
        return y, None, None

    cover = _render_cover()
    pages: list[Image.Image] = [cover]
    img, draw, y = _new_content_page(2)

    def _flush_page() -> None:
        nonlocal img, draw, y
        pages.append(img)
        img, draw, y = _new_content_page(len(pages) + 1)

    for section_title, body in sections:
        if y + 120 > page_h - bottom:
            _flush_page()
        new_y, _, _ = _render_section(draw, y, section_title, body, len(pages) + 1)
        if new_y == -1:
            _flush_page()
            new_y, _, _ = _render_section(draw, y, section_title, body, len(pages) + 1)
        y = new_y
        y += 18

    pages.append(img)

    output = io.BytesIO()
    first, *rest = pages
    first.save(output, format="PDF", save_all=True, append_images=rest, resolution=150.0)
    return output.getvalue()


def markdown_to_pdf_bytes(markdown_text: str, title: str) -> bytes:
    try:
        from reportlab.lib import colors  # type: ignore
        from reportlab.lib.enums import TA_LEFT  # type: ignore
        from reportlab.lib.pagesizes import letter  # type: ignore
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet  # type: ignore
        from reportlab.lib.units import inch  # type: ignore
        from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle  # type: ignore
    except Exception:  # noqa: BLE001
        return _fallback_pdf(markdown_text, title)

    context = _split_report_preamble(markdown_text)
    sections = _split_sections(markdown_text)

    def _make_table(rows: list[list[str]], styles: dict[str, ParagraphStyle]) -> Table | None:
        cleaned = [row for row in rows if any(cell.strip() for cell in row)]
        if len(cleaned) < 2:
            return None
        header = cleaned[0]
        body_rows = cleaned[2:] if len(cleaned) > 2 else []
        data = [[Paragraph(_linkify(cell.strip()), styles["TableHeaderBeacon"]) for cell in header]]
        for row in body_rows:
            data.append([Paragraph(_linkify(cell.strip()), styles["TableCellBeacon"]) for cell in row])
        table = Table(data, repeatRows=1, hAlign="LEFT", colWidths=None)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EEF2FF")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#0F172A")),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8.2),
                    ("LEADING", (0, 0), (-1, -1), 10.2),
                    ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#C9D4E3")),
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

    def _parse_table_block(lines: list[str], start: int) -> tuple[list[list[str]] | None, int]:
        table_lines = [lines[start]]
        i = start + 1
        while i < len(lines) and lines[i].strip().startswith("|"):
            table_lines.append(lines[i])
            i += 1
        parsed = [[cell.strip() for cell in row.strip("|").split("|")] for row in table_lines]
        return (parsed if len(parsed) >= 2 else None, i)

    def _body_flowables(markdown_block: str, styles: dict[str, ParagraphStyle]) -> list:
        lines = markdown_block.splitlines()
        flowables = []
        para_buffer: list[str] = []
        i = 0

        def flush_paragraph() -> None:
            nonlocal para_buffer
            if para_buffer:
                text = " ".join(para_buffer).strip()
                if text:
                    flowables.append(Paragraph(_linkify(text), styles["BodyBeacon"]))
                para_buffer = []

        while i < len(lines):
            line = lines[i].rstrip()
            stripped = line.strip()

            if not stripped:
                flush_paragraph()
                flowables.append(Spacer(1, 0.08 * inch))
                i += 1
                continue

            if stripped in {"---", "***", "___"}:
                flush_paragraph()
                flowables.append(Spacer(1, 0.06 * inch))
                flowables.append(
                    Table([[""]], colWidths=[6.2 * inch], style=[("LINEABOVE", (0, 0), (-1, -1), 0.5, colors.HexColor("#D8E1EA"))])
                )
                flowables.append(Spacer(1, 0.08 * inch))
                i += 1
                continue

            if stripped.startswith("### "):
                flush_paragraph()
                flowables.append(Paragraph(_linkify(stripped[4:].strip()), styles["SubHeadingBeacon"]))
                i += 1
                continue

            if stripped.startswith("#### "):
                flush_paragraph()
                flowables.append(Paragraph(_linkify(stripped[5:].strip()), styles["MicroHeadingBeacon"]))
                i += 1
                continue

            if stripped.startswith("|") and i + 1 < len(lines) and "|" in lines[i + 1]:
                table_rows, next_i = _parse_table_block(lines, i)
                flush_paragraph()
                if table_rows is not None:
                    table = _make_table(table_rows, styles)
                    if table is not None:
                        flowables.append(table)
                        flowables.append(Spacer(1, 0.12 * inch))
                i = next_i
                continue

            if stripped.startswith(("- ", "* ")):
                flush_paragraph()
                flowables.append(Paragraph(f"- {_linkify(stripped[2:].strip())}", styles["BulletBeacon"]))
                i += 1
                continue

            ordered = re.match(r"^\d+\.\s+(.*)$", stripped)
            if ordered:
                flush_paragraph()
                flowables.append(Paragraph(_linkify(f"{ordered.group(1).strip()}"), styles["BulletNumberBeacon"]))
                i += 1
                continue

            para_buffer.append(stripped)
            i += 1

        flush_paragraph()
        return flowables

    def _weak_signal_cards(body: str, styles: dict[str, ParagraphStyle]) -> list:
        items = [line[2:].strip() for line in body.splitlines() if line.strip().startswith(("- ", "* "))]
        if not items:
            return _body_flowables(body, styles)
        flowables = []
        for item in items:
            flowables.append(Paragraph(f"- {_linkify(item)}", styles["BodyBeacon"]))
            flowables.append(Spacer(1, 0.05 * inch))
        return flowables

    def _scenario_cards(body: str, styles: dict[str, ParagraphStyle]) -> list:
        rows = []
        current: list[str] = []
        for line in body.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith(("- ", "* ")):
                current.append(stripped[2:].strip())
            else:
                current.append(stripped)
        if current:
            for item in current:
                rows.append(
                    [
                        Paragraph("<font color='#1D4ED8'><b>Scenario</b></font>", styles["TinyLabelBeacon"]),
                        Paragraph(_linkify(item), styles["BodyBeacon"]),
                    ]
                )
        if not rows:
            return _body_flowables(body, styles)
        table = Table(rows, colWidths=[0.9 * inch, 5.4 * inch], hAlign="LEFT")
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FCFDFF")),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#D8E1EA")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#E5EBF3")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )
        return [table, Spacer(1, 0.1 * inch)]

    def _later_page(canvas, doc) -> None:  # noqa: ANN001
        canvas.saveState()
        width, height = letter
        canvas.setStrokeColor(colors.HexColor("#D8E1EA"))
        canvas.line(doc.leftMargin, height - 0.58 * inch, width - doc.rightMargin, height - 0.58 * inch)
        canvas.setFont("Helvetica-Bold", 8)
        canvas.setFillColor(colors.HexColor("#0F172A"))
        canvas.drawString(doc.leftMargin, height - 0.39 * inch, "Beacon AI")
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#64748B"))
        canvas.drawRightString(width - doc.rightMargin, height - 0.39 * inch, f"{context.title} | Page {doc.page}")
        canvas.drawString(doc.leftMargin, 0.4 * inch, "Internal executive analysis")
        canvas.drawRightString(width - doc.rightMargin, 0.4 * inch, "Beacon AI")
        canvas.restoreState()

    def _cover_page(canvas, doc) -> None:  # noqa: ANN001
        canvas.saveState()
        width, height = letter
        navy = colors.HexColor("#0F172A")
        navy_2 = colors.HexColor("#111D36")
        canvas.setFillColor(navy)
        canvas.rect(0, 0, width, height, fill=1, stroke=0)
        canvas.setFillColor(navy_2)
        canvas.rect(0, height - 1.15 * inch, width, 1.15 * inch, fill=1, stroke=0)
        canvas.setFillColor(colors.HexColor("#B88A1D"))
        canvas.rect(0, 0, 0.18 * inch, height, fill=1, stroke=0)
        canvas.setStrokeColor(colors.HexColor("#1D4ED8"))
        canvas.setLineWidth(1.2)
        canvas.line(width - 2.1 * inch, 0.8 * inch, width - 0.6 * inch, 0.8 * inch)
        canvas.restoreState()

    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="CoverBrand",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=8.5,
            leading=10,
            textColor=colors.HexColor("#CBD5E1"),
            spaceAfter=2,
        )
    )
    styles.add(
        ParagraphStyle(
            name="CoverTitle",
            parent=styles["Title"],
            fontName="Times-Bold",
            fontSize=24,
            leading=28,
            textColor=colors.white,
            alignment=TA_LEFT,
            spaceAfter=10,
        )
    )
    styles.add(
        ParagraphStyle(
            name="CoverLead",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=11.5,
            leading=15,
            textColor=colors.HexColor("#E5EEF9"),
            spaceAfter=16,
        )
    )
    styles.add(
        ParagraphStyle(
            name="MetaLabel",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=7.5,
            leading=9,
            textColor=colors.HexColor("#94A3B8"),
            spaceAfter=3,
        )
    )
    styles.add(
        ParagraphStyle(
            name="MetaValue",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=10.5,
            leading=12,
            textColor=colors.white,
        )
    )
    styles.add(
        ParagraphStyle(
            name="BodyBeacon",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=10.3,
            leading=13.2,
            textColor=colors.HexColor("#334155"),
            spaceAfter=5,
        )
    )
    styles.add(
        ParagraphStyle(
            name="SectionBeacon",
            parent=styles["Heading2"],
            fontName="Times-Bold",
            fontSize=16,
            leading=18,
            textColor=colors.HexColor("#0F172A"),
            spaceBefore=0,
            spaceAfter=6,
        )
    )
    styles.add(
        ParagraphStyle(
            name="SubHeadingBeacon",
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
            name="MicroHeadingBeacon",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=9.3,
            leading=11,
            textColor=colors.HexColor("#1D4ED8"),
            spaceBefore=5,
            spaceAfter=2,
        )
    )
    styles.add(
        ParagraphStyle(
            name="BulletBeacon",
            parent=styles["BodyTextBeacon"],
            leftIndent=10,
            firstLineIndent=0,
            spaceAfter=4,
        )
    )
    styles.add(
        ParagraphStyle(
            name="BulletNumberBeacon",
            parent=styles["BodyTextBeacon"],
            leftIndent=10,
            firstLineIndent=0,
            spaceAfter=4,
        )
    )
    styles.add(
        ParagraphStyle(
            name="TinyLabelBeacon",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=7.4,
            leading=9,
            textColor=colors.HexColor("#64748B"),
        )
    )
    styles.add(
        ParagraphStyle(
            name="TableHeaderBeacon",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=8.0,
            leading=9.6,
            textColor=colors.HexColor("#0F172A"),
        )
    )
    styles.add(
        ParagraphStyle(
            name="TableCellBeacon",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=7.9,
            leading=9.8,
            textColor=colors.HexColor("#334155"),
        )
    )

    cover_stats = [
        ("Industry / Sector", _meta_lookup("Industry") or "n/a"),
        ("Geographic scope", _meta_lookup("Geographic scope") or "n/a"),
        ("Time range", _meta_lookup("Time range") or "n/a"),
        ("Sections", str(len(sections))),
    ]

    cover_logo = None
    if LOGO_PATH.exists():
        cover_logo = Image(str(LOGO_PATH), width=0.55 * inch, height=0.55 * inch)

    cover_story = []
    if cover_logo is not None:
        cover_story.append(
            Table(
                [[cover_logo, Paragraph("Beacon AI executive analysis", styles["CoverBrand"])]],
                colWidths=[0.7 * inch, 4.7 * inch],
                style=[
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ],
            )
        )
    else:
        cover_story.append(Paragraph("Beacon AI executive analysis", styles["CoverBrand"]))

    cover_story.extend(
        [
            Spacer(1, 0.35 * inch),
            Paragraph(context.title, styles["CoverTitle"]),
            Paragraph(
                context.lead
                or "A concise executive report on macro, mega, and sub-trend movement, designed for leadership review and immediate action.",
                styles["CoverLead"],
            ),
            Spacer(1, 0.18 * inch),
            Table(
                [[Paragraph(label, styles["MetaLabel"]) for label, _ in cover_stats], [Paragraph(value, styles["MetaValue"]) for _, value in cover_stats]],
                colWidths=[1.3 * inch, 1.3 * inch, 1.3 * inch, 1.3 * inch],
                style=[
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#111D36")),
                    ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#2A3B5F")),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#2A3B5F")),
                    ("LEFTPADDING", (0, 0), (-1, -1), 10),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ],
            ),
            Spacer(1, 0.28 * inch),
            Paragraph(
                "Prepared for leadership review. The report compresses the trend hierarchy, weak signals, scenarios, and strategic implications into a single decision-ready memo.",
                styles["CoverLead"],
            ),
            Spacer(1, 1.05 * inch),
        ]
    )

    story = cover_story + [PageBreak()]

    def _section_heading(title_text: str) -> Paragraph:
        return Paragraph(title_text, styles["SectionBeacon"])

    for section_index, (title_text, body) in enumerate(sections):
        if section_index > 0:
            story.append(PageBreak())
        story.append(_section_heading(title_text))
        story.append(Spacer(1, 0.06 * inch))

        if title_text == "Executive Summary":
            lead_lines = [line.strip() for line in body.splitlines() if line.strip()]
            summary = " ".join(lead_lines[:2]) if lead_lines else ""
            if summary:
                box = Table(
                    [[Paragraph(_linkify(summary), styles["BodyBeacon"])]],
                    colWidths=[6.4 * inch],
                    style=[
                        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
                        ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#D8E1EA")),
                        ("LEFTPADDING", (0, 0), (-1, -1), 12),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                        ("TOPPADDING", (0, 0), (-1, -1), 10),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                    ],
                )
                story.append(box)
                story.append(Spacer(1, 0.12 * inch))
            remainder = "\n".join(lead_lines[2:]) if len(lead_lines) > 2 else ""
            if remainder:
                story.extend(_body_flowables(remainder, styles))
            continue

        if title_text == "Weak Signals":
            story.extend(_weak_signal_cards(body, styles))
            continue

        if title_text == "Scenarios":
            story.extend(_scenario_cards(body, styles))
            continue

        if title_text in {"PESTEL Macro Scan", "Key Trends", "Trend Hierarchy From trends.py"}:
            story.extend(_body_flowables(body, styles))
            continue

        if title_text == "Sources":
            story.extend(_body_flowables(body, styles))
            continue

        story.extend(_body_flowables(body, styles))
        story.append(Spacer(1, 0.06 * inch))

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=0.62 * inch,
        rightMargin=0.62 * inch,
        topMargin=0.72 * inch,
        bottomMargin=0.7 * inch,
        title=title,
        author="Beacon AI",
    )

    # Draw cover and content chrome with separate page callbacks.
    def _first_page(canvas, doc_obj):  # noqa: ANN001
        _cover_page(canvas, doc_obj)

    def _later_page_callback(canvas, doc_obj):  # noqa: ANN001
        _later_page(canvas, doc_obj)

    # Avoid name collision above.
    doc.build(story, onFirstPage=_first_page, onLaterPages=_later_page_callback)
    return buffer.getvalue()
