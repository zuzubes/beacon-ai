"""
LangSmith evaluation harness for engine/company_sectors.py's company -> website ->
industry/sector detection pipeline (the "Detect Industry from Website" sidebar button
in india-trend-radar/app.py).

Ground truth: ../eval-website-to-industry (repo root) -- a small hand-curated set of
VC funds with their real website and the sectors they actually invest in.

Builds/refreshes a LangSmith dataset from that file, then runs the real detection
pipeline (research_search.find_official_website -> company_sectors._fetch_company_text
-> company_sectors._extract_sectors -- the exact functions app.py calls) against it,
scored on three axes:

  - accuracy    : deterministic checks -- did we find the right website? did the
                  detected taxonomy sectors keyword-overlap the analyst's ground truth?
  - honesty     : LLM-judged groundedness -- is each detected sector actually
                  supported by the scraped website text, or guessed from the company
                  name / outside knowledge not present in that text?
  - helpfulness : LLM-judged usefulness -- would a VC analyst find the detected list
                  a useful answer, giving partial credit for same-idea/different-
                  wording sectors rather than requiring an exact string match?

Run:
    python langsmith/eval_website_to_industry.py

Requires OPENAI_API_KEY, LANGSMITH_API_KEY (+ LANGSMITH_ENDPOINT/LANGSMITH_PROJECT),
and at least one of SERPER_API_KEY / SERP_API_KEY / TAVILY_API_KEY in the repo-root
.env. Results upload to LangSmith as a new experiment against the
"website-to-industry" dataset; the script also prints each row's scores locally.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
INDIA_TREND_RADAR = REPO_ROOT / "india-trend-radar"
EVAL_FILE = REPO_ROOT / "eval-website-to-industry"
DATASET_NAME = "website-to-industry"

# engine/ is a package inside india-trend-radar/, not on sys.path by default outside
# that app's own pytest.ini (`pythonpath = .`) -- add it explicitly so this script can
# import the exact production functions instead of re-implementing them.
sys.path.insert(0, str(INDIA_TREND_RADAR))


def _load_env_file() -> None:
    env_path = REPO_ROOT / ".env"
    if not env_path.exists():
        return
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

from engine import company_sectors, research_search  # noqa: E402
from langsmith import Client, traceable  # noqa: E402
from langsmith.evaluation import evaluate  # noqa: E402
from openai import OpenAI  # noqa: E402

JUDGE_MODEL = "gpt-4.1-mini"


# ---------------------------------------------------------------------------
# Ground-truth loading
# ---------------------------------------------------------------------------


def _load_eval_rows() -> list[dict]:
    """eval-website-to-industry is comma-separated but NOT quoted CSV -- the
    invests_in_sectors column itself contains commas, so each row has a variable
    number of fields. Only the first two fields are positional (company, website);
    everything after that is folded into the sectors list."""
    lines = EVAL_FILE.read_text(encoding="utf-8").splitlines()
    rows = []
    for line in lines[1:]:  # skip header
        if not line.strip():
            continue
        parts = [p.strip() for p in line.split(",")]
        company, website, *sectors = parts
        rows.append(
            dict(company=company, website=website, invests_in_sectors=[s for s in sectors if s])
        )
    return rows


def _ensure_dataset(client: Client, rows: list[dict]) -> None:
    if client.has_dataset(dataset_name=DATASET_NAME):
        return
    dataset = client.create_dataset(
        DATASET_NAME,
        description=(
            "Company -> official website -> invested-in sectors, hand-curated ground "
            "truth for engine/company_sectors.py's website/industry detector."
        ),
    )
    client.create_examples(
        dataset_id=dataset.id,
        examples=[
            dict(
                inputs=dict(company=row["company"]),
                outputs=dict(website=row["website"], invests_in_sectors=row["invests_in_sectors"]),
            )
            for row in rows
        ],
    )


# ---------------------------------------------------------------------------
# Target: the real detection pipeline (same functions app.py calls)
# ---------------------------------------------------------------------------


def _api_keys() -> dict:
    return dict(
        serper=os.getenv("SERPER_API_KEY") or os.getenv("serper_api_key"),
        serpapi=os.getenv("SERP_API_KEY") or os.getenv("SERPAPI_API_KEY"),
        tavily=os.getenv("TAVILY_API_KEY") or os.getenv("tavily_api_key"),
        openai=os.getenv("OPENAI_API_KEY") or os.getenv("openai_api_key"),
    )


@traceable(name="detect_industry_from_website")
def run_detector(inputs: dict) -> dict:
    keys = _api_keys()
    company = inputs["company"]
    website = research_search.find_official_website(company, keys["serper"], keys["serpapi"], keys["tavily"])
    page_text = company_sectors._fetch_company_text(website) if website else None
    sectors = company_sectors._extract_sectors(company, page_text, keys["openai"]) if page_text else []
    return dict(website=website, sectors=sectors, page_text=page_text or "")


# ---------------------------------------------------------------------------
# Accuracy evaluators (deterministic)
# ---------------------------------------------------------------------------


def _normalize_url(url: str | None) -> str:
    value = (url or "").strip().lower()
    value = re.sub(r"^https?://", "", value)
    value = re.sub(r"^www\.", "", value)
    return value.rstrip("/")


def website_accuracy(run, example) -> dict:
    expected = _normalize_url((example.outputs or {}).get("website"))
    actual = _normalize_url((run.outputs or {}).get("website"))
    if not expected:
        return dict(key="website_accuracy", score=None, comment="No expected website in dataset row.")
    if actual == expected:
        score, comment = 1.0, "Exact website match."
    elif actual and (actual in expected or expected in actual):
        score, comment = 0.5, f"Partial match: got '{actual}', expected '{expected}'."
    else:
        score, comment = 0.0, f"No match: got '{actual or '(none)'}', expected '{expected}'."
    return dict(key="website_accuracy", score=score, comment=comment)


_STOPWORDS = {"and", "the", "for", "with", "software", "services", "in", "to", "of", "or", "is", "at"}


def _keywords(phrase: str) -> set[str]:
    # Includes digits (not just [a-z]) so short domain acronyms like "AI", "B2B", "SaaS"
    # survive as single tokens instead of being dropped or fragmented -- those are exactly
    # the sector labels this eval file uses most, so losing them would silently weaken the
    # one deterministic cross-check this evaluator provides.
    return {w for w in re.findall(r"[a-z0-9]+", phrase.lower()) if len(w) >= 2 and w not in _STOPWORDS}


def sector_keyword_overlap(run, example) -> dict:
    """Coarse, deterministic sanity check -- literal word overlap between the
    analyst's free-text sectors and the model's fixed-taxonomy sectors. Meant as a
    cheap, non-LLM cross-check against the `helpfulness` judge below, not a precise
    score on its own (a taxonomy term and a free-text synonym often share zero words)."""
    expected_sectors = (example.outputs or {}).get("invests_in_sectors") or []
    detected_sectors = (run.outputs or {}).get("sectors") or []
    if not expected_sectors:
        return dict(key="sector_keyword_overlap", score=None, comment="No expected sectors in dataset row.")

    detected_keywords: set[str] = set()
    for sector in detected_sectors:
        detected_keywords |= _keywords(sector)

    matched, unmatched = 0, []
    for expected in expected_sectors:
        if _keywords(expected) & detected_keywords:
            matched += 1
        else:
            unmatched.append(expected)

    score = matched / len(expected_sectors)
    comment = f"{matched}/{len(expected_sectors)} expected sectors keyword-matched a detected sector."
    if unmatched:
        comment += f" Missed: {', '.join(unmatched)}."
    return dict(key="sector_keyword_overlap", score=score, comment=comment)


# ---------------------------------------------------------------------------
# LLM-judge evaluators: honesty (groundedness) and helpfulness
# ---------------------------------------------------------------------------


def _judge(prompt: str) -> dict:
    keys = _api_keys()
    if not keys["openai"]:
        return dict(score=None, comment="No OPENAI_API_KEY available to run the LLM judge.")
    client = OpenAI(api_key=keys["openai"])
    response = client.responses.create(model=JUDGE_MODEL, input=prompt, max_output_tokens=400)
    text = (getattr(response, "output_text", "") or "").strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
    try:
        data = json.loads(text)
        raw_score = data.get("score")
        return dict(score=float(raw_score) if raw_score is not None else None, comment=str(data.get("comment", "")))
    except Exception as exc:  # noqa: BLE001
        return dict(score=None, comment=f"Judge response could not be parsed: {exc}")


GROUNDEDNESS_PROMPT = """You are auditing an AI industry-classification system for a VC research tool, \
checking for hallucination.

Company: {company}
Text scraped from their website (this is ALL the evidence the system had -- it is not allowed to use \
outside knowledge):
{page_text}

The system classified this company as investing in these sectors: {sectors}

For each sector, judge whether the scraped text actually supports it (mentions the sector, a close \
synonym, or clearly related language) versus the system likely having guessed it from the company \
name or general/outside knowledge not present in this text.

Respond with ONLY valid JSON, no markdown fences: {{"score": number from 0.0 (all sectors are \
ungrounded guesses) to 1.0 (every sector is clearly supported by the scraped text), "comment": "one \
sentence explaining the score, naming any ungrounded sector"}}
"""


def groundedness(run, example) -> dict:
    """Honesty axis: does the model's answer stay within what the scraped page
    actually said, rather than confidently filling gaps from the company name or its
    own general knowledge? A high sector_keyword_overlap score with a LOW groundedness
    score is the interesting failure mode -- it means the system got lucky, not that
    it reasoned correctly from evidence."""
    page_text = (run.outputs or {}).get("page_text") or ""
    sectors = (run.outputs or {}).get("sectors") or []
    company = (example.inputs or {}).get("company", "")
    if not sectors:
        return dict(key="groundedness", score=None, comment="No sectors were detected -- nothing to check for grounding.")
    if not page_text:
        return dict(key="groundedness", score=0.0, comment="Sectors were returned with no scraped page text behind them -- cannot be grounded.")
    prompt = GROUNDEDNESS_PROMPT.format(company=company, page_text=page_text[:6000], sectors=", ".join(sectors))
    result = _judge(prompt)
    return dict(key="groundedness", score=result["score"], comment=result["comment"])


HELPFULNESS_PROMPT = """You are grading whether an AI industry-classification system gave a VC analyst \
a useful answer.

Company: {company}
Analyst's own ground-truth sectors for this company: {expected}
System's detected sectors: {detected}

Score how helpful the system's answer would be to an analyst who already knows the ground truth. Give \
high credit for sectors that express the same idea even if worded differently (e.g. "fintech" and \
"financial services" are the same idea), partial credit for a list that is directionally right but \
missing some sectors or is a bit too broad/narrow, and low credit for a list that would mislead the \
analyst or is unrelated to the ground truth.

Respond with ONLY valid JSON, no markdown fences: {{"score": number from 0.0 to 1.0, "comment": "one \
sentence justifying the score"}}
"""


def helpfulness(run, example) -> dict:
    expected_sectors = (example.outputs or {}).get("invests_in_sectors") or []
    detected_sectors = (run.outputs or {}).get("sectors") or []
    company = (example.inputs or {}).get("company", "")
    if not expected_sectors:
        return dict(key="helpfulness", score=None, comment="No expected sectors in dataset row.")
    if not detected_sectors:
        return dict(key="helpfulness", score=0.0, comment="No sectors were detected at all.")
    prompt = HELPFULNESS_PROMPT.format(
        company=company, expected=", ".join(expected_sectors), detected=", ".join(detected_sectors)
    )
    result = _judge(prompt)
    return dict(key="helpfulness", score=result["score"], comment=result["comment"])


def main() -> None:
    rows = _load_eval_rows()
    print(f"Loaded {len(rows)} ground-truth rows from {EVAL_FILE.relative_to(REPO_ROOT)}")

    client = Client()
    _ensure_dataset(client, rows)

    results = evaluate(
        run_detector,
        data=DATASET_NAME,
        evaluators=[website_accuracy, sector_keyword_overlap, groundedness, helpfulness],
        experiment_prefix="website-to-industry",
        description="Company -> website -> sector detection, scored on accuracy / honesty (groundedness) / helpfulness.",
        max_concurrency=2,
    )

    print(f"\nLangSmith experiment: {results.url}\n")


if __name__ == "__main__":
    main()
