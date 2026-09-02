"""
News signals engine: produces the "data relevant signals" article feed.

- mock mode: deterministic sample article cards, clearly labeled as sample
  data so they are never mistaken for real reporting.
- live mode: calls NewsAPI.org's /v2/everything endpoint with the user's key.
  If NewsAPI cannot return at least 5 articles, falls back to Currents Search
  API and still returns a live article list when possible.
"""

from __future__ import annotations

import hashlib
import os
import random
import re
from datetime import datetime, timedelta, timezone
from typing import Iterable

import requests

_STOPWORD_LEAD_INS = {
    "the", "a", "an", "how", "why", "what", "who", "when", "where", "this",
    "these", "those", "its", "their", "his", "her", "your", "our", "as", "by",
    "and", "or", "but", "so", "if", "yet", "nor", "in", "on", "at", "to", "for",
}

# Fictional, clearly-sample outlet names for mock mode (never real publishers,
# so sample cards can't be mistaken for real articles from real outlets).
MOCK_SOURCES = [
    "Signal Wire (sample)",
    "Cross-Border Desk (sample)",
    "Asia Capital Digest (sample)",
    "Frontier Markets Brief (sample)",
    "TechFlow Asia (sample)",
    "Emerging Markets Ledger (sample)",
]

TITLE_TEMPLATES = [
    "{industry} deal activity picks up as {region} firms look at {geo}",
    "{region} {industry} moves start to matter for {geo}",
    "{company}: {industry} momentum builds in {region}",
    "Capital moves into {geo}-based {industry} startups as {region} supply shifts",
    "{region} {industry} trends are reshaping the view from {geo}",
    "{region} firms revisit {geo} sourcing as {industry} deals rise",
    "Policy changes in {region} could change {industry} economics in {geo}",
    "Three {industry} signals from {region} to watch this quarter",
]

TAG_POOL = [
    "Deal Activity", "Policy & Regulation", "Supply Chain", "Capital Markets",
    "M&A", "Manufacturing", "Cross-Border", "Early-Stage",
]

_FILLER_PHRASES = (
    "explainer:",
    "what ",
    "could",
    "worth tracking",
    "worth watching",
    "the view from",
)


def _polish_sample_text(text: str) -> str:
    value = (text or "").strip()
    if not value:
        return value
    for phrase in _FILLER_PHRASES:
        value = re.sub(re.escape(phrase), "", value, flags=re.IGNORECASE)
    value = re.sub(r"\s{2,}", " ", value)
    value = re.sub(r"\s+,", ",", value)
    value = value.strip(" ,;:-")
    if value and value[0].islower():
        value = value[0].upper() + value[1:]
    return value


def _seed_from(*parts: str) -> random.Random:
    key = "|".join(parts)
    h = hashlib.sha256(key.encode("utf-8")).hexdigest()
    return random.Random(int(h[:16], 16))


def _parse_domains(source_domains: str | Iterable[str] | None) -> str | None:
    if not source_domains:
        return None
    if isinstance(source_domains, str):
        raw_items = source_domains.replace(" ", ",").split(",")
    else:
        raw_items = list(source_domains)
    domains = [item.strip() for item in raw_items if item and item.strip()]
    return ",".join(domains) or None


def _load_currentnews_api_key() -> str:
    return (
        os.getenv("CURRENTNEWS_API_KEY", "")
        or os.getenv("CURRENT_NEWS_API_KEY", "")
        or os.getenv("CURRENTS_API_KEY", "")
        or os.getenv("CURRENTNEWSAPI_KEY", "")
    )


def generate_mock_news(company: str, time_range: str, region: str, industry: str, count: int = 10) -> list[dict]:
    """Deterministic sample article cards, matching the query inputs.

    The `company` argument is intentionally ignored so sample article copy never
    mentions the entered company name.
    """
    industry_label = industry.strip() or "the sector"
    geo = "India"
    region_label = region if region != "US & China (Both)" else "the US and China"

    rng = _seed_from(company, time_range, region, industry_label, "news")
    now = datetime.utcnow()

    articles = []
    for i in range(count):
        template = rng.choice(TITLE_TEMPLATES)
        title = template.format(
            industry=industry_label, region=region_label, geo=geo, company="Sector"
        )
        title = _polish_sample_text(title)
        source = rng.choice(MOCK_SOURCES)
        hours_ago = rng.randint(1, 72)
        tags = rng.sample(TAG_POOL, k=rng.randint(2, 3))
        articles.append(
            dict(
                title=title,
                source=source,
                published_at=(now - timedelta(hours=hours_ago)).isoformat() + "Z",
                hours_ago=hours_ago,
                tags=tags,
                url=None,
                is_sample=True,
            )
        )
    articles.sort(key=lambda a: a["hours_ago"])
    return articles


def _extract_topic_keywords(title: str, description: str | None, industry: str, limit: int = 3) -> list[str]:
    """NewsAPI doesn't return topic tags, so derive lightweight ones from capitalized
    phrases in the title/description (proper nouns, acronyms, named entities) -- the same
    trick most "auto-tagged" news feeds use in the absence of a real classifier."""
    text = f"{title or ''}. {description or ''}"
    # runs of 1-3 consecutive capitalized words, e.g. "New Delhi", "Reserve Bank of India" (partial)
    candidates = re.findall(r"\b[A-Z][a-zA-Z0-9&'.]*(?:\s+[A-Z][a-zA-Z0-9&'.]*){0,2}\b", text)

    keywords: list[str] = []
    seen: set[str] = set()
    for phrase in candidates:
        words = phrase.split()
        # a mid-sentence period (e.g. "Alaska." followed by "By ...") means the regex has
        # accidentally bridged two sentences into one candidate -- reject those outright.
        if any(w.rstrip(".").lower() in _STOPWORD_LEAD_INS or (w.endswith(".") and w != words[-1]) for w in words):
            continue
        normalized = phrase.strip().rstrip(".")
        key = normalized.lower()
        if not normalized or key in seen or len(normalized) < 3:
            continue
        seen.add(key)
        keywords.append(normalized)
        if len(keywords) >= limit:
            break

    if not keywords and industry.strip():
        keywords.append(industry.strip())
    return keywords


def _region_keywords(region: str) -> list[str]:
    """Terms used to *rank* results toward the app's US/China focus. NOT used as a hard
    NewsAPI filter -- combining it with the industry terms via a strict AND was tested and
    found to return almost nothing for a specific industry + region + short time window (real
    coverage is too sparse), or to silently drop the industry requirement and let through
    off-topic articles that merely contained a common region word like "American". A soft
    ranking boost keeps every result on-topic (industry stays hard-required) while still
    preferring region-relevant coverage when it exists."""
    if region == "China":
        return ["china", "chinese"]
    if region == "United States":
        return ["us", "u.s.", "united states", "american", "america"]
    return ["china", "chinese", "us", "u.s.", "united states", "american", "america"]


def _fetch_newsapi_page(query: str, from_date: str, to_date: str, sort_by: str, page_size: int, api_key: str, domains: str | None) -> list[dict]:
    params = {
        "q": query,
        "from": from_date,
        "to": to_date,
        "language": "en",
        "searchIn": "title,description",
        "sortBy": sort_by,
        "pageSize": page_size,
        "apiKey": api_key,
    }
    if domains:
        params["domains"] = domains
    resp = requests.get("https://newsapi.org/v2/everything", params=params, timeout=15)
    resp.raise_for_status()
    payload = resp.json()
    if payload.get("status") != "ok":
        raise RuntimeError(payload.get("message", "NewsAPI request failed"))
    return payload.get("articles", [])


def _fetch_currentnews_page(keywords: str, page_number: int, page_size: int, api_key: str, country: str | None = None) -> list[dict]:
    params = {
        "keywords": keywords,
        "language": "en",
        "page_number": page_number,
        "page_size": page_size,
        "apiKey": api_key,
    }
    if country:
        params["country"] = country
    resp = requests.get("https://api.currentsapi.services/v1/search", params=params, timeout=15)
    resp.raise_for_status()
    payload = resp.json()
    if payload.get("status") != "ok":
        raise RuntimeError(payload.get("message", "Currents request failed"))
    return payload.get("news", []) or payload.get("articles", [])


def call_live_news(
    time_range: str,
    industry: str,
    api_key: str,
    region: str = "US & China (Both)",
    source_domains: str | Iterable[str] | None = None,
    count: int = 5,
) -> list[dict]:
    """Calls NewsAPI.org's /v2/everything endpoint, combining relevance and popularity so the
    feed favors articles that are both closely on-topic AND widely covered, rather than just
    whichever NewsAPI's single 'relevancy' heuristic ranks first. Raises on failure."""
    days_map = {
        "Past 3 days": 3,
        "Past 1 week": 7,
        "Past 2 weeks": 14,
        "Past 1 month": 30,
    }
    days = days_map.get(time_range, 30)
    now = datetime.utcnow()
    from_date = (now - timedelta(days=days)).strftime("%Y-%m-%d")
    to_date = now.strftime("%Y-%m-%d")

    # Each significant word of the industry is prefixed with "+" to REQUIRE it (NewsAPI's
    # default, un-prefixed matching is a fuzzy "should match" -- it still returns results even
    # when a term is absent, which let completely off-topic articles through). A quoted exact
    # phrase was tried too and was far too restrictive (~1 article/week for a two-word
    # industry like "Climate Tech"); requiring each word separately keeps results genuinely
    # on-topic without demanding the exact phrase appear verbatim.
    industry_label = re.sub(r"[_-]+", " ", industry).strip() or industry
    # Drop tokens with no letters/digits (e.g. a lone "&" from "Food & Beverages" splitting
    # off its own space-separated token) -- a bare "+&" required term breaks NewsAPI's query.
    industry_words = [w for w in re.findall(r"[\w&-]+", industry_label) if re.search(r"\w", w)] or ["India"]
    query = " ".join(f"+{w}" for w in industry_words)
    # Currents' /search takes a plain keyword string -- it doesn't support NewsAPI's "+"
    # required-term operator, so this is the unprefixed word list instead of `query`.
    keyword = " ".join(industry_words)
    domains = _parse_domains(source_domains)
    region_terms = _region_keywords(region)

    # Fetch a larger pool sorted two different ways, then combine ranks -- an article that
    # shows up near the top of BOTH lists is both relevant and popular, so it should surface
    # first. One that only appears in one list still counts, just ranked lower.
    fetch_size = max(count * 2, 15)
    ranked_by_url: dict[str, dict] = {}
    errors: list[str] = []
    for sort_by in ("relevancy", "popularity"):
        try:
            page = _fetch_newsapi_page(query, from_date, to_date, sort_by, fetch_size, api_key, domains)
        except Exception as exc:  # noqa: BLE001
            # If one sort mode fails (rate limit, transient error), fall back to whichever
            # mode still works rather than failing the whole feed.
            errors.append(f"NewsAPI {sort_by} failed: {type(exc).__name__}: {exc}")
            page = []
        for rank, item in enumerate(page):
            key = item.get("url") or item.get("title") or str(rank)
            entry = ranked_by_url.setdefault(key, {"item": item, "ranks": []})
            entry["ranks"].append(rank)

    if not ranked_by_url:
        # Both sort modes failed outright -- try Currents before falling back to sample data.
        fallback_key = _load_currentnews_api_key()
        if not fallback_key:
            details = "; ".join(errors) if errors else "NewsAPI returned no results"
            raise RuntimeError(f"{details}; CURRENTNEWS_API_KEY was not found")

        currentnews_articles: list[dict] = []
        currentnews_query = keyword
        for page_number in (1, 2):
            try:
                currentnews_articles.extend(
                    _fetch_currentnews_page(
                        currentnews_query,
                        page_number=page_number,
                        page_size=count,
                        api_key=fallback_key,
                    )
                )
            except Exception as exc:  # noqa: BLE001
                errors.append(f"Currents page {page_number} failed: {type(exc).__name__}: {exc}")
                continue

        if not currentnews_articles:
            details = "; ".join(errors) if errors else "NewsAPI returned no results and Currents returned no results"
            raise RuntimeError(details)

        return _normalize_currents_articles(currentnews_articles, industry_label, count)

    def combined_score(entry: dict) -> float:
        ranks = entry["ranks"]
        item = entry["item"]
        score = sum(ranks) / len(ranks)
        # articles appearing in both lists get a bonus (favors relevant AND popular)
        if len(ranks) > 1:
            score -= 2
        # soft preference for articles that actually mention the selected region
        text = f"{item.get('title', '')} {item.get('description', '')}".lower()
        if any(term in text for term in region_terms):
            score -= 1
        # NewsAPI's "+word" operator matches full article body text, so a piece that only
        # mentions the industry deep in its body (not in the title/description a reader
        # actually sees) can still outrank genuinely on-topic articles -- push those down.
        if industry_words and not any(w.lower() in text for w in industry_words):
            score += 100
        return score

    ordered_items = [
        entry["item"]
        for entry in sorted(ranked_by_url.values(), key=combined_score)
    ][:count]

    now = datetime.utcnow()
    articles = []
    for item in ordered_items:
        published_at = item.get("publishedAt")
        hours_ago = None
        if published_at:
            try:
                dt = datetime.strptime(published_at, "%Y-%m-%dT%H:%M:%SZ")
                hours_ago = int((now - dt).total_seconds() // 3600)
            except ValueError:
                hours_ago = None
        title = item.get("title", "Untitled")
        description = item.get("description")
        articles.append(
            dict(
                title=title,
                source=(item.get("source") or {}).get("name", "Unknown source"),
                published_at=published_at,
                hours_ago=hours_ago if hours_ago is not None else 9999,
                tags=_extract_topic_keywords(title, description, industry),
                url=item.get("url"),
                urlToImage=item.get("urlToImage"),
                is_sample=False,
            )
        )

    if len(articles) >= count:
        return articles[:count]

    fallback_key = _load_currentnews_api_key()
    if not fallback_key:
        return articles

    currentnews_articles: list[dict] = []
    for page_number in (1, 2):
        try:
            currentnews_articles.extend(
                _fetch_currentnews_page(
                    keyword,
                    page_number=page_number,
                    page_size=count,
                    api_key=fallback_key,
                )
            )
        except Exception as exc:  # noqa: BLE001
            errors.append(f"Currents page {page_number} failed: {type(exc).__name__}: {exc}")
            continue

    if not currentnews_articles:
        if articles:
            return articles
        details = "; ".join(errors) if errors else "NewsAPI returned no results and Currents returned no results"
        raise RuntimeError(details)

    return _normalize_currents_articles(currentnews_articles, industry_label, count)


def _normalize_currents_articles(currents_articles: list[dict], industry: str, count: int) -> list[dict]:
    now = datetime.now(timezone.utc)
    # Currents' /search keyword matching is loose and can surface completely off-topic
    # results (e.g. "safari tents" for "Food & Beverages"), so filter for on-topic articles
    # first and only fall back to the raw pool if nothing actually mentions the industry.
    relevance_words = [w.lower() for w in re.findall(r"[\w&-]+", industry) if re.search(r"\w", w)]
    on_topic = []
    off_topic = []
    for index, item in enumerate(currents_articles):
        title = item.get("title") or "Untitled"
        description = item.get("description")
        published = item.get("published")
        hours_ago = 9999
        if published:
            parsed = None
            for fmt in ("%Y-%m-%d %H:%M:%S %z", "%Y-%m-%d %H:%M:%S"):
                try:
                    parsed = datetime.strptime(published, fmt)
                    break
                except ValueError:
                    continue
            if parsed is not None:
                if parsed.tzinfo is not None:
                    parsed = parsed.astimezone(timezone.utc)
                else:
                    parsed = parsed.replace(tzinfo=timezone.utc)
                hours_ago = int((now - parsed).total_seconds() // 3600)
        entry = dict(
            title=title,
            source=item.get("author") or (item.get("source") or "Currents"),
            published_at=published,
            hours_ago=hours_ago,
            tags=_extract_topic_keywords(title, description, industry),
            url=item.get("url"),
            urlToImage=item.get("image"),
            is_sample=False,
        )
        text = f"{title} {description or ''}".lower()
        if relevance_words and any(word in text for word in relevance_words):
            on_topic.append(entry)
        else:
            off_topic.append(entry)
    articles = on_topic or off_topic
    articles.sort(key=lambda a: a["hours_ago"])
    deduped = []
    seen = set()
    for article in articles:
        key = article.get("url") or article.get("title")
        if key in seen:
            continue
        seen.add(key)
        deduped.append(article)
    return deduped[:count]
