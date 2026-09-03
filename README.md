# Beacon AI - Cross-Border Trend Intelligence

Detects rising categories/business models in China & US that historically transfer to India,
and generates ranked "transfer probability" briefs for Indian VC partners. See [plan.md](plan.md)
for the full build plan.

The repo has two parts:

- A data pipeline (`src/`, `data/`, `outputs/`, `n8n/`, `langsmith/`) that scores and exports signals/briefs.
- **`india-trend-radar/`** — a minimalist internal Streamlit tool for a micro-VC fund partner to scan
  macro-level trends emerging in the US and China, drill into the mega- and sub-trends they create, and
  get an India-investment read (Invest / Strategize / Watch / Stay away) on each. This is the live,
  demo-able app; its full workflow, validation/fallback behavior, cost tracking, and setup are documented
  in detail below.

## Setup — data pipeline

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # fill in OPENAI_API_KEY + LANGSMITH_API_KEY
```

## Setup — india-trend-radar app

```bash
cd india-trend-radar
pip install -r requirements.txt
streamlit run streamlit_app.py
```

Requires Python 3.9+.

### Data modes

The app works with **zero configuration** out of the box, using deterministic sample data (clearly
labeled "sample" in the UI) so you can see the full workflow immediately.

To use live data, turn on the toggles in the sidebar and provide your own keys:

- **Trends** — add `openai_api_key` to a local `.env` file in the app folder, then turn on "Use live
  OpenAI API for trends" to generate the trend hierarchy with OpenAI.
- **Research search** — add `SERPER_API_KEY`, `SERP_API_KEY`, and `TAVILY_API_KEY` to the same `.env`
  file. The app runs a live research search before OpenAI, saves the raw search payload under
  `raw/research/`, extracts keywords from snippets, and uses those snippets plus local reports to
  inform macro, mega, and sub-trends.
- **News Signals** — add `NEWSAPI_KEY` and `CURRENTNEWS_API_KEY` to the same `.env` file, then turn on
  "Use live NewsAPI.org for signals" to fetch live articles. The app tries NewsAPI first and falls back
  to Currents Search if NewsAPI cannot return at least 5 articles. Currents uses `keywords=<industry>`,
  `language=en`, and `page_size=3` across multiple pages. The live query uses the selected
  industry/sector as the keyword, English-only results, `title,description` matching, and
  `sortBy=relevancy`.
- **Trend analysis report** — every run writes a markdown file named like `region_industry_timestamp.md`
  under `raw/analysis/`, then writes a combined `*_final.md` file that appends the structured output
  from `trends.py`.

If a live call fails (bad key, rate limit, network error) the app shows a warning and automatically
falls back to sample data rather than crashing.

The app reads `openai_api_key` and `NEWSAPI_KEY` from the local `.env` file in `india-trend-radar/`.

## Repository structure

Top level:

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

`india-trend-radar/` (the app):

```
app.py                 Vercel landing page entrypoint
streamlit_app.py       Main Streamlit app: layout, navigation, cards
engine/
  trends.py             Macro/Mega/Sub trend generation (mock + live OpenAI)
  research_search.py    Live search preprocessing and report cross-reference
  trend_analysis.py     Markdown analysis report assembly
  news.py                News signal generation (mock + live NewsAPI)
  momentum.py            Plotly radial "momentum" chart
raw/reports/            Local research reports used for sub-trend grounding
raw/research/           Generated search context files
raw/analysis/           Generated analysis markdown files
requirements.txt
.streamlit/config.toml   Minimalist light theme
```

## india-trend-radar workflow

1. Enter **Company / Fund**, **Time Range**, **Region**, and **Industry / Sector** in the sidebar.
2. Click **Run Analysis**. The app finds:
   - **Macro-Trends** — long-term, decade-scale forces (society, technology, economy, ecology, politics).
   - **Mega-Trends** — the points of tension each macro-trend creates against consumer/business needs.
   - **Sub-Trends** — emerging, actionable trends arising from that tension.
3. Each trend renders as a card: name, description, strength, growth, time horizon, and a recommendation pill.
4. A **Momentum** tab plots every trend on a radial chart (radius = strength, grouped into colored category arcs).
5. A live **research search pass** runs before OpenAI, extracts keywords from search snippets, and cross-references local research reports to ground the trend hierarchy. It tries Serper first, then falls back to SerpAPI and Tavily if Serper fails or times out.
6. The app writes a timestamped markdown trend-analysis report for every run under `raw/analysis/`, then combines that report with the `trends.py` output into a final analysis file.
7. A **News Signals** tab lists relevant articles for the query.

## Real tools, validation, and fallback behavior

This app documents the exact behavior expected from the real API layer, including how failures are handled.

### Input / output contract

- `research_search.py` returns a `ResearchContext` object with `providers_used`, `keywords`, `hits`, `report_matches`, and a prompt string for the trend generator.
- `trends.py` returns a list of trend dictionaries with the required fields: `tier`, `id`, `parent`, `category`, `name`, `description`, `strength`, `growth_pct`, `time_horizon`, and `recommendation`.
- `news.py` returns a list of article dictionaries with title, source, timestamps, tags, and a sample/live flag.
- `trend_analysis.py` returns a `TrendAnalysisResult` with markdown, HTML, PDF bytes, file paths, and a public share URL when upload succeeds.

### Provider order and orchestration

- Research search tries Serper first, then SerpAPI, then Tavily.
- News tries NewsAPI first, then Currents Search if NewsAPI is empty or fails.
- Trend generation uses OpenAI when a key is present, otherwise deterministic sample output.
- Growth-company drill-down uses OpenAI when available, otherwise deterministic sample companies and social signals.
- Final-analysis sharing uploads the generated PDF to a free public host and returns a direct URL when the upload succeeds.

### Validation and fallback rules

- Truncated OpenAI responses are rejected instead of being shown as partial output.
- Invalid or empty provider responses fall back to the next provider or to deterministic sample data.
- The final-analysis PDF download reads the saved PDF from disk, so the button does not depend only on in-memory state.
- The share link is only shown when it is a real public URL.

### Contradiction handling

- The structured trend hierarchy is the source of record for the app.
- The prose report is generated to stay aligned with that hierarchy and the appended trend table.
- If a live provider disagrees with the rest of the pipeline or returns malformed output, the app does not try to merge contradictory content; it falls back to the next valid provider or to sample data.

### Failure modes and cost profile

- OpenAI calls only happen when a live key is enabled. If the API is unavailable or the response is truncated, the app falls back to sample content.
- Research search can fan out across up to three search providers, so the request cost is driven by how many fallbacks are needed.
- News can make one NewsAPI call and, if necessary, one Currents call.
- PDF sharing uses a free public upload host. If that host fails, sharing is disabled for that run but the local PDF download still works.

### Internal cost calculation matrix

Use this matrix to track every request in a consistent way. The goal is not just to estimate invoice cost, but to see which parts of the workflow are creating hidden spend.

| Track on every request | What it tells you | How to capture it | Why it matters |
| --- | --- | --- | --- |
| Provider and model | Which vendor and model family handled the request | Record the exact model name returned by the client call | Pricing changes by model tier and version, so this is the first cost driver to isolate |
| Feature or endpoint | Which product path created the spend | Tag the request as trends, research search, news, drill-down, or PDF export | Lets the team find the highest-cost workflow quickly |
| Input tokens | Prompt size sent to the model | Log prompt token count before the request is sent | Larger prompts are the most predictable cost amplifier |
| Output tokens | Amount generated by the model | Log completion token count after the response returns | Output-heavy requests usually cost more and can signal overly verbose prompts |
| Cached tokens | Whether provider-native caching was used | Record cached prompt tokens separately when available | Caching can materially reduce cost on repeated or structured prompts |
| Latency | Time spent waiting for the request | Capture end-to-end elapsed time in milliseconds | Slow calls often correlate with retries, multi-step chains, or tool overhead |
| Retries | How many times the request was attempted | Count explicit provider retries or fallback attempts | A cheap request can become expensive if it fails and gets repeated |
| Tool calls | Any extra external calls made by the model flow | Count search, browser, function, or API tool invocations | Tool use hides cost outside the model bill and should be tracked explicitly |
| Estimated cost | Expected spend for the request | Multiply token counts by the current provider pricing sheet | Gives the team an alertable estimate before the invoice closes |

Suggested formula:

```text
estimated_cost =
  (input_tokens - cached_tokens) * input_rate +
  cached_tokens * cached_input_rate +
  output_tokens * output_rate +
  tool_call_costs +
  retry_overhead
```

Recommended internal fields:

| Field | Example |
| --- | --- |
| request_id | `trend-analysis-20260903-014731` |
| timestamp | `2026-09-03 01:47:31` |
| provider | `openai` |
| model | `gpt-4.1-mini` |
| feature | `trend generation` |
| input_tokens | `4,820` |
| cached_tokens | `1,200` |
| output_tokens | `910` |
| retries | `1` |
| tool_calls | `3` |
| latency_ms | `12,840` |
| estimated_cost_usd | `$0.42` |
| status | `success` / `fallback` / `truncated` |

Each run writes a folder under `raw/cost_tracking/` named like `<company>_<timestamp>/` with both `cost_log.json` and `cost_log.csv`.

### Evidence

The behavior above is covered by tests:

- `india-trend-radar/tests/test_research_search.py` checks provider precedence and fallback.
- `india-trend-radar/tests/test_trend_analysis.py` checks public upload behavior.
- `india-trend-radar/tests/test_growth_companies.py` checks live-vs-sample behavior.
- `india-trend-radar/tests/test_final_analysis_render.py` checks branded HTML rendering and sanitization.
- `india-trend-radar/tests/test_app_sidebar.py` checks the app still boots cleanly.

The "Detect Industry from Website" button (`india-trend-radar/engine/company_sectors.py`) is additionally scored
against a hand-curated ground-truth set via a LangSmith eval — see
[`langsmith/eval_website_to_industry.py`](langsmith/eval_website_to_industry.py) and its
results in [`langsmith/langsmith_documentation.md`](langsmith/langsmith_documentation.md).

### Agent journey and metrics

The app shows the tracked journey in the UI itself so the flow is visible during review:

- `research_search.py` writes `raw/research/latest_research_context.json` with the query, countries, provider order, live hits, report matches, extracted keywords, and prompt input.
- `trend_analysis.py` writes the markdown source, the combined markdown, the branded HTML report, and the PDF export under `raw/analysis/`.
- `streamlit_app.py` surfaces a compact run summary with live-hits count, local-report count, provider order, PDF state, and share state.
- The final-analysis tab keeps the download/share path tied to the saved PDF file so the UI is backed by an actual artifact on disk.

These fields are the main validation and metric points reviewers should inspect when checking orchestration quality.

## Reliability evidence

The `india-trend-radar/` app's live toolchain, validation, and fallback behavior is documented in detail
above and covered by its own tests. The project makes the orchestration explicit:

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

The app exposes the information journey and tracked outputs directly in the UI:

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

## Feasibility and Responsible AI

The `india-trend-radar/` MVP is narrow on purpose:

- Single-user local tool.
- No authentication.
- No shared database.
- Inputs stay limited to company/fund, time range, region, and sector.
- Deterministic sample data keeps the app usable when live APIs are absent.
- Live providers are optional and sit behind clear fallbacks.

Security and retention stay lightweight for the prototype:

- API keys are read from local `.env` files only.
- Generated research context and analysis artifacts are stored on disk under `india-trend-radar/raw/research/` and `india-trend-radar/raw/analysis/`.
- There is no server-side retention policy; files persist locally until deleted.
- Public sharing uses a free file host only for the final PDF. If that host fails, local download still works.

Validation and monitoring are explicit:

- Provider failures fall back to deterministic sample outputs instead of surfacing partial results.
- Truncated model responses are rejected.
- The bottom-of-page warning area keeps user-facing error text readable while hiding stack details.
- The test suite checks provider precedence, upload behavior, sanitization, and app boot.

Define these launch KPIs before the pilot, then track them on every run:

- Time from query to final brief.
- Run completion rate without manual intervention.
- Share/download success rate.
- Percentage of runs with live research coverage.
- Percentage of sections with supporting evidence.
- Analyst satisfaction or usefulness score on the final report.

## Notes

- Sample trend and news content is templated per your Industry/Sector input and seeded by your query, so the same inputs always return the same sample output (useful for demos), while different inputs produce different results.
- Sample news article sources are intentionally fictional (e.g. "Signal Wire (sample)") so they're never mistaken for real reporting.
- This is a single-user local tool; there is no authentication or multi-user state.
