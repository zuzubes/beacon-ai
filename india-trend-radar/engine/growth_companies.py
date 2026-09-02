"""
Growing-companies and social-signal engine for Beacon AI's Sub-Trend Drill-Down.

Two independent LLM-backed lookups, both following the mock/live split used
throughout this engine (see trends.py, news.py):

  - companies growing in a region for a given sub-trend/sector, each with a
    stated growth driver
  - "social signal" color for the same sub-trend: trending TikTok/Instagram
    hashtags and representative Reddit post summaries

The social-signal lookup has no real TikTok/Instagram/Reddit API behind it --
per the product brief this is explicitly an LLM estimate, not a live fetch.
Every result from this module carries is_sample/is_estimate framing so the UI
can label it honestly, matching the app's existing "sample data" pattern.
"""

from __future__ import annotations

import hashlib
import json
import random
from datetime import date, timedelta

MODEL = "gpt-4.1-mini"

_NAME_PREFIXES = [
    "Nova", "Terra", "Vertex", "Bright", "North Star", "Delta", "Orbit", "Summit",
    "Clear", "Pulse", "Meridian", "Anchor", "Silver Peak", "Ridge", "Harbor", "Ember",
    "Loop", "Foundry", "Beacon", "Cardinal", "Lumen", "Cascade",
]
_NAME_SUFFIXES = [
    "Labs", "Works", "Collective", "Group", "Ventures", "Systems", "Studio",
    "Partners", "Technologies", "Commerce",
]

_GROWTH_DRIVER_TEMPLATES = [
    "Riding demand for {sub_trend} in {region}, with distribution partnerships accelerating reach in {industry}.",
    "Early mover on {sub_trend}; {region} customers are switching from legacy {industry} providers.",
    "Product-led growth in the {sub_trend} niche, with word-of-mouth adoption spreading across {region}'s {industry} buyers.",
    "Raised growth capital to scale {sub_trend} capacity serving {region}'s {industry} demand.",
    "Benefiting from regulatory or infrastructure tailwinds around {sub_trend} that are reshaping {industry} in {region}.",
]

_HASHTAG_BANK = [
    "trending", "musthave", "viral", "fyp", "smallbusiness", "innovation",
    "startuplife", "growth", "founders", "consumertrends",
]

_REDDIT_SUBREDDITS = ["r/startups", "r/Entrepreneur", "r/investing", "r/technology", "r/business"]


def _seed_from(*parts: str) -> random.Random:
    key = "|".join(parts)
    h = hashlib.sha256(key.encode("utf-8")).hexdigest()
    return random.Random(int(h[:16], 16))


def _slug_tag(text: str) -> str:
    return "".join(ch for ch in text if ch.isalnum()) or "trend"


def generate_mock_companies(
    sub_trend_name: str, industry: str, region: str, count: int = 20
) -> list[dict]:
    """Deterministic, seeded sample list -- same inputs -> same output, clearly
    marked is_sample=True so it's never mistaken for a real company list."""
    sub_trend_label = sub_trend_name.strip() or "this space"
    industry_label = industry.strip() or "the sector"
    region_label = region.strip() or "the region"
    rng = _seed_from(sub_trend_label, industry_label, region_label, "companies")

    companies: list[dict] = []
    used_names: set[str] = set()
    while len(companies) < count:
        name = f"{rng.choice(_NAME_PREFIXES)} {rng.choice(_NAME_SUFFIXES)}"
        if name in used_names:
            continue
        used_names.add(name)
        template = rng.choice(_GROWTH_DRIVER_TEMPLATES)
        reason = template.format(sub_trend=sub_trend_label, region=region_label, industry=industry_label)
        companies.append(
            dict(
                name=f"{name} (sample)",
                growth_reason=reason,
                growth_pct=round(rng.uniform(20, 300), 0),
                is_sample=True,
            )
        )
    return companies


def generate_mock_social_signals(sub_trend_name: str, industry: str, region: str) -> dict:
    """Deterministic sample hashtags/Reddit signals, matching generate_mock_companies'
    seeded pattern. Always is_sample=True -- never confused with the (also-estimated,
    but at least model-generated) live output."""
    sub_trend_label = sub_trend_name.strip() or "this space"
    industry_label = industry.strip() or "this sector"
    rng = _seed_from(sub_trend_label, industry_label, region, "social")
    base_tag = _slug_tag(sub_trend_label)

    tiktok_hashtags = [f"#{base_tag}"] + [f"#{base_tag}{tag}" for tag in rng.sample(_HASHTAG_BANK, k=4)]
    instagram_hashtags = [f"#{base_tag}"] + [f"#{tag}{base_tag}" for tag in rng.sample(_HASHTAG_BANK, k=4)]

    reddit_signals = [
        dict(
            title=f"Anyone else noticing {sub_trend_label.lower()} everywhere right now? (sample)",
            subreddit=rng.choice(_REDDIT_SUBREDDITS),
            why_relevant=f"Illustrates rising community interest in {sub_trend_label.lower()} within {industry_label}.",
        )
        for _ in range(3)
    ]

    return dict(
        tiktok_hashtags=tiktok_hashtags,
        instagram_hashtags=instagram_hashtags,
        reddit_signals=reddit_signals,
        is_sample=True,
    )


# ---------------------------------------------------------------------------
# Live mode (OpenAI API)
# ---------------------------------------------------------------------------

COMPANIES_PROMPT_TEMPLATE = """You are a research analyst for a VC fund partner scouting investable \
companies for a specific sub-trend.

Sub-trend: {sub_trend}
Industry / Sector: {industry}
Region: {region}

Research context:
{research_context}

List up to {count} real, currently operating companies that are growing in {region} within this \
sub-trend / sector. Prefer companies you have reasonably high confidence actually exist and are \
active; do not pad the list with invented names to reach {count} if you are not confident -- fewer, \
accurate entries are better than a padded list.

For each company give a concrete 1-2 sentence reason it is growing (what specifically is driving \
demand, distribution, or adoption -- not a generic statement).

Respond with ONLY valid JSON (no markdown fences, no commentary), an array of objects, each shaped:
{{
  "name": string,
  "growth_reason": string (1-2 sentences, specific),
  "growth_pct": number or null (approximate YoY growth/momentum if you have a reasonable estimate, else null)
}}
"""

SOCIAL_SIGNALS_PROMPT_TEMPLATE = """You are estimating social-media chatter for a VC research tool. \
This is a directional estimate based on your training knowledge, not a live data pull.

Sub-trend: {sub_trend}
Industry / Sector: {industry}
Region: {region}
Today's date: {today}
Requested recency window: {time_range} (i.e. only the period from {window_start} to {today})

Every post idea, hashtag, and "why it's relevant" note must read as current within that window --
do not reference a specific past year (e.g. "in 2024") or any event/dataset that would date it \
outside the requested window.

Give:
- 5 trending or plausible TikTok hashtags related to this sub-trend
- 5 trending or plausible Instagram hashtags related to this sub-trend
- 3 representative Reddit post ideas (title + subreddit + why it's relevant) that capture the kind \
of discussion this sub-trend is generating right now, within the requested window

Respond with ONLY valid JSON (no markdown fences, no commentary), shaped exactly:
{{
  "tiktok_hashtags": [string, ...],
  "instagram_hashtags": [string, ...],
  "reddit_signals": [{{"title": string, "subreddit": string, "why_relevant": string}}, ...]
}}
"""


def _extract_text(response) -> str:
    if getattr(response, "status", None) == "incomplete":
        reason = getattr(getattr(response, "incomplete_details", None), "reason", "unknown")
        raise RuntimeError(f"response truncated by the API before it finished ({reason})")
    text = getattr(response, "output_text", "") or ""
    if not text:
        chunks = []
        for item in getattr(response, "output", []) or []:
            for content in getattr(item, "content", []) or []:
                if getattr(content, "type", "") == "output_text":
                    chunks.append(getattr(content, "text", ""))
        text = "".join(chunks)
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
    return text.strip()


def _parse_json(text: str, expected_type: type) -> object:
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"could not parse the model's JSON response ({exc})") from exc
    if not isinstance(data, expected_type):
        raise ValueError(f"Expected a JSON {expected_type.__name__}")
    return data


def call_live_companies(
    sub_trend_name: str,
    industry: str,
    region: str,
    api_key: str,
    research_context: str | None = None,
    count: int = 20,
) -> list[dict]:
    """Calls the OpenAI API for a live list of growing companies. Raises on failure --
    callers should fall back to generate_mock_companies, matching trends.py's pattern."""
    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    prompt = COMPANIES_PROMPT_TEMPLATE.format(
        sub_trend=sub_trend_name or "General",
        industry=industry or "General",
        region=region or "Global",
        research_context=research_context or "- Not available",
        count=count,
    )
    response = client.responses.create(model=MODEL, input=prompt, max_output_tokens=4000)
    data = _parse_json(_extract_text(response), list)

    normalized = []
    for item in data:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        if not name:
            continue
        normalized.append(
            dict(
                name=name,
                growth_reason=str(item.get("growth_reason") or "").strip(),
                growth_pct=item.get("growth_pct"),
                is_sample=False,
            )
        )
    return normalized[:count]


_TIME_RANGE_DAYS = {
    "Past 3 days": 3,
    "Past 1 week": 7,
    "Past 2 weeks": 14,
    "Past 1 month": 30,
}


def call_live_social_signals(
    sub_trend_name: str, industry: str, region: str, api_key: str, time_range: str = "Past 1 month"
) -> dict:
    """Calls the OpenAI API for estimated social-media signal color. Raises on failure --
    callers should fall back to generate_mock_social_signals."""
    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    today = date.today()
    window_start = today - timedelta(days=_TIME_RANGE_DAYS.get(time_range, 30))
    prompt = SOCIAL_SIGNALS_PROMPT_TEMPLATE.format(
        sub_trend=sub_trend_name or "General",
        industry=industry or "General",
        region=region or "Global",
        today=today.isoformat(),
        time_range=time_range or "Past 1 month",
        window_start=window_start.isoformat(),
    )
    response = client.responses.create(model=MODEL, input=prompt, max_output_tokens=1500)
    data = _parse_json(_extract_text(response), dict)

    return dict(
        tiktok_hashtags=[str(t).strip() for t in data.get("tiktok_hashtags", []) if str(t).strip()],
        instagram_hashtags=[str(t).strip() for t in data.get("instagram_hashtags", []) if str(t).strip()],
        reddit_signals=[
            dict(
                title=str(r.get("title", "")).strip(),
                subreddit=str(r.get("subreddit", "")).strip(),
                why_relevant=str(r.get("why_relevant", "")).strip(),
            )
            for r in data.get("reddit_signals", [])
            if isinstance(r, dict) and str(r.get("title", "")).strip()
        ],
        is_sample=False,
    )
