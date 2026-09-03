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
from time import perf_counter

import requests

from engine.cost_tracking import CostRunTracker
from engine.final_analysis_render import render_final_analysis_html
from engine.pdf_export import markdown_to_pdf_bytes

ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_DIR = ROOT_DIR / "raw" / "analysis"
DEFAULT_SHARE_UPLOAD_ENDPOINTS = tuple(
    endpoint
    for endpoint in (
        os.getenv("SHARE_UPLOAD_ENDPOINT", "").strip() or None,
        "https://0x0.st",
        "https://transfer.sh",
    )
    if endpoint
)


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
    html_report: str
    report_path: str
    combined_path: str
    html_path: str
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


def _relative_or_absolute(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT_DIR))
    except ValueError:
        return str(path)


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
        f"**Time range**: {time_range}\n\n"
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
    cost_tracker: CostRunTracker | None = None,
) -> str:
    from openai import OpenAI

    from engine.openai_keys import call_with_failover, resolve_openai_keys

    prompt = REPORT_PROMPT_TEMPLATE.format(
        industry=industry or "General",
        region=region or "Global",
        time_range=time_range or "Past 1 week",
        research_context=getattr(research_context, "prompt", "- Not available"),
        trend_summary=_format_trend_summary(trend_data),
    )
    started = perf_counter()
    try:
        response = call_with_failover(
            resolve_openai_keys(api_key),
            lambda key: OpenAI(api_key=key).responses.create(
                model="gpt-4.1-mini",
                input=prompt,
                max_output_tokens=7000,
            ),
        )
    except Exception as exc:  # noqa: BLE001
        elapsed_ms = int((perf_counter() - started) * 1000)
        if cost_tracker:
            cost_tracker.add_entry(
                feature="final analysis report",
                provider="openai",
                model="gpt-4.1-mini",
                endpoint="responses.create",
                status="error",
                latency_ms=elapsed_ms,
                error=f"{type(exc).__name__}: {exc}",
            )
        raise
    elapsed_ms = int((perf_counter() - started) * 1000)
    if getattr(response, "status", None) == "incomplete":
        reason = getattr(getattr(response, "incomplete_details", None), "reason", "unknown")
        if cost_tracker:
            cost_tracker.add_entry(
                feature="final analysis report",
                provider="openai",
                model="gpt-4.1-mini",
                endpoint="responses.create",
                status="error",
                response=response,
                latency_ms=elapsed_ms,
                error=f"truncated: {reason}",
            )
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
    if cost_tracker:
        cost_tracker.add_entry(
            feature="final analysis report",
            provider="openai",
            model="gpt-4.1-mini",
            endpoint="responses.create",
            status="success",
            response=response,
            latency_ms=elapsed_ms,
        )
    return text or _sample_report_markdown(time_range, region, industry, research_context, trend_data)


COMBINED_PROMPT_TEMPLATE = """You are a research analyst for an India-focused micro-VC fund partner. \
The partner tracks trends emerging in the US and China to find investable signal for India.

Query context:
- Time range: {time_range}
- Region focus: {region}
- Industry / Sector: {industry}

Research context:
{research_context}

You will produce two pieces of work in this single response: a trend hierarchy, then an analysis \
report built on that same hierarchy. Do both in one pass -- write the report using the trends you \
yourself just produced, not a separate or shortened version of them.

PART 1 -- TREND HIERARCHY
Produce a trend hierarchy with exactly three tiers, using this working definition for each tier:

Macro-Trends: long-term, macro changes that play out across many years or decades with large-scale \
impact, summarizing major forces across society, technology, economy, ecology, and politics.

Mega-Trends: the building blocks of the arena — points of tension that macro-trends create when they \
intersect with consumers' or businesses' basic needs.

Sub-Trends: emerging, actionable trends arising from that tension, highlighting how an investor could \
act on emerging expectations today, with explicit relevance to India as an investment destination \
given developments in the US and China.

Return 4-6 Macro-Trends. Each Macro-Trend has 2 Mega-Trends. Each Mega-Trend has 2 Sub-Trends.

PART 2 -- ANALYSIS REPORT
Using the trend hierarchy from Part 1, write a concise markdown report with these sections:
# Trend Analysis: {industry} in {region}
## Executive Summary
## PESTEL Macro Scan
## Key Trends
## Weak Signals
## Scenarios
## Strategic Implications
## Assumptions & Limitations

Rules for the report:
- Be concrete and concise.
- Ground the narrative in the supplied context and the Part 1 trend hierarchy.
- Use markdown tables where they help readability.
- Do not invent citations or external facts that are not already implied by the input.
- If evidence is thin, state that clearly.

OUTPUT FORMAT -- follow exactly, no commentary before, between, or after the two parts:

===TRENDS_JSON===
A JSON array of trend objects, ONLY valid JSON (no markdown fences), each shaped exactly:
{{
  "tier": "Macro" | "Mega" | "Sub",
  "parent": string or null (the exact name of the parent trend, null for Macro tier),
  "category": string (a short cluster label shared by a Macro-Trend and its children, e.g. "Energy & Climate"),
  "name": string (trend name, concise),
  "description": string (2-3 sentences, specific and non-generic),
  "strength": number from 0 to 10 (current momentum/strength of the trend),
  "growth_pct": number (year-over-year mention/interest growth, can be negative),
  "time_horizon": string (e.g. "<1y", "1-2y", "2-5y", "5-10y", "10y+"),
  "recommendation": "Invest" | "Strategize" | "Watch" | "Stay away"
}}
===REPORT_MARKDOWN===
The Part 2 markdown report.
"""


def parse_combined_response(text: str) -> tuple[list[dict], str]:
    """Splits a COMBINED_PROMPT_TEMPLATE response into (trend_data, report_markdown)."""
    from engine import trends as trends_module

    if "===REPORT_MARKDOWN===" not in text:
        raise RuntimeError("combined response was missing the ===REPORT_MARKDOWN=== section")
    trends_part, report_part = text.split("===REPORT_MARKDOWN===", 1)
    trends_part = trends_part.replace("===TRENDS_JSON===", "").strip()
    report_markdown = report_part.strip()
    if not report_markdown:
        raise RuntimeError("combined response had an empty report section")
    trend_data = trends_module.parse_live_trends_json(trends_part)
    return trend_data, report_markdown


def call_combined_trends_and_report(
    time_range: str,
    region: str,
    industry: str,
    api_key: str,
    research_context: object | None = None,
    on_text: "callable | None" = None,
    cost_tracker: CostRunTracker | None = None,
) -> tuple[list[dict], str]:
    """Single streamed OpenAI call that produces both the trend hierarchy and the report
    built from it, replacing two sequential round-trips (call_live_trends, then
    _live_report_markdown) with one -- the second call previously had to re-send the research
    context and a summary of the just-generated trends from scratch as a fresh prompt; doing
    both in one pass skips that repeated prompt processing and the extra network round-trip.

    `on_text`, if given, is called with the accumulated raw response text after each chunk so
    a caller can render live progress instead of a blank wait. Raises on failure -- callers
    should fall back to the separate call_live_trends / build_trend_analysis_report path."""
    from openai import OpenAI

    from engine import trends as trends_module
    from engine.openai_keys import call_with_failover, resolve_openai_keys

    prompt = COMBINED_PROMPT_TEMPLATE.format(
        time_range=time_range or "Past 1 week",
        region=region or "Global",
        industry=industry or "General",
        research_context=getattr(research_context, "prompt", None) or "- Not available",
    )
    started = perf_counter()
    accumulated = []

    def _stream_once(key: str):
        # Reset in case a prior key's attempt streamed partial text before failing --
        # a retry on the backup key must not append to stale content from that attempt.
        accumulated.clear()
        with OpenAI(api_key=key).responses.stream(
            model="gpt-4.1-mini",
            input=prompt,
            # Same combined headroom as the two separate calls this replaces (12000 for
            # trends + 7000 for the report).
            max_output_tokens=19000,
        ) as stream:
            for event in stream:
                if getattr(event, "type", "") == "response.output_text.delta":
                    accumulated.append(event.delta)
                    if on_text is not None:
                        on_text("".join(accumulated))
            return stream.get_final_response()

    try:
        response = call_with_failover(resolve_openai_keys(api_key), _stream_once)
    except Exception as exc:  # noqa: BLE001
        elapsed_ms = int((perf_counter() - started) * 1000)
        if cost_tracker:
            cost_tracker.add_entry(
                feature="trend generation + final analysis report (combined)",
                provider="openai",
                model="gpt-4.1-mini",
                endpoint="responses.stream",
                status="error",
                latency_ms=elapsed_ms,
                error=f"{type(exc).__name__}: {exc}",
            )
        raise
    elapsed_ms = int((perf_counter() - started) * 1000)

    if getattr(response, "status", None) == "incomplete":
        reason = getattr(getattr(response, "incomplete_details", None), "reason", "unknown")
        if cost_tracker:
            cost_tracker.add_entry(
                feature="trend generation + final analysis report (combined)",
                provider="openai",
                model="gpt-4.1-mini",
                endpoint="responses.stream",
                status="error",
                response=response,
                latency_ms=elapsed_ms,
                error=f"truncated: {reason}",
            )
        raise RuntimeError(f"response truncated by the API before it finished ({reason})")

    text = trends_module.extract_response_text(response)
    try:
        result = parse_combined_response(text)
    except Exception as exc:  # noqa: BLE001
        if cost_tracker:
            cost_tracker.add_entry(
                feature="trend generation + final analysis report (combined)",
                provider="openai",
                model="gpt-4.1-mini",
                endpoint="responses.stream",
                status="error",
                response=response,
                latency_ms=elapsed_ms,
                error=f"{type(exc).__name__}: {exc}",
            )
        raise
    if cost_tracker:
        cost_tracker.add_entry(
            feature="trend generation + final analysis report (combined)",
            provider="openai",
            model="gpt-4.1-mini",
            endpoint="responses.stream",
            status="success",
            response=response,
            latency_ms=elapsed_ms,
        )
    return result


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


def _upload_public_pdf(
    pdf_bytes: bytes,
    filename: str,
    endpoints: tuple[str, ...] = DEFAULT_SHARE_UPLOAD_ENDPOINTS,
) -> str | None:
    """Upload the PDF to a public file host and return the URL.

    The app needs an actual public URL, not a local file URI. We try 0x0.st
    first because it accepts multipart file uploads and returns a direct file
    URL in the response body. transfer.sh is used as a fallback.
    """
    if not endpoints:
        return None
    for endpoint in endpoints:
        try:
            if "transfer.sh" in endpoint:
                resp = requests.put(
                    f"{endpoint.rstrip('/')}/{filename}",
                    data=pdf_bytes,
                    headers={
                        "Content-Type": "application/pdf",
                        "User-Agent": "Beacon AI/1.0",
                    },
                    timeout=20,
                )
            else:
                resp = requests.post(
                    endpoint,
                    files={"file": (filename, pdf_bytes, "application/pdf")},
                    headers={"User-Agent": "Beacon AI/1.0"},
                    timeout=20,
                )
            resp.raise_for_status()
            value = resp.text.strip()
            if value.startswith(("http://", "https://")):
                return value
        except Exception:  # noqa: BLE001
            continue
    return None


def build_trend_analysis_report(
    time_range: str,
    region: str,
    industry: str,
    trend_data: list[dict],
    research_context: object | None,
    api_key: str | None = None,
    output_dir: Path | None = None,
    precomputed_report_markdown: str | None = None,
    cost_tracker: CostRunTracker | None = None,
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

    if precomputed_report_markdown:
        # Caller already has a report -- e.g. from call_combined_trends_and_report, which
        # generates it alongside trend_data in one pass. Skip the extra OpenAI round-trip.
        report_markdown = precomputed_report_markdown
    elif api_key:
        try:
            report_markdown = _live_report_markdown(
                api_key,
                time_range,
                region,
                industry,
                research_context,
                trend_data,
                cost_tracker=cost_tracker,
            )
        except Exception:
            report_markdown = _sample_report_markdown(time_range, region, industry, research_context, trend_data)
    else:
        report_markdown = _sample_report_markdown(time_range, region, industry, research_context, trend_data)

    combined_markdown = _combined_markdown(report_markdown, trend_data, research_context)
    html_report = render_final_analysis_html(
        report_markdown,
        combined_markdown,
        trend_data,
        research_context,
        timestamp,
        region,
        industry,
    )
    html_path = output_root / f"{base_name}_final.html"
    pdf_bytes = markdown_to_pdf_bytes(combined_markdown, title=f"Beacon AI final analysis - {industry} in {region}")
    pdf_path.write_bytes(pdf_bytes)
    share_url = _upload_public_pdf(pdf_bytes, pdf_path.name)

    report_path.write_text(report_markdown, encoding="utf-8")
    combined_path.write_text(combined_markdown, encoding="utf-8")
    html_path.write_text(html_report, encoding="utf-8")

    return TrendAnalysisResult(
        report_markdown=report_markdown,
        combined_markdown=combined_markdown,
        html_report=html_report,
        report_path=_relative_or_absolute(report_path),
        combined_path=_relative_or_absolute(combined_path),
        html_path=_relative_or_absolute(html_path),
        pdf_path=_relative_or_absolute(pdf_path),
        pdf_bytes=pdf_bytes,
        share_url=share_url,
        generated_at=timestamp,
    )
