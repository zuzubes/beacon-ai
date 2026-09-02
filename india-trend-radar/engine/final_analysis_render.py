"""Branded HTML rendering for Beacon AI's final analysis report."""

from __future__ import annotations

import base64
import html
import re
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
LOGO_PATH = ROOT_DIR / "assets" / "beacon-ai-logo.png"

ALLOWED_TAGS = [
    "a",
    "article",
    "blockquote",
    "br",
    "div",
    "em",
    "h1",
    "h2",
    "h3",
    "h4",
    "hr",
    "img",
    "li",
    "ol",
    "p",
    "section",
    "span",
    "strong",
    "table",
    "tbody",
    "td",
    "tfoot",
    "th",
    "thead",
    "tr",
    "ul",
]

ALLOWED_ATTRIBUTES = {
    "a": ["href", "title", "target", "rel"],
    "img": ["src", "alt"],
    "td": ["colspan", "rowspan"],
    "th": ["colspan", "rowspan", "scope"],
    "*": ["class"],
}

SAFE_PROTOCOLS = ("http://", "https://", "data:")


@dataclass(frozen=True)
class ReportPreamble:
    title: str
    meta: list[tuple[str, str]]
    lead: str


def _logo_data_uri() -> str | None:
    if not LOGO_PATH.exists():
        return None
    data = LOGO_PATH.read_bytes()
    return "data:image/png;base64," + base64.b64encode(data).decode("ascii")


def _sanitize_html(value: str) -> str:
    class _Sanitizer(HTMLParser):
        def __init__(self) -> None:
            super().__init__(convert_charrefs=False)
            self.parts: list[str] = []
            self.skip_depth = 0

        def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
            if tag in {"script", "style"}:
                self.skip_depth += 1
                return
            if self.skip_depth or tag not in ALLOWED_TAGS:
                return
            allowed = ALLOWED_ATTRIBUTES.get(tag, []) + ALLOWED_ATTRIBUTES.get("*", [])
            rendered_attrs: list[str] = []
            for name, raw_value in attrs:
                if name not in allowed or raw_value is None:
                    continue
                value = raw_value.strip()
                if name in {"href", "src"} and not value.startswith(SAFE_PROTOCOLS):
                    continue
                rendered_attrs.append(f'{name}="{html.escape(value, quote=True)}"')
            attrs_text = f" {' '.join(rendered_attrs)}" if rendered_attrs else ""
            self.parts.append(f"<{tag}{attrs_text}>")

        def handle_endtag(self, tag: str) -> None:
            if tag in {"script", "style"}:
                if self.skip_depth:
                    self.skip_depth -= 1
                return
            if self.skip_depth or tag not in ALLOWED_TAGS:
                return
            self.parts.append(f"</{tag}>")

        def handle_data(self, data: str) -> None:
            if not self.skip_depth:
                self.parts.append(html.escape(data))

        def handle_entityref(self, name: str) -> None:
            if not self.skip_depth:
                self.parts.append(f"&{name};")

        def handle_charref(self, name: str) -> None:
            if not self.skip_depth:
                self.parts.append(f"&#{name};")

    parser = _Sanitizer()
    parser.feed(value)
    parser.close()
    return "".join(parser.parts)


def _render_inline(text: str) -> str:
    escaped = html.escape(text)
    escaped = re.sub(
        r"\[([^\]]+)\]\((https?://[^)]+)\)",
        lambda m: f'<a href="{html.escape(m.group(2), quote=True)}" target="_blank" rel="noopener noreferrer">{m.group(1)}</a>',
        escaped,
    )
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", escaped)
    return escaped.replace("\n", "<br>")


def _render_table(rows: list[list[str]]) -> str:
    if len(rows) < 2:
        return ""
    header = rows[0]
    body_rows = rows[2:] if len(rows) > 2 else []
    parts = ["<table><thead><tr>"]
    parts.extend(f"<th>{_render_inline(cell.strip())}</th>" for cell in header)
    parts.append("</tr></thead><tbody>")
    for row in body_rows:
        parts.append("<tr>")
        parts.extend(f"<td>{_render_inline(cell.strip())}</td>" for cell in row)
        parts.append("</tr>")
    parts.append("</tbody></table>")
    return "".join(parts)


def _render_markdown_fragment(markdown_text: str) -> str:
    lines = markdown_text.splitlines()
    parts: list[str] = []
    i = 0
    list_type: str | None = None
    in_paragraph: list[str] = []

    def flush_paragraph() -> None:
        nonlocal in_paragraph
        if in_paragraph:
            parts.append(f"<p>{_render_inline(' '.join(in_paragraph).strip())}</p>")
            in_paragraph = []

    def close_list() -> None:
        nonlocal list_type
        if list_type:
            parts.append(f"</{list_type}>")
            list_type = None

    while i < len(lines):
        line = lines[i].rstrip()
        stripped = line.strip()

        if not stripped:
            flush_paragraph()
            close_list()
            i += 1
            continue

        heading_match = re.match(r"^(#{1,4})\s+(.+)$", stripped)
        if heading_match:
            flush_paragraph()
            close_list()
            level = len(heading_match.group(1)) + 1
            parts.append(f"<h{level}>{_render_inline(heading_match.group(2).strip())}</h{level}>")
            i += 1
            continue

        if stripped.startswith(("- ", "* ")):
            flush_paragraph()
            if list_type != "ul":
                close_list()
                parts.append("<ul>")
                list_type = "ul"
            parts.append(f"<li>{_render_inline(stripped[2:].strip())}</li>")
            i += 1
            continue

        ordered_match = re.match(r"^\d+\.\s+(.+)$", stripped)
        if ordered_match:
            flush_paragraph()
            if list_type != "ol":
                close_list()
                parts.append("<ol>")
                list_type = "ol"
            parts.append(f"<li>{_render_inline(ordered_match.group(1).strip())}</li>")
            i += 1
            continue

        if "|" in stripped and i + 1 < len(lines):
            next_line = lines[i + 1].strip()
            if re.match(r"^\|?(?:\s*:?-{3,}:?\s*\|)+\s*:?-{3,}:?\s*\|?$", next_line):
                flush_paragraph()
                close_list()
                table_rows: list[list[str]] = []
                while i < len(lines):
                    row_text = lines[i].strip()
                    if not row_text or "|" not in row_text:
                        break
                    cells = [cell.strip() for cell in row_text.strip("|").split("|")]
                    table_rows.append(cells)
                    i += 1
                parts.append(_render_table(table_rows))
                continue

        close_list()
        in_paragraph.append(stripped)
        i += 1

    flush_paragraph()
    close_list()
    return _sanitize_html("".join(parts))


def _split_report_preamble(report_markdown: str) -> ReportPreamble:
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
    return ReportPreamble(title=title, meta=meta, lead=lead)


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


def _summaries(trend_data: list[dict], research_context: object | None) -> list[tuple[str, str]]:
    live_hits = len(getattr(research_context, "hits", []) or [])
    return [
        ("Trend nodes", str(len(trend_data))),
        ("Live sources", str(live_hits)),
    ]


def render_final_analysis_html(
    report_markdown: str,
    combined_markdown: str,
    trend_data: list[dict],
    research_context: object | None,
    generated_at: str,
    region: str,
    industry: str,
) -> str:
    preamble = _split_report_preamble(report_markdown)
    sections = _split_sections(combined_markdown)
    logo_uri = _logo_data_uri()
    metrics = _summaries(trend_data, research_context)

    section_cards = []
    for title, body in sections:
        body_html = _render_markdown_fragment(body)
        card_class = "section-card section-card-wide" if title in {"Trend Hierarchy From trends.py", "Sources"} else "section-card"
        section_cards.append(
            f"""
            <section class="{card_class}">
                <div class="section-head">
                    <h2>{html.escape(title)}</h2>
                </div>
                <div class="section-body">{body_html}</div>
            </section>
            """
        )

    hero_meta = "".join(
        f"""
        <div class="hero-meta-item">
            <div class="hero-meta-label">{html.escape(label)}</div>
            <div class="hero-meta-value">{html.escape(value)}</div>
        </div>
        """
        for label, value in preamble.meta[:4]
    )
    stat_cards = "".join(
        f"""
        <div class="metric-card">
            <div class="metric-label">{html.escape(label)}</div>
            <div class="metric-value">{html.escape(value)}</div>
        </div>
        """
        for label, value in metrics
    )

    logo_html = (
        f'<img class="brand-logo" src="{logo_uri}" alt="Beacon AI logo" />'
        if logo_uri
        else '<div class="brand-mark">Beacon AI</div>'
    )

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(preamble.title)}</title>
  <style>
    :root {{
      --navy: #0f172a;
      --navy-2: #111d36;
      --slate: #475569;
      --muted: #64748b;
      --line: #d8e1ea;
      --cream: #f7f8fb;
      --blue: #1d4ed8;
      --gold: #b88a1d;
      --gold-bg: #fbf3da;
      --card: #ffffff;
      --shadow: 0 16px 34px rgba(15, 23, 42, 0.08);
    }}

    * {{ box-sizing: border-box; }}
    html {{ font-size: 10.5pt; }}
    body {{
      margin: 0;
      background: linear-gradient(180deg, #eef3f8 0%, #f5f7fb 100%);
      color: var(--navy);
      font-family: Arial, Helvetica, sans-serif;
      line-height: 1.55;
    }}

    .report {{
      max-width: 8.5in;
      margin: 0 auto;
      min-height: 100vh;
      padding: 18px 16px 28px;
    }}

    .hero {{
      position: relative;
      overflow: hidden;
      background: linear-gradient(135deg, var(--navy) 0%, var(--navy-2) 62%, #18294c 100%);
      color: white;
      border-radius: 28px;
      padding: 28px 28px 22px;
      box-shadow: var(--shadow);
      margin-bottom: 16px;
    }}

    .hero::after {{
      content: "";
      position: absolute;
      inset: 0;
      background:
        radial-gradient(ellipse at top right, rgba(184, 138, 29, 0.18), transparent 36%),
        radial-gradient(ellipse at bottom left, rgba(29, 78, 216, 0.18), transparent 28%);
      pointer-events: none;
    }}

    .hero-inner, .section-card, .summary-grid, .signal-callout {{
      position: relative;
      z-index: 1;
    }}

    .hero-brand {{
      display: flex;
      align-items: center;
      gap: 14px;
      margin-bottom: 20px;
    }}

    .brand-logo {{
      width: 52px;
      height: 52px;
      object-fit: contain;
      border-radius: 16px;
      background: rgba(255,255,255,0.06);
      padding: 6px;
    }}

    .brand-mark {{
      font-weight: 700;
      letter-spacing: 0.04em;
      text-transform: uppercase;
      color: rgba(255,255,255,0.72);
      font-size: 0.78rem;
    }}

    .hero-kicker {{
      font-size: 0.72rem;
      letter-spacing: 0.18em;
      text-transform: uppercase;
      color: rgba(255,255,255,0.6);
    }}

    .hero-title {{
      margin: 8px 0 10px;
      font-family: Georgia, "Times New Roman", serif;
      font-size: 2.15rem;
      line-height: 1.08;
      letter-spacing: -0.03em;
      max-width: 6.2in;
    }}

    .hero-lead {{
      margin: 0;
      max-width: 6.2in;
      color: rgba(255,255,255,0.84);
      font-size: 1rem;
    }}

    .hero-meta {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 10px;
      margin-top: 18px;
    }}

    .hero-meta-item {{
      background: rgba(255, 255, 255, 0.07);
      border: 1px solid rgba(255, 255, 255, 0.12);
      border-radius: 16px;
      padding: 12px 14px;
    }}

    .hero-meta-label, .metric-label, .section-kicker, .signal-label {{
      text-transform: uppercase;
      letter-spacing: 0.12em;
      font-size: 0.66rem;
    }}

    .hero-meta-label {{
      color: rgba(255,255,255,0.55);
      margin-bottom: 6px;
    }}

    .hero-meta-value {{
      font-weight: 600;
      color: white;
    }}

    .hero-footer {{
      display: grid;
      grid-template-columns: 1.5fr 1fr;
      gap: 14px;
      margin-top: 18px;
      align-items: end;
    }}

    .summary-grid {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 10px;
    }}

    .metric-card {{
      background: rgba(255, 255, 255, 0.08);
      border: 1px solid rgba(255, 255, 255, 0.14);
      border-radius: 16px;
      padding: 12px 14px;
      min-height: 88px;
    }}

    .metric-value {{
      font-family: Georgia, "Times New Roman", serif;
      font-size: 1.05rem;
      margin-top: 8px;
      color: white;
      font-weight: 700;
      line-height: 1.22;
    }}

    .signal-callout {{
      background: rgba(255, 255, 255, 0.08);
      border: 1px solid rgba(255,255,255,0.12);
      border-radius: 20px;
      padding: 16px 18px;
    }}

    .signal-label {{
      color: rgba(255,255,255,0.6);
      margin-bottom: 8px;
    }}

    .signal-title {{
      font-family: Georgia, "Times New Roman", serif;
      font-size: 1.1rem;
      font-weight: 700;
      margin-bottom: 6px;
    }}

    .signal-desc {{
      color: rgba(255,255,255,0.82);
      font-size: 0.92rem;
    }}

    .content {{
      display: grid;
      gap: 14px;
    }}

    .section-card {{
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 22px;
      box-shadow: var(--shadow);
      padding: 20px 22px;
    }}

    .section-card-wide {{
      border-left: 4px solid var(--blue);
    }}

    .section-head {{
      display: flex;
      flex-direction: column;
      gap: 6px;
      margin-bottom: 14px;
    }}

    .section-kicker {{
      color: var(--gold);
      font-weight: 700;
    }}

    .section-head h2 {{
      margin: 0;
      font-family: Georgia, "Times New Roman", serif;
      font-size: 1.25rem;
      letter-spacing: -0.02em;
      color: var(--navy);
    }}

    .section-body {{
      color: var(--slate);
      font-size: 0.92rem;
    }}

    .section-body h3 {{
      font-family: Georgia, "Times New Roman", serif;
      color: var(--navy);
      margin: 16px 0 8px;
      font-size: 1.02rem;
    }}

    .section-body p {{ margin: 0 0 10px; }}
    .section-body ul, .section-body ol {{ margin: 0 0 12px 20px; padding: 0; }}
    .section-body li {{ margin: 0 0 6px; }}

    .section-body table {{
      width: 100%;
      border-collapse: collapse;
      margin-top: 8px;
      font-size: 0.84rem;
      overflow: hidden;
      border-radius: 14px;
    }}

    .section-body thead th {{
      background: #eef2ff;
      color: var(--navy);
      text-align: left;
      padding: 10px 10px;
      border-bottom: 1px solid #d7deea;
      font-weight: 700;
    }}

    .section-body tbody td {{
      padding: 9px 10px;
      border-bottom: 1px solid #e7edf5;
      vertical-align: top;
    }}

    .section-body tbody tr:nth-child(even) {{ background: #fafcff; }}
    .section-body a {{ color: var(--blue); text-decoration: none; }}
    .section-body strong {{ color: var(--navy); }}
    .section-body blockquote {{
      margin: 10px 0;
      padding: 10px 14px;
      border-left: 3px solid var(--gold);
      background: var(--gold-bg);
      color: var(--navy);
      border-radius: 0 12px 12px 0;
    }}

    .footer-note {{
      color: var(--muted);
      font-size: 0.78rem;
      text-align: center;
      margin-top: 12px;
      padding-bottom: 6px;
    }}

    @media (max-width: 900px) {{
      .hero-meta, .summary-grid, .hero-footer {{
        grid-template-columns: 1fr;
      }}
      .report {{ padding: 0; }}
      .hero, .section-card {{ border-radius: 0; }}
    }}
  </style>
</head>
<body>
  <div class="report">
    <header class="hero">
      <div class="hero-inner">
        <div class="hero-brand">
          {logo_html}
          <div>
            <div class="hero-kicker">Beacon AI analysis</div>
            <div class="hero-kicker" style="margin-top:4px;">{html.escape(industry)} · {html.escape(region)}</div>
          </div>
        </div>
        <h1 class="hero-title">{html.escape(preamble.title)}</h1>
        <p class="hero-lead">{html.escape(preamble.lead or "Decision-ready summary of the current trend hierarchy, research context, and strategic implications.")}</p>
        <div class="hero-meta">
          {hero_meta}
        </div>
        <div class="hero-footer">
          <div class="summary-grid">
            {stat_cards}
          </div>
        </div>
      </div>
    </header>

    <main class="content">
      {''.join(section_cards)}
    </main>

    <div class="footer-note">Generated {html.escape(generated_at)} · Beacon AI</div>
  </div>
</body>
</html>
"""
