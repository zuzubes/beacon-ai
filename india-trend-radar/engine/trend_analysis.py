"""
Trend-analysis report builder for Beacon AI.

This module turns the current query inputs, the research context, and the
trend hierarchy into a timestamped markdown report plus a combined final
analysis document and PDF export.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import requests

from engine.pdf_export import markdown_to_pdf_bytes

ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_DIR = ROOT_DIR / "raw" / "analysis"


def _load_env_file() -> None:
    for env_path in (
        Path(__file__).with_name(".env"),
        ROOT_DIR / ".env",
    ):
        if not env_path.exists():
            continue

        for line in env_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            key = key.strip()
            if not key or key in os.environ:
                continue
            os.environ[key] = value.strip().strip('"').strip("'")


_load_env_file()


@dataclass(frozen=True)
class TrendAnalysisResult:
    report_markdown: str
    combined_markdown: str
    report_path: str
    combined_path: str
    pdf_path: str
    pdf_bytes: bytes
    share_url: str | None
    generated_at: str


REPORT_PROMPT_TEMPLATE = """You are writing the final trend-analysis report for Beacon AI.

Context:
- Industry / Sector: {industry}
- Region: {region}
- Time range: {time_range}

Research context:
{research_context}

Trend hierarchy produced by trends.py:
{trend_summary}

Write a concise markdown report with these sections:
# Trend Analysis: {industry} in {region}
## Executive Summary
## PESTEL Macro Scan
## Key Trends
## Weak Signals
## Scenarios
## Strategic Implications
## Assumptions & Limitations

Rules:
- Be concrete and concise.
- Ground the narrative in the supplied context and trend hierarchy.
- Use markdown tables where they help readability.
- Do not invent citations or external facts that are not already implied by the input.
- If evidence is thin, state that clearly.
"""


def _slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_") or "analysis"


def _format_trend_summary(trend_data: list[dict], limit: int = 20) -> str:
    if not trend_data:
        return "- No trend hierarchy available."
    items = sorted(
        trend_data,
        key=lambda item: (
            {"Macro": 0, "Mega": 1, "Sub": 2}.get(item.get("tier", "Sub"), 3),
            -float(item.get("strength", 0.0)),
            item.get("name", ""),
        ),
    )[:limit]
    lines = []
    for item in items:
        parent = item.get("parent") or "None"
        lines.append(
            f"- {item.get('tier', 'Sub')}: {item.get('name', 'Untitled')} | "
            f"category={item.get('category', 'General')} | parent={parent} | "
            f"strength={float(item.get('strength', 0.0)):.1f} | "
            f"growth={float(item.get('growth_pct', 0.0)):+.0f}% | "
            f"horizon={item.get('time_horizon', '1-2y')} | "
            f"recommendation={item.get('recommendation', 'Watch')}"
        )
    return "\n".join(lines)


def _trend_table(trend_data: list[dict]) -> str:
    if not trend_data:
        return "| Tier | Trend | Category | Parent | Strength | Growth | Horizon | Recommendation |\n|---|---|---|---|---:|---:|---|---|"

    rows = [
        "| Tier | Trend | Category | Parent | Strength | Growth | Horizon | Recommendation |",
        "|---|---|---|---|---:|---:|---|---|",
    ]
    for item in sorted(
        trend_data,
        key=lambda item: (
            {"Macro": 0, "Mega": 1, "Sub": 2}.get(item.get("tier", "Sub"), 3),
            -float(item.get("strength", 0.0)),
            item.get("name", ""),
        ),
    ):
        rows.append(
            "| {tier} | {name} | {category} | {parent} | {strength:.1f} | {growth:+.0f}% | {horizon} | {recommendation} |".format(
                tier=item.get("tier", "Sub"),
                name=str(item.get("name", "Untitled")).replace("|", "\\|"),
                category=str(item.get("category", "General")).replace("|", "\\|"),
                parent=str(item.get("parent") or "None").replace("|", "\\|"),
                strength=float(item.get("strength", 0.0)),
                growth=float(item.get("growth_pct", 0.0)),
                horizon=str(item.get("time_horizon", "1-2y")).replace("|", "\\|"),
                recommendation=str(item.get("recommendation", "Watch")).replace("|", "\\|"),
            )
        )
    return "\n".join(rows)


def _report_preamble(time_range: str, region: str, industry: str) -> str:
    return (
        f"# Trend Analysis: {industry} in {region}\n\n"
        f"**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        f"**Industry**: {industry}\n\n"
        f"**Geographic scope**: {region}\n\n"
        f"**Time horizon**: {time_range}\n\n"
    )


def _source_url(value: str | None) -> str | None:
    if not value:
        return None
    value = str(value).strip()
    if value.startswith(("http://", "https://", "file://")):
        return value
    return None


def _sources_markdown(research_context: object | None) -> str:
    lines: list[str] = []
    if research_context is not None:
        hits = getattr(research_context, "hits", []) or []
        for hit in hits[:8]:
            url = _source_url(getattr(hit, "url", None))
            title = getattr(hit, "title", "Source")
            snippet = getattr(hit, "snippet", "")
            if url:
                lines.append(f"- [{title}]({url}) - {snippet}")
            else:
                lines.append(f"- {title} - {snippet}")

        matches = getattr(research_context, "report_matches", []) or []
        for match in matches[:5]:
            rel_path = str(getattr(match, "path", "")).strip()
            abs_path = (ROOT_DIR / rel_path).resolve()
            url = abs_path.as_uri() if abs_path.exists() else None
            title = getattr(match, "title", "Local report")
            excerpt = getattr(match, "excerpt", "")
            if url:
                lines.append(f"- [{title}]({url}) - {excerpt}")
            else:
                lines.append(f"- {title} - {excerpt}")

    if not lines:
        lines.append("- No live sources available.")

    return "## Sources\n" + "\n".join(lines)


def _sample_report_markdown(
    time_range: str,
    region: str,
    industry: str,
    research_context: object | None,
    trend_data: list[dict],
) -> str:
    keyword_line = "- None"
    report_line = "- No local report matches were found."
    if research_context is not None:
        keywords = getattr(research_context, "keywords", []) or []
        matches = getattr(research_context, "report_matches", []) or []
        if keywords:
            keyword_line = "\n".join(f"- {keyword}" for keyword in keywords[:10])
        if matches:
            report_line = "\n".join(
                f"- {match.title}: {match.excerpt}" for match in matches[:5]
            )

    top_trends = sorted(trend_data, key=lambda item: float(item.get("strength", 0.0)), reverse=True)[:6]
    trend_bullets = "\n".join(
        f"- **{item.get('name', 'Untitled')}** ({item.get('tier', 'Sub')}): "
        f"{item.get('description', '')}"
        for item in top_trends
    ) or "- No trends available."

    return (
        _report_preamble(time_range, region, industry)
        + "## Executive Summary\n"
        + "Sample analysis generated from the current trend hierarchy and research context.\n\n"
        + "## PESTEL Macro Scan\n"
        + "### Political / Economic / Social / Technological / Environmental / Legal\n"
        + "The current query suggests policy, pricing, consumer, and technology pressure points, but the app is using sample synthesis here because no live OpenAI report was requested or available.\n\n"
        + "## Key Trends\n"
        + trend_bullets
        + "\n\n## Weak Signals\n"
        + "- No weak signals detected in the sources surveyed.\n\n"
        + "## Scenarios\n"
        + "Two uncertainties dominate: how quickly adoption moves from niche to mainstream, and whether external shocks accelerate or slow capital deployment.\n\n"
        + "## Strategic Implications\n"
        + "1. Focus on the strongest macro-to-sub trend linkages.\n"
        + "2. Prioritize India-relevant execution themes that appear in both the trend hierarchy and the research context.\n\n"
        + "## Assumptions & Limitations\n"
        + "This sample report is a deterministic fallback. It should be replaced by a live OpenAI-generated narrative when an API key is present.\n\n"
        + "## Extracted Keywords\n"
        + keyword_line
        + "\n\n## Local Reports Cross-Reference\n"
        + report_line
    )


def _live_report_markdown(
    api_key: str,
    time_range: str,
    region: str,
    industry: str,
    research_context: object | None,
    trend_data: list[dict],
) -> str:
    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    prompt = REPORT_PROMPT_TEMPLATE.format(
        industry=industry or "General",
        region=region or "Global",
        time_range=time_range or "Past 1 week",
        research_context=getattr(research_context, "prompt", "- Not available"),
        trend_summary=_format_trend_summary(trend_data),
    )
    response = client.responses.create(
        model="gpt-4.1-mini",
        input=prompt,
        max_output_tokens=7000,
    )
    if getattr(response, "status", None) == "incomplete":
        reason = getattr(getattr(response, "incomplete_details", None), "reason", "unknown")
        raise RuntimeError(f"response truncated by the API before it finished ({reason})")

    text = getattr(response, "output_text", "").strip()
    if not text:
        chunks = []
        for item in getattr(response, "output", []) or []:
            for content in getattr(item, "content", []) or []:
                if getattr(content, "type", "") == "output_text":
                    chunks.append(getattr(content, "text", ""))
        text = "".join(chunks).strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
    return text or _sample_report_markdown(time_range, region, industry, research_context, trend_data)


def _combined_markdown(
    report_markdown: str,
    trend_data: list[dict],
    research_context: object | None,
) -> str:
    return (
        report_markdown.strip()
        + "\n\n## Trend Hierarchy From trends.py\n\n"
        + _trend_table(trend_data)
        + "\n\n"
        + _sources_markdown(research_context)
    )


def _tinyurl(target_url: str) -> str | None:
    try:
        resp = requests.get(
            "https://tinyurl.com/api-create.php",
            params={"url": target_url},
            timeout=12,
        )
        resp.raise_for_status()
        value = resp.text.strip()
        return value if value.startswith("http") else None
    except Exception:  # noqa: BLE001
        return None


def build_trend_analysis_report(
    time_range: str,
    region: str,
    industry: str,
    trend_data: list[dict],
    research_context: object | None,
    api_key: str | None = None,
    output_dir: Path | None = None,
) -> TrendAnalysisResult:
    output_root = output_dir or DEFAULT_OUTPUT_DIR
    output_root.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    region_slug = _slugify(region)
    industry_slug = _slugify(industry)
    base_name = f"{region_slug}_{industry_slug}_{timestamp}"
    report_path = output_root / f"{base_name}.md"
    combined_path = output_root / f"{base_name}_final.md"
    pdf_path = output_root / f"{base_name}_final.pdf"

    if api_key:
        try:
            report_markdown = _live_report_markdown(api_key, time_range, region, industry, research_context, trend_data)
        except Exception:
            report_markdown = _sample_report_markdown(time_range, region, industry, research_context, trend_data)
    else:
        report_markdown = _sample_report_markdown(time_range, region, industry, research_context, trend_data)

    combined_markdown = _combined_markdown(report_markdown, trend_data, research_context)
    pdf_bytes = markdown_to_pdf_bytes(combined_markdown, title=f"Beacon AI final analysis - {industry} in {region}")
    pdf_path.write_bytes(pdf_bytes)
    share_url = _tinyurl(pdf_path.as_uri())

    report_path.write_text(report_markdown, encoding="utf-8")
    combined_path.write_text(combined_markdown, encoding="utf-8")

    return TrendAnalysisResult(
        report_markdown=report_markdown,
        combined_markdown=combined_markdown,
        report_path=str(report_path.relative_to(ROOT_DIR)),
        combined_path=str(combined_path.relative_to(ROOT_DIR)),
        pdf_path=str(pdf_path.relative_to(ROOT_DIR)),
        pdf_bytes=pdf_bytes,
        share_url=share_url,
        generated_at=timestamp,
    )
