# Beacon AI - Cross-Border Trend Intelligence

Detects rising categories/business models in China & US that historically transfer to India,
and generates ranked "transfer probability" briefs for Indian VC partners. See [plan.md](plan.md)
for the full build plan.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # fill in OPENAI_API_KEY + LANGSMITH_API_KEY
```

## Structure

- `data/raw/` — source datasets (not edited in place)
- `src/` — pipeline modules (`load` → `clean` → `features` → `score` → `briefs` → `export`)
- `outputs/` — signals, briefs, and dashboard-ready extracts for PowerBI/n8n
- `n8n/`
  - `brief_generation_demo.json` — n8n workflow export (automation POC)
  - `workflow_documentation.md` — what it does, why n8n, limits vs. production
- `langsmith/`
  - `Screenshot-Langsmith-Round1.png` — tracing evidence for `generate_brief` runs
  - `langsmith_documentation.md` — what was monitored and what it shows, including the
    website→industry detection eval results
  - `eval-website-to-industry` — hand-curated ground-truth rows for the website→industry eval
  - `eval_website_to_industry.py` — LangSmith eval of the company/fund → website → sector
    detector against [`langsmith/eval-website-to-industry`](langsmith/eval-website-to-industry), scored on accuracy,
    honesty (groundedness), and helpfulness
- `feedback/`
  - `round1_decision.md` — keep or change industry/use case + why

## Reliability evidence

The `india-trend-radar/` app documents its live toolchain, validation, and fallback behavior in its own README and tests. The project now makes the orchestration explicit:

- Provider order is fixed, not ad hoc.
- Search falls back Serper -> SerpAPI -> Tavily.
- News falls back NewsAPI -> Currents when the primary feed is thin or fails.
- Trend generation rejects truncated API responses and falls back to deterministic sample data.
- Final-analysis sharing uses public file hosts for copyable URLs, and PDF download uses the saved file on disk.

Relevant evidence lives under `india-trend-radar/tests/`, especially:

- `test_research_search.py`
- `test_trend_analysis.py`
- `test_growth_companies.py`
- `test_final_analysis_render.py`
- `test_app_sidebar.py`

## Agent journey and validation

The app now exposes the information journey and tracked outputs directly in the UI:

- Research search produces `latest_research_context.json` with provider order, live hits, extracted keywords, and local report matches.
- Trend analysis writes both markdown and HTML/PDF outputs under `raw/analysis/`.
- Final analysis shows whether the PDF is saved and whether a public share URL was published.
- The context card shows the active providers, the number of live hits, the number of local report matches, and the current output state.

This is the evidence trail reviewers can inspect to see how information flows through the system and where it is validated.

## Business case and client framing

The MVP answers one narrow question: which US/China trend signals look transferable to India, and what should a VC partner do with them.

Set these KPIs before launch:

- Time to generate a usable analysis from query to report.
- Percentage of runs that complete without manual intervention.
- Share/download success rate for the final analysis.
- Percentage of outputs supported by live research or local report evidence.
- Analyst usefulness score on the final readout.

A cleaner client-facing narrative is:

1. Problem: partners need a fast, repeatable way to scan cross-border trend signals.
2. Method: the system collects research, ranks trends, and turns them into an India investment read.
3. Evidence: every run stores the raw research context, final markdown, HTML, PDF, and eval artifacts.
4. Outcome: a concise trend brief plus a drill-down path for follow-up analysis.
