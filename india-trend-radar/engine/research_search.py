"""
Research search preprocessing for Beacon AI.

This module runs a live web search before the OpenAI trend call, extracts
keywords from search snippets, writes the raw response to disk, and pulls in
local research reports for sub-trend grounding.
"""

from __future__ import annotations

import json
import logging
import os
import re
from collections import Counter
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse

import requests

logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT_DIR = ROOT_DIR.parent
DEFAULT_REPORT_DIR = REPO_ROOT_DIR / "data" / "raw" / "reports"
DEFAULT_OUTPUT_DIR = ROOT_DIR / "raw" / "research"
SERPER_ENDPOINT = "https://google.serper.dev/search"
SERPAPI_ENDPOINT = "https://serpapi.com/search"
TAVILY_ENDPOINT = "https://api.tavily.com/search"
DEEPL_FREE_ENDPOINT = "https://api-free.deepl.com/v2/translate"
DEEPL_PRO_ENDPOINT = "https://api.deepl.com/v2/translate"

STOPWORDS = {
    "about",
    "after",
    "also",
    "among",
    "and",
    "are",
    "as",
    "between",
    "before",
    "both",
    "but",
    "can",
    "during",
    "for",
    "from",
    "have",
    "into",
    "more",
    "most",
    "new",
    "not",
    "of",
    "on",
    "or",
    "over",
    "past",
    "per",
    "selected",
    "than",
    "that",
    "the",
    "their",
    "this",
    "trend",
    "trends",
    "trending",
    "with",
    "year",
    "years",
}


ENV_FILE_PATHS = (
    Path(__file__).with_name(".env"),
    ROOT_DIR / ".env",
    REPO_ROOT_DIR / ".env",
)

# What this loader last wrote into os.environ, per key. A rotated key in .env has to
# be able to replace the stale value a long-running process loaded at startup, but a
# value set by anyone else -- exported in the launching shell, or assigned at runtime --
# must still win. Comparing against what we wrote distinguishes the two: if the current
# value is still ours, it is safe to refresh; if it changed, someone else owns it now.
_ENV_VALUES_FROM_FILE: dict[str, str] = {}


def _load_env_file() -> None:
    """Loads .env into os.environ, refreshing values this loader previously set.

    Called at import and again on each Streamlit rerun, so editing .env (e.g.
    rotating an OpenAI key) takes effect without restarting the server.
    """
    for env_path in ENV_FILE_PATHS:
        if not env_path.exists():
            continue

        for line in env_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            key = key.strip()
            if not key:
                continue
            current = os.environ.get(key)
            if current is not None and current != _ENV_VALUES_FROM_FILE.get(key):
                continue  # set by the shell or at runtime -- that value wins over the file
            value = value.strip().strip('"').strip("'")
            if current != value:
                logger.info("env: loaded %s from %s", key, env_path)
            os.environ[key] = value
            _ENV_VALUES_FROM_FILE[key] = value


_load_env_file()


@dataclass(frozen=True)
class SearchHit:
    title: str
    url: str
    snippet: str
    position: int
    source: str = "web"
    provider: str = "serper"


@dataclass(frozen=True)
class ReportMatch:
    path: str
    title: str
    excerpt: str
    score: int


@dataclass(frozen=True)
class ResearchContext:
    query: str
    countries: list[str]
    language: str
    time_range: str
    search_window: str
    providers_used: list[str]
    keywords: list[str]
    hits: list[SearchHit]
    report_matches: list[ReportMatch]
    output_path: str
    prompt: str
    knowledge_graph: dict | None = None


def _region_to_countries(region: str) -> list[str]:
    if region == "US & China (Both)":
        return ["us", "cn"]
    if region == "China":
        return ["cn"]
    return ["us"]


def _time_range_days(time_range: str) -> int:
    mapping = {
        "Past 3 days": 3,
        "Past 1 week": 7,
        "Past 2 weeks": 14,
        "Past 1 month": 30,
    }
    return mapping.get(time_range, 7)


def _build_query(industry: str, region: str, time_range: str) -> tuple[str, str]:
    days = _time_range_days(time_range)
    end_date = date.today()
    start_date = end_date - timedelta(days=days)
    region_label = region if region != "US & China (Both)" else "US and China"
    query = f"{industry.strip()} trends 2026 {region_label} after:{start_date.isoformat()} before:{end_date.isoformat()}"
    return query, f"{start_date.isoformat()}..{end_date.isoformat()}"


def _serper_request(api_key: str, query: str, country: str, language: str, page: int = 1) -> dict:
    payload = {
        "query": query,
        "page": page,
        "country": country,
        "lang": language,
        "gl": country,
        "hl": language,
        "tbs": "sbd:1",
        "autocorrect": False,
    }
    resp = requests.post(
        SERPER_ENDPOINT,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json=payload,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def _serpapi_request(api_key: str, query: str, country: str, language: str, page: int = 1) -> dict:
    params = {
        "engine": "google",
        "q": query,
        "page": page,
        "gl": country,
        "hl": language,
        "num": 10,
        "api_key": api_key,
        "tbs": "sbd:1",
    }
    resp = requests.get(SERPAPI_ENDPOINT, params=params, timeout=20)
    resp.raise_for_status()
    return resp.json()


def _serpapi_baidu_request(api_key: str, query: str, page: int = 1) -> dict:
    """China-region search source. See https://serpapi.com/baidu-search-api."""
    params = {
        "engine": "baidu",
        "q": query,
        "pn": (page - 1) * 10,
        "api_key": api_key,
    }
    resp = requests.get(SERPAPI_ENDPOINT, params=params, timeout=20)
    resp.raise_for_status()
    return resp.json()


def _serpapi_knowledge_graph_request(api_key: str, query: str, language: str = "zh-cn") -> dict:
    """China-region structured-entity source. The `knowledge_graph` object is returned as part
    of a normal Google-engine SerpApi response (Baidu's engine does not carry one), see
    https://serpapi.com/knowledge-graph-results."""
    params = {
        "engine": "google",
        "q": query,
        "hl": language,
        "api_key": api_key,
    }
    resp = requests.get(SERPAPI_ENDPOINT, params=params, timeout=20)
    resp.raise_for_status()
    return resp.json().get("knowledge_graph") or {}


def _extract_knowledge_graph_facts(raw: dict) -> dict:
    if not raw:
        return {}
    facts = {}
    for key in ("title", "type", "subtitle", "description"):
        value = raw.get(key)
        if isinstance(value, str) and value.strip():
            facts[key] = value.strip()
    return facts


def _deepl_endpoint(api_key: str) -> str:
    return DEEPL_FREE_ENDPOINT if api_key.strip().endswith(":fx") else DEEPL_PRO_ENDPOINT


def _deepl_translate_batch(api_key: str, texts: list[str]) -> list[str]:
    """Translates a batch of strings to English via DeepL, preserving order and length.
    Empty strings pass through untouched; on any failure the originals are returned unchanged
    so a translation outage never breaks the research pipeline."""
    if not api_key or not any(t.strip() for t in texts):
        return texts
    try:
        resp = requests.post(
            _deepl_endpoint(api_key),
            headers={"Authorization": f"DeepL-Auth-Key {api_key}"},
            json={"text": texts, "target_lang": "EN"},
            timeout=30,
        )
        resp.raise_for_status()
        translations = resp.json().get("translations", [])
        if len(translations) != len(texts):
            return texts
        return [item.get("text") or original for item, original in zip(translations, texts)]
    except Exception:  # noqa: BLE001
        return texts


def _translate_hits_and_kg_to_english(
    api_key: str, hits: list[SearchHit], knowledge_graph: dict
) -> tuple[list[SearchHit], dict]:
    kg_keys = list(knowledge_graph.keys())
    batch = [hit.title for hit in hits] + [hit.snippet for hit in hits] + [knowledge_graph[k] for k in kg_keys]
    translated = _deepl_translate_batch(api_key, batch)
    n = len(hits)
    titles, snippets, kg_values = translated[:n], translated[n : 2 * n], translated[2 * n :]

    translated_hits = [
        SearchHit(
            title=titles[i],
            url=hit.url,
            snippet=snippets[i],
            position=hit.position,
            source=hit.source,
            provider=hit.provider,
        )
        for i, hit in enumerate(hits)
    ]
    translated_kg = dict(zip(kg_keys, kg_values))
    return translated_hits, translated_kg


def _tavily_request(api_key: str, query: str, country: str, time_range: str) -> dict:
    payload = {
        "query": query,
        "search_depth": "basic",
        "topic": "general",
        "max_results": 10,
        "include_answer": False,
        "include_raw_content": False,
        "country": _tavily_country_name(country),
        "time_range": _tavily_time_range(time_range),
        "auto_parameters": False,
    }
    resp = requests.post(
        TAVILY_ENDPOINT,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json=payload,
        timeout=20,
    )
    resp.raise_for_status()
    return resp.json()


def _parse_hits(payload: dict, country: str, provider: str) -> list[SearchHit]:
    candidates = payload.get("organic_results") or payload.get("organic") or payload.get("results") or []
    hits: list[SearchHit] = []
    for index, item in enumerate(candidates, start=1):
        title = str(item.get("title") or item.get("name") or "").strip()
        url = str(item.get("url") or item.get("link") or "").strip()
        snippet = str(item.get("snippet") or item.get("description") or item.get("content") or "").strip()
        if not (title or snippet or url):
            continue
        position = int(item.get("position") or index)
        hits.append(
            SearchHit(
                title=title,
                url=url,
                snippet=snippet,
                position=position,
                source=country,
                provider=provider,
            )
        )
    return hits


# Directory, social, and data-vendor domains that rank highly for "<company> official
# website" but are never the company's own site. Reading one of these yields a profile
# page with no stated sector focus (or a login wall), which downstream looks identical
# to "this company has no sector focus" -- so they are skipped as candidates.
AGGREGATOR_DOMAINS = frozenset({
    "angel.co", "apollo.io", "bloomberg.com", "cbinsights.com", "craft.co",
    "crunchbase.com", "dnb.com", "f6s.com", "facebook.com", "forbes.com",
    "glassdoor.com", "indeed.com", "instagram.com", "linkedin.com", "medium.com",
    "owler.com", "pitchbook.com", "privateequityinternational.com", "producthunt.com",
    "reddit.com", "rocketreach.co", "signalhire.com", "t.co", "tracxn.com",
    "twitter.com", "wellfound.com", "wikipedia.org", "x.com", "yahoo.com",
    "youtube.com", "zaubacorp.com", "zoominfo.com",
})


def _registrable_domain(url: str) -> str:
    netloc = urlparse(url).netloc.lower().split("@")[-1].split(":")[0]
    return netloc[4:] if netloc.startswith("www.") else netloc


def _is_aggregator(url: str) -> bool:
    domain = _registrable_domain(url)
    return any(domain == known or domain.endswith(f".{known}") for known in AGGREGATOR_DOMAINS)


def _alphanumeric(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def _looks_like_company_site(url: str, company_name: str) -> bool:
    """True when the domain plausibly belongs to the company (e.g. '12flags' ->
    12flags.com), which is a much stronger signal than search rank alone."""
    name = _alphanumeric(company_name)
    if not name:
        return False
    label = _alphanumeric(_registrable_domain(url).split(".")[0])
    if not label:
        return False
    return name in label or label in name


def _pick_official_website(hits: list[SearchHit], company_name: str) -> str | None:
    """Best candidate from one provider's hits, or None if it offered nothing usable
    (so the caller can fall through to the next provider)."""
    candidates = [hit.url for hit in hits if hit.url and not _is_aggregator(hit.url)]
    for url in candidates:
        if _looks_like_company_site(url, company_name):
            return url
    return candidates[0] if candidates else None


def find_official_website(
    company_name: str,
    serper_api_key: str | None = None,
    serp_api_key: str | None = None,
    tavily_api_key: str | None = None,
) -> str | None:
    """Best-effort company-name -> official homepage URL lookup, trying Serper, then
    SerpApi, then Tavily (same default provider priority used elsewhere in this module).

    Falls through to the next provider both when a provider errors and when it returns
    nothing usable -- a page of directory/profile links is as useless as no answer."""
    query = f"{company_name.strip()} official website"
    attempts = []
    if serper_api_key:
        attempts.append(lambda: _parse_hits(_serper_request(serper_api_key, query, "us", "en"), "us", "serper"))
    if serp_api_key:
        attempts.append(lambda: _parse_hits(_serpapi_request(serp_api_key, query, "us", "en"), "us", "serpapi"))
    if tavily_api_key:
        attempts.append(lambda: _parse_hits(_tavily_request(tavily_api_key, query, "us", "Past 1 month"), "us", "tavily"))
    for attempt in attempts:
        try:
            hits = attempt()
        except Exception as exc:  # noqa: BLE001
            logger.warning("find_official_website: provider call failed for %r: %s: %s", query, type(exc).__name__, exc)
            continue
        chosen = _pick_official_website(hits, company_name)
        logger.warning(
            "find_official_website: %r returned %d hits %s -> chose %s",
            query,
            len(hits),
            [hit.url for hit in hits[:5]],
            chosen or "nothing usable (all aggregator/profile links); trying next provider",
        )
        if chosen:
            return chosen
    return None


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z][a-zA-Z&/-]{2,}", text.lower())


def _extract_keywords_from_text(text: str, limit: int = 12) -> list[str]:
    words = [token for token in _tokens(text) if token not in STOPWORDS and len(token) > 3]
    counts = Counter(words)
    pairs = Counter(
        f"{a} {b}"
        for a, b in zip(words, words[1:])
        if a != b and a not in STOPWORDS and b not in STOPWORDS
    )
    ranked = [phrase for phrase, _ in pairs.most_common(limit)]
    ranked.extend(word for word, _ in counts.most_common(limit))
    deduped = []
    seen = set()
    for item in ranked:
        normalized = item.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(normalized)
        if len(deduped) >= limit:
            break
    return deduped


def _extract_report_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".txt", ".md"}:
        return path.read_text(encoding="utf-8", errors="ignore")
    if suffix == ".pdf":
        try:
            from pypdf import PdfReader
        except Exception:  # noqa: BLE001
            return ""
        reader = PdfReader(str(path))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    return ""


def _split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text.replace("\n", " "))
    return [part.strip() for part in parts if part.strip()]


def _score_report(text: str, keywords: Iterable[str]) -> int:
    lower = text.lower()
    score = 0
    for keyword in keywords:
        if keyword.lower() in lower:
            score += 1
    return score


def _load_report_matches(report_dir: Path, keywords: list[str], limit: int = 5) -> list[ReportMatch]:
    if not report_dir.exists():
        return []

    matches: list[ReportMatch] = []
    for path in sorted(report_dir.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix.lower() not in {".md", ".txt", ".pdf"}:
            continue
        text = _extract_report_text(path)
        if not text.strip():
            continue
        score = _score_report(text, keywords)
        if score <= 0:
            continue
        sentences = _split_sentences(text)
        excerpt = ""
        for sentence in sentences:
            if any(keyword.lower() in sentence.lower() for keyword in keywords):
                excerpt = sentence
                break
        if not excerpt:
            excerpt = text.strip().replace("\n", " ")[:400]
        matches.append(
            ReportMatch(
                # Absolute, not relative_to(ROOT_DIR) -- report_dir now lives at the repo root
                # (data/raw/reports), outside india-trend-radar/, so it isn't under ROOT_DIR.
                # An absolute path here still round-trips correctly through trend_analysis.py's
                # `(ROOT_DIR / match.path).resolve()` -- pathlib's join treats an absolute right
                # operand as an override, ignoring the left side.
                path=str(path.resolve()),
                title=path.stem.replace("_", " ").replace("-", " ").title(),
                excerpt=excerpt[:400],
                score=score,
            )
        )

    matches.sort(key=lambda item: (-item.score, item.title))
    return matches[:limit]


def _build_prompt(
    query: str,
    countries: list[str],
    language: str,
    time_range: str,
    search_window: str,
    providers_used: list[str],
    keywords: list[str],
    hits: list[SearchHit],
    report_matches: list[ReportMatch],
    knowledge_graph: dict | None = None,
) -> str:
    countries_label = ", ".join(countries) if countries else "global"
    providers_label = ", ".join(providers_used) if providers_used else "none"
    snippet_lines = []
    for hit in hits[:5]:
        snippet_lines.append(f"- {hit.title} | {hit.url} | {hit.snippet} [{hit.provider}]")
    if not snippet_lines:
        snippet_lines.append("- No live search snippets available.")

    report_lines = []
    for match in report_matches[:5]:
        report_lines.append(f"- {match.title} ({match.path}) | {match.excerpt}")
    if not report_lines:
        report_lines.append("- No local reports found in raw/reports.")

    kg_section = ""
    if knowledge_graph:
        kg_line = " | ".join(f"{k}: {v}" for k, v in knowledge_graph.items())
        kg_section = f"- Knowledge graph (SerpApi): {kg_line}\n"

    return (
        "Serper research context:\n"
        f"- Query: {query}\n"
        f"- Countries: {countries_label}\n"
        f"- Language: {language}\n"
        f"- Time range: {time_range} ({search_window})\n"
        f"- Providers used: {providers_label}\n"
        f"- Keywords extracted from snippets: {', '.join(keywords) if keywords else 'none'}\n"
        + kg_section
        + f"- Live snippets:\n" + "\n".join(snippet_lines) + "\n"
        f"- Local report cross-reference:\n" + "\n".join(report_lines) + "\n"
        "- Use the live snippets to identify macro, mega, and sub-trend signals.\n"
        "- Use the local reports to ground sub-trends and India-specific implications."
    )


def _tavily_country_name(country: str) -> str:
    mapping = {
        "us": "united states",
        "cn": "china",
    }
    return mapping.get(country.lower(), country.lower())


def _tavily_time_range(time_range: str) -> str:
    mapping = {
        "Past 3 days": "week",
        "Past 1 week": "week",
        "Past 2 weeks": "month",
        "Past 1 month": "month",
    }
    return mapping.get(time_range, "week")


def _try_serper(
    api_key: str, query: str, countries: list[str], language: str, raw_payloads: list[dict], providers_used: list[str]
) -> list[SearchHit]:
    hits: list[SearchHit] = []
    for country in countries:
        try:
            payload = _serper_request(api_key, query, country, language, page=1)
            raw_payloads.append({"provider": "serper", "country": country, "response": payload})
            provider_hits = _parse_hits(payload, country, "serper")
            hits.extend(provider_hits)
            if provider_hits and "serper" not in providers_used:
                providers_used.append("serper")
        except Exception as exc:  # noqa: BLE001
            raw_payloads.append({"provider": "serper", "country": country, "error": f"{type(exc).__name__}: {exc}"})
    return hits


def _try_serpapi_google(
    api_key: str, query: str, countries: list[str], language: str, raw_payloads: list[dict], providers_used: list[str]
) -> list[SearchHit]:
    hits: list[SearchHit] = []
    for country in countries:
        try:
            payload = _serpapi_request(api_key, query, country, language, page=1)
            raw_payloads.append({"provider": "serpapi", "country": country, "response": payload})
            provider_hits = _parse_hits(payload, country, "serpapi")
            hits.extend(provider_hits)
            if provider_hits and "serpapi" not in providers_used:
                providers_used.append("serpapi")
        except Exception as exc:  # noqa: BLE001
            raw_payloads.append({"provider": "serpapi", "country": country, "error": f"{type(exc).__name__}: {exc}"})
    return hits


def _try_tavily(
    api_key: str, query: str, countries: list[str], time_range: str, raw_payloads: list[dict], providers_used: list[str]
) -> list[SearchHit]:
    hits: list[SearchHit] = []
    for country in countries:
        try:
            payload = _tavily_request(api_key, query, country, time_range)
            raw_payloads.append({"provider": "tavily", "country": country, "response": payload})
            provider_hits = _parse_hits(payload, country, "tavily")
            hits.extend(provider_hits)
            if provider_hits and "tavily" not in providers_used:
                providers_used.append("tavily")
        except Exception as exc:  # noqa: BLE001
            raw_payloads.append({"provider": "tavily", "country": country, "error": f"{type(exc).__name__}: {exc}"})
    return hits


def _try_serpapi_baidu_and_knowledge_graph(
    api_key: str, query: str, raw_payloads: list[dict], providers_used: list[str]
) -> tuple[list[SearchHit], dict]:
    """China-region priority-1 source: Baidu search results plus a Google-engine knowledge-graph
    lookup for structured entity context. See module docstring links for both SerpApi endpoints."""
    knowledge_graph: dict = {}
    try:
        kg_raw = _serpapi_knowledge_graph_request(api_key, query)
        knowledge_graph = _extract_knowledge_graph_facts(kg_raw)
        raw_payloads.append({"provider": "serpapi-knowledge-graph", "country": "cn", "response": kg_raw})
    except Exception as exc:  # noqa: BLE001
        raw_payloads.append({"provider": "serpapi-knowledge-graph", "country": "cn", "error": f"{type(exc).__name__}: {exc}"})

    hits: list[SearchHit] = []
    try:
        payload = _serpapi_baidu_request(api_key, query, page=1)
        raw_payloads.append({"provider": "serpapi-baidu", "country": "cn", "response": payload})
        hits = _parse_hits(payload, "cn", "serpapi")
        if hits and "serpapi" not in providers_used:
            providers_used.append("serpapi")
    except Exception as exc:  # noqa: BLE001
        raw_payloads.append({"provider": "serpapi-baidu", "country": "cn", "error": f"{type(exc).__name__}: {exc}"})

    return hits, knowledge_graph


def build_research_context(
    industry: str,
    region: str,
    time_range: str,
    serper_api_key: str | None = None,
    serp_api_key: str | None = None,
    tavily_api_key: str | None = None,
    deepl_api_key: str | None = None,
    report_dir: Path | None = None,
) -> ResearchContext:
    query, search_window = _build_query(industry, region, time_range)
    countries = _region_to_countries(region)
    language = "en"
    hits: list[SearchHit] = []
    raw_payloads: list[dict] = []
    providers_used: list[str] = []
    knowledge_graph: dict = {}

    if region == "China":
        # Priority 1: SerpApi (Baidu search + knowledge graph)
        if serp_api_key:
            kg_hits, knowledge_graph = _try_serpapi_baidu_and_knowledge_graph(
                serp_api_key, query, raw_payloads, providers_used
            )
            hits.extend(kg_hits)

        # Priority 2: Serper -- only if the step above produced nothing. `not hits` is
        # re-evaluated at each step so the chain stops at the first provider that answers;
        # computing it once would let a later provider run even after an earlier one
        # succeeded, spending its quota for results already in hand.
        if not hits and serper_api_key:
            hits.extend(_try_serper(serper_api_key, query, countries, language, raw_payloads, providers_used))

        # Priority 3: Tavily
        if not hits and tavily_api_key:
            hits.extend(_try_tavily(tavily_api_key, query, countries, time_range, raw_payloads, providers_used))
    else:
        # Priority 1: Serper
        if serper_api_key:
            hits.extend(_try_serper(serper_api_key, query, countries, language, raw_payloads, providers_used))

        # Priority 2: SerpApi (Google)
        if not hits and serp_api_key:
            hits.extend(_try_serpapi_google(serp_api_key, query, countries, language, raw_payloads, providers_used))

        # Priority 3: Tavily
        if not hits and tavily_api_key:
            hits.extend(_try_tavily(tavily_api_key, query, countries, time_range, raw_payloads, providers_used))

    hits = sorted(hits, key=lambda item: item.position)
    deduped_hits: list[SearchHit] = []
    seen_urls = set()
    for hit in hits:
        key = hit.url or hit.title
        if key in seen_urls:
            continue
        seen_urls.add(key)
        deduped_hits.append(hit)
    hits = deduped_hits[:10]

    if region == "China" and deepl_api_key:
        hits, knowledge_graph = _translate_hits_and_kg_to_english(deepl_api_key, hits, knowledge_graph)

    search_text = " ".join(f"{hit.title} {hit.snippet}" for hit in hits)
    keywords = _extract_keywords_from_text(search_text, limit=10)
    reports_root = report_dir or DEFAULT_REPORT_DIR
    report_matches = _load_report_matches(reports_root, keywords, limit=5)

    output_dir = DEFAULT_OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "latest_research_context.json"
    payload = {
        "query": query,
        "countries": countries,
        "language": language,
        "time_range": time_range,
        "search_window": search_window,
        "providers_used": providers_used,
        "keywords": keywords,
        "hits": [hit.__dict__ for hit in hits],
        "report_matches": [match.__dict__ for match in report_matches],
        "knowledge_graph": knowledge_graph,
        "raw_attempts": raw_payloads,
    }
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    prompt = _build_prompt(
        query,
        countries,
        language,
        time_range,
        search_window,
        providers_used,
        keywords,
        hits,
        report_matches,
        knowledge_graph,
    )
    return ResearchContext(
        query=query,
        countries=countries,
        language=language,
        time_range=time_range,
        search_window=search_window,
        providers_used=providers_used,
        keywords=keywords,
        hits=hits,
        report_matches=report_matches,
        output_path=str(output_path.relative_to(ROOT_DIR)),
        prompt=prompt,
        knowledge_graph=knowledge_graph or None,
    )
