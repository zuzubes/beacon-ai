# Beacon AI — Agile Execution Plan

This document reframes what has already been built — the n8n **PoC** and the `india-trend-radar` **MVP** — into a client-facing, phased Agile delivery plan: Epics, User Stories, 2-week Sprints, a Definition of Done, and per-sprint Acceptance Criteria/KPIs. It is written as the plan a consulting team would hand a client (e.g. an Indian micro-VC fund) to explain how this was — and could be — delivered in a disciplined, incremental way, per the AI Manager certification's required artifacts (see [`feedback/round1_decision.md`](feedback/round1_decision.md)).

Every Epic and Story below maps to something that actually exists in the repo today — no aspirational features. Where a capability is still a known gap or limitation, it's called out explicitly rather than glossed over.

**Scope mapping** (as instructed):
- **PoC** = the n8n conversational workflow (`n8n/`) and the data pipeline that feeds it (`src/`)
- **MVP** = the `india-trend-radar/` Streamlit application, front end and back end
- **Launch** = left open below for manual completion

---

## 1. Timeline Overview

| Phase | Sprints | Duration | Outcome |
|---|---|---|---|
| **PoC** | Sprint 1 | Weeks 1–2 | A partner can pick a sector in an n8n chat and get a partner-ready investment brief back, generated from a real China/US/India funding data pipeline. |
| **MVP** | Sprints 2–6 | Weeks 3–12 (10 weeks) | `india-trend-radar`: full trend-hierarchy generation, live research grounding, visualization, news signals, drill-down, summary report + PDF export, and production-hardening (cost tracking, key failover, test coverage). |
| **Launch** | Sprint 7+ | Week 13+ | _Open — to be defined._ |

```
Week:   1    2    3    4    5    6    7    8    9   10   11   12   13+
       |----|----|----|----|----|----|----|----|----|----|----|----|------------>
        Sprint1   Sprint2  Sprint3  Sprint4  Sprint5  Sprint6    Sprint 7+
        (PoC)     (MVP)    (MVP)    (MVP)    (MVP)    (MVP)      (Launch — TBD)
                  Trend    Radar +  Drill-   Summary  Reliability,
                  core +   News     down +   Report   Cost, Failover,
                  research          Industry & Export & Test Hardening
                                    Detect
```

**Why PoC is one sprint and MVP is five:** the PoC's job was narrow by design — prove "pick a sector → get a brief" is a real, chainable pipeline (per [`n8n/workflow_documentation.md`](n8n/workflow_documentation.md), it was explicitly *not* meant to be the long-term product surface). The MVP is where the actual product surface area lives: nine distinct capabilities across research, generation, visualization, drill-down, export, and reliability engineering, each with its own module and test file under `india-trend-radar/`.

---

## 2. Epics & User Stories

### Phase: PoC — n8n Workflow

#### Epic PoC-1 — Cross-Border Funding Data Foundation
*Owning code: `src/load.py`, `src/clean.py`, `src/config.py`*

| ID | Story | Notes |
|---|---|---|
| PoC-1.1 | As a data analyst, I want China/US/India funding CSVs loaded and normalized into one schema (`company, country, sector, round, amount_usd, amount_precision, year, quarter`), so downstream scoring runs on consistent data regardless of source format. | China source uses `gb18030` encoding; India `amount` is in USD millions — both handled explicitly, not assumed. |
| PoC-1.2 | As a data analyst, I want inconsistent sector labels (e.g. "Fintech" vs "Financial Technology") harmonized via a shared mapping table, so cross-country comparison is possible. | `SECTOR_MAP` in `src/config.py`; unmapped values degrade to a title-cased "Other" rather than being dropped. |
| PoC-1.3 | As a data analyst, I want fuzzy/bucketed China deal amounts (e.g. "several million RMB") converted to point-estimate USD with a precision flag, so partial data is used, not silently discarded. | `amount_precision` column: `exact` / `bucket_estimate` / `undisclosed` / `unknown_currency`. |

#### Epic PoC-2 — Transfer-Probability Signal Engine
*Owning code: `src/features.py`, `src/score.py`*

| ID | Story | Notes |
|---|---|---|
| PoC-2.1 | As a VC partner, I want each sector scored with a transparent, explainable weighted formula (velocity, maturity, India-early-signal, market size), so I can trust and defend the ranking to my own LPs. | `transfer_score` formula documented in `plan.md` Phase 3. |
| PoC-2.2 | As a VC partner, I want to see which sectors are "already maturing abroad, still early in India," so I can prioritize genuinely time-sensitive opportunities. | `still_early_in_india` flag, `maturity_comparison.csv`. |
| PoC-2.3 | As a VC partner, I want only sectors with real China/US deal presence included in the ranking, so I'm not shown a fabricated "transfer" claim for a sector with no actual foreign signal. | Sectors with `china_us_deal_count == 0` are excluded outright, not scored as 0. |

#### Epic PoC-3 — Automated Brief Generation
*Owning code: `src/briefs.py`, `langsmith/`*

| ID | Story | Notes |
|---|---|---|
| PoC-3.1 | As a VC partner, I want a partner-ready markdown brief auto-generated for each top-ranked sector, so I don't have to interpret a raw scoring table myself. | Structured output (`headline`, `why_rising_abroad`, `india_opportunity`, `key_risks`, `confidence_note`) via OpenAI `responses.parse`. |
| PoC-3.2 | As a VC partner, I want the brief grounded only in the pipeline's own numbers, not invented company names or facts, so I don't repeat a hallucinated claim to my own investors. | Prompt explicitly restricts the model to the sector's score-table values. |
| PoC-3.3 | As an ops lead, I want every brief-generation call traced in LangSmith, so a generated brief's provenance can be audited after the fact. | `@traceable` on `generate_brief`; evidence in `langsmith/Screenshot-Langsmith-Round1.png`. |

#### Epic PoC-4 — Conversational Front Door (n8n)
*Owning code: `n8n/brief_generation_demo.json`, `src/bridge_server.py`*

| ID | Story | Notes |
|---|---|---|
| PoC-4.1 | As a partner, I want to type a sector name into a chat window and get the brief back in the same conversation, so I never have to touch a terminal or notebook. | "When chat message received" → Get Sectors → Match Sector → Generate Brief → Format Brief Output. |
| PoC-4.2 | As a partner, if what I typed doesn't exactly match an available sector, I want to see the list of valid sectors, so I know what to ask for next. | "Ask For Sector" branch when no exact (case-insensitive) match. |
| PoC-4.3 | As an engineer, I want the n8n workflow to call a token-protected local bridge server instead of executing Python directly inside n8n, so a shared/managed n8n instance stays secure. | `X-Bridge-Token` header check in `src/bridge_server.py`; `Execute Command` is disabled on the shared instance by design. |

> **Known PoC limitations, carried forward on purpose (not hidden):** requires the bridge server + tunnel running locally; tunnel URL is ephemeral and must be updated by hand; single shared-secret auth; no persistence beyond the filesystem; only sectors with a computed `transfer_score` (20 of ~69) are offered. See `n8n/workflow_documentation.md` for the full list — these are exactly the gaps a production build (Epic-level "Launch" work) would close.

---

### Phase: MVP — `india-trend-radar`

#### Epic MVP-1 — Trend Hierarchy Generation
*Owning code: `engine/trends.py`; tests: `tests/test_trends.py`, `tests/test_app_sidebar.py`*

| ID | Story |
|---|---|
| MVP-1.1 | As a VC partner, I want to enter Company/Fund, Time Range, Region, and Industry and get a Macro → Mega → Sub-Trend hierarchy, so I can see where a category sits in context before drilling in. |
| MVP-1.2 | As a VC partner, I want each trend card to show strength, growth %, time horizon, and an Invest/Strategize/Watch/Stay-away recommendation, so I can act on it directly without extra interpretation. |
| MVP-1.3 | As a user, when the OpenAI API is unavailable or returns a truncated response, I want the app to fall back to deterministic sample data instead of crashing or showing partial output. |

#### Epic MVP-2 — Live Research Grounding
*Owning code: `engine/research_search.py`; tests: `tests/test_research_search.py`*

| ID | Story |
|---|---|
| MVP-2.1 | As a VC partner, I want trend generation grounded in a live web search pass (Serper → SerpAPI → Tavily fallback), so the hierarchy reflects current signal, not just the model's training data. |
| MVP-2.2 | As an engineer/reviewer, I want the research context (provider order, live-hit count, extracted keywords, local report matches) written to disk and surfaced in the UI, so I can audit how a given trend was derived. |

#### Epic MVP-3 — Momentum & Trend Radar Visualization
*Owning code: `engine/momentum.py`*

| ID | Story |
|---|---|
| MVP-3.1 | As a VC partner, I want a radial "momentum" chart plotting every trend's strength, so I can compare trends visually at a glance instead of reading a table. |
| MVP-3.2 | As a VC partner, I want the strongest trend visually distinguished (color/accent) from the rest, so I immediately know where to focus. |

#### Epic MVP-4 — News Signals
*Owning code: `engine/news.py`*

| ID | Story |
|---|---|
| MVP-4.1 | As a VC partner, I want a feed of 8 news articles relevant to my selected industry, so I can sanity-check the trend read against real reporting. |
| MVP-4.2 | As a VC partner, I want news filtered to my selected region and time range (not stale articles or ones about an unrelated country), so the signal stays credible. |

#### Epic MVP-5 — Sub-Trend Drill-Down
*Owning code: `engine/growth_companies.py`, `engine/product_trends.py`; tests: `tests/test_growth_companies.py`, `tests/test_product_trends.py`*

| ID | Story |
|---|---|
| MVP-5.1 | As a VC partner, I want to drill into a specific sub-trend and see relevant growth companies, so I can identify concrete investable names. |
| MVP-5.2 | As a VC partner, I want social signals supporting a sub-trend, scoped to my selected time range, so I'm not shown stale sentiment from outside my query window. |
| MVP-5.3 | As a VC partner, I want a trending-products table filtered to my selected industry (empty rather than irrelevant when nothing matches), so I never see, say, skincare products under a Food & Beverages analysis. |

#### Epic MVP-6 — Industry Auto-Detection
*Owning code: `engine/company_sectors.py`; eval: `langsmith/eval_website_to_industry.py`*

| ID | Story |
|---|---|
| MVP-6.1 | As a VC partner, I want to enter a company/fund name and have the app detect its investment sector from its own website, so I don't have to manually classify every fund I look up. |
| MVP-6.2 | As an ops lead, I want the detector's accuracy scored against a hand-curated ground-truth set in LangSmith (accuracy, honesty/groundedness, helpfulness), so its quality is measured, not assumed. |

#### Epic MVP-7 — Summary Report & Export
*Owning code: `engine/trend_analysis.py`, `engine/final_analysis_render.py`, `engine/pdf_export.py`; tests: `tests/test_trend_analysis.py`, `tests/test_final_analysis_render.py`*

| ID | Story |
|---|---|
| MVP-7.1 | As a VC partner, I want a consolidated Summary Report combining the trend hierarchy and prose analysis, so I have one document to read instead of piecing tabs together. |
| MVP-7.2 | As a VC partner, I want to download the report as a branded, sanitized PDF, so I can share it outside the app. |
| MVP-7.3 | As a VC partner, I want a public share link only when the PDF upload actually succeeds, so I never hand out a broken link. |

#### Epic MVP-8 — Reliability, Cost & Performance Engineering
*Owning code: `engine/openai_keys.py`, `engine/cost_tracking.py`, `engine/research_search.py`, `engine/news.py`*

| ID | Story |
|---|---|
| MVP-8.1 | As an engineer, I want every external call (OpenAI, search, news) to follow a defined, fixed provider fallback order, so a single vendor outage doesn't take the app down. |
| MVP-8.2 | As an ops lead, I want every analysis run's token usage, latency, and estimated cost logged per call, so spend is auditable per run instead of guessed at the monthly invoice. |
| MVP-8.3 | As an ops lead, I want automatic failover to a backup OpenAI key on rate-limit/quota errors, so one exhausted key doesn't block a partner mid-session. |
| MVP-8.4 | As a VC partner, I want the first analysis run to show staged, plain-language progress instead of a long silent wait, so the tool feels responsive even while generation is in flight. |

#### Epic MVP-9 — Quality & Regression Safety
*Owning code: `india-trend-radar/tests/`*

| ID | Story |
|---|---|
| MVP-9.1 | As an engineer, I want automated tests covering provider fallback precedence, output sanitization, and clean app boot, so a regression is caught by CI before a partner ever sees it. |

---

### Phase: Launch — *Open, candidate scope*

> None of the epics below are built yet — this phase is genuinely open per the original scope ("for launch, keep it open, I'll add it manually"). These are the candidate epics identified so far; owning code, sprint sequencing, and acceptance criteria are intentionally left undefined until scoped.

#### Epic Launch-1 — Multi-Tenant Onboarding & Profiles
*Owning code: not yet built*

| ID | Story |
|---|---|
| Launch-1.1 | As a new user, I want to sign up and access my own workspace, so multiple partners/funds can use Beacon AI without seeing each other's runs. |
| Launch-1.2 | As a user, I want to set and persist my profile and preferences, so I don't have to re-enter the same inputs every session. |

#### Epic Launch-2 — India Lookalike Company Identification
*Owning code: not yet built*

| ID | Story |
|---|---|
| Launch-2.1 | As a VC partner, I want the app to identify India-based companies analogous to the ones trending in the US and China, so I get concrete lookalike investment targets, not just a trend category. |
| Launch-2.2 | As a VC partner, I want these lookalike companies categorized by funding stage, size, and growth rate, so I can quickly filter to the ones that fit my fund's check size and stage. |

#### Epic Launch-3 — Sub-Trend Ecosystem Landscape
*Owning code: not yet built*

| ID | Story |
|---|---|
| Launch-3.1 | As a VC partner, I want a landscape view of the companies operating within a specific sub-trend, so I can deconstruct the competitive ecosystem instead of reading a flat company list. |

#### Epic Launch-4 — Agent & API Access
*Owning code: not yet built*

| ID | Story |
|---|---|
| Launch-4.1 | As a developer or agent user, I want to trigger trend generation directly through an API, not only the Streamlit UI, so programmatic and agent-based users can consume Beacon AI without a browser session. |

---

## 3. Sprint Plan (2-week sprints)

### Sprint 1 — PoC: Data Pipeline → Scoring → Brief → n8n Chat
**Epics:** PoC-1, PoC-2, PoC-3, PoC-4
**Goal:** A partner can open the n8n chat, name a sector, and receive a grounded, LangSmith-traced investment brief — proving the end-to-end shape (trigger → validate → generate → respond) cheaply, without committing to a production front end.

### Sprint 2 — MVP: Trend Hierarchy Core + Research Grounding
**Epics:** MVP-1, MVP-2
**Goal:** The core loop works — inputs in, a live-research-grounded Macro/Mega/Sub-trend hierarchy out, with a safe deterministic fallback when live data isn't available.

### Sprint 3 — MVP: Visualization + News Signals
**Epics:** MVP-3, MVP-4
**Goal:** Partners can *see* the trend landscape (radar chart) and cross-check it against real, region/time-relevant news — not just read a wall of cards.

### Sprint 4 — MVP: Drill-Down + Industry Auto-Detection
**Epics:** MVP-5, MVP-6
**Goal:** Partners can go from a sub-trend to concrete companies/products/social signal, and skip manual sector classification when researching a specific fund.

### Sprint 5 — MVP: Summary Report & Export
**Epics:** MVP-7
**Goal:** Everything generated so far consolidates into one shareable, exportable artifact — the thing a partner actually forwards to their IC.

### Sprint 6 — MVP: Reliability, Cost & Quality Hardening
**Epics:** MVP-8, MVP-9
**Goal:** The app survives a vendor outage or an exhausted API key without failing a partner mid-session, every run's cost is auditable, and the full test suite guards all of the above against regression.

### Sprint 7+ — Launch
Sprint boundaries and timeline remain open (per original scope: "for launch, keep it open"). The epics below are the candidate scope identified so far; sequencing into specific 2-week sprints is still to be decided.

- Launch-1 — Multi-Tenant Onboarding & Profiles
- Launch-2 — India Lookalike Company Identification
- Launch-3 — Sub-Trend Ecosystem Landscape
- Launch-4 — Agent & API Access

---

## 4. Definition of Done

**Story-level DoD** (applies to every story above, no exceptions):

1. Code merged behind the feature's owning module — no logic left only in `streamlit_app.py` glue code.
2. A live path **and** a deterministic sample/mock fallback both exist and are exercised — never just the happy path.
3. Automated tests exist for the story's behavior and pass (`pytest`) — see per-epic test files listed above.
4. Manually verified end-to-end in the running app (not just unit-tested in isolation) before being called done.
5. Failure modes are handled visibly: a plain-language warning to the user, never a raw stack trace or a silent wrong answer.
6. No secrets (API keys, tokens) committed; all credentials read from a local, gitignored `.env`.
7. Behavior documented in the owning README (`README.md` or `india-trend-radar/README.md`) — specifically the provider order, validation rule, or fallback behavior the story introduces.

**Epic-level DoD** — an Epic is Done when:

- Every story in it meets the Story-level DoD above, **and**
- The epic's dedicated test file(s) pass in the full suite run, **and**
- The behavior is demonstrable live, on request, without pre-staged data (sample-mode is an acceptable substitute only when live keys are intentionally withheld for the demo).

**PoC-specific DoD** — additionally: the bridge server + n8n workflow can be started from a clean checkout following `n8n/workflow_documentation.md` with no undocumented manual steps, and a full "type sector name → receive brief" round trip completes in the chat.

**MVP-specific DoD** — additionally: `streamlit run streamlit_app.py` boots cleanly with zero configuration (sample mode), and every live-mode toggle documented in `india-trend-radar/README.md`'s "Data modes" section works when the corresponding key is supplied.

---

## 5. Acceptance Criteria & KPIs per Sprint

### Sprint 1 (PoC)
- `pytest tests/` (repo root) passes — `test_load.py`, `test_clean.py`, `test_features.py`, `test_score.py`, `test_briefs.py`.
- `outputs/signals/transfer_scores.csv` contains ranked sectors with `transfer_score` in `[0, 1]`, restricted to sectors with nonzero China/US deal presence.
- `outputs/briefs/` contains a generated brief per top-ranked sector plus a combined `briefs.json`.
- End-to-end chat demo: a partner names a valid sector and receives a brief in-chat; an invalid/no-match input returns the sector picklist instead of an error.
- At least one `generate_brief` run is visible as a trace in LangSmith.
- **KPI:** time from chat message sent → brief returned in chat (baseline to be measured and recorded, since no target currently exists in the repo).
- **KPI:** brief generation success rate (runs that return a valid structured brief vs. fail/timeout).

### Sprint 2 (MVP — Trend Hierarchy + Research Grounding)
- `tests/test_app_sidebar.py` and `tests/test_trends.py` pass in `india-trend-radar/`.
- A run with all four inputs set returns Macro/Mega/Sub-trend cards, each containing every required field (`tier`, `id`, `parent`, `category`, `name`, `description`, `strength`, `growth_pct`, `time_horizon`, `recommendation`).
- `tests/test_research_search.py` passes, confirming Serper → SerpAPI → Tavily fallback order.
- `raw/research/latest_research_context.json` is written on every run with provider order, live-hit count, and extracted keywords populated.
- A forced truncated-response condition falls back to sample data instead of crashing or rendering partial output (manually verified, not just asserted in a test).
       - **KPI:** % of runs completing with live research coverage vs. falling back to sample data.
       - **KPI:** run completion rate without manual intervention (per `india-trend-radar/README.md`'s stated launch KPI).

### Sprint 3 (MVP — Visualization + News Signals)
- Trend Radar chart renders with an explicit title (no "undefined") and the strongest category visually distinguished — regression-checked, since this was a real bug hit and fixed once already.
- News Signals tab renders exactly 8 articles per run.
- Manual spot-check across 3+ industry/region combinations: no article is off-industry or off-region (this exact failure mode — Russia/India articles under a US & China query — was previously observed and fixed).
- News fallback to Currents triggers correctly when NewsAPI returns fewer than 5 results.
- **KPI:** news relevance rate (articles matching selected industry + region, sampled manually per release since no automated relevance scorer exists yet).

### Sprint 4 (MVP — Drill-Down + Industry Auto-Detection)
- `tests/test_growth_companies.py` and `tests/test_product_trends.py` pass.
- Drill-down for a sub-trend returns companies and social signals scoped to the selected time range; trending products are either industry-matched or an explicit empty state — never an unfiltered, irrelevant fallback list.
- `tests/test_company_sectors.py` passes.
- Website→industry detector eval (`langsmith/eval_website_to_industry.py`) run against the ground-truth set in `langsmith/eval-website-to-industry`, with accuracy/honesty/helpfulness scores recorded in `langsmith/langsmith_documentation.md`.
- **KPI:** industry-detection eval accuracy score against the ground-truth set (target to be set once a baseline run exists).

### Sprint 5 (MVP — Summary Report & Export)
- `tests/test_trend_analysis.py` and `tests/test_final_analysis_render.py` pass.
- Summary Report tab renders the combined markdown + trend table for a completed run.
- PDF download reads from the saved file on disk under `raw/analysis/`, not from in-memory state only — confirmed by killing and reloading the session mid-flow.
- Share link is shown only on confirmed successful upload; a failed upload disables sharing for that run without blocking the local PDF download.
- **KPI:** share/download success rate (per `india-trend-radar/README.md`'s stated launch KPI).

### Sprint 6 (MVP — Reliability, Cost & Quality Hardening)
- All 6 OpenAI call sites (`trends.py`, `trend_analysis.py` ×2, `growth_companies.py` ×2, `company_sectors.py`) use `engine/openai_keys.py`'s failover; a simulated `RateLimitError` on the primary key is confirmed to retry successfully on the backup key.
- Every analysis run writes `cost_log.json` and `cost_log.csv` under `raw/cost_tracking/<company>_<timestamp>/` with token counts, latency, and estimated cost populated.
- Full `india-trend-radar/tests/` suite passes at 100% (currently 61+ tests across 8 test files).
- First-click ("cold") analysis latency is measured and recorded as a baseline metric, even if not yet at target.
- **KPI:** 100% of OpenAI call sites covered by failover.
- **KPI:** 100% of runs producing a cost log entry.
- **KPI:** test suite pass rate = 100% before any sprint is called closed.

### Sprint 7 (Launch — Onboarding, Lookalikes, Landscape, Agent Access)

> None of Launch-1 through Launch-4 are built yet, so nothing below is a measured result — these are the acceptance bars this work will be held to once it's scoped into an actual sprint, stated now so "done" is defined before the work starts.

- **Launch-1:** A second user can sign up, log in, and run an analysis without seeing another account's runs, saved profile, or preferences — verified with two concurrent test accounts, not just single-user testing. Profile/preference values persist across a full logout/login cycle, not just within one browser session.
- **Launch-2:** For a completed analysis run, the app returns at least one India-based "lookalike" company for each trending China/US comparison company surfaced in that run, each tagged with funding stage, company size, and growth rate — never an unlabeled name with no comparison basis.
- **Launch-3:** The ecosystem landscape view for a selected sub-trend renders using real drill-down data (companies/signals already generated for that sub-trend), not placeholder or unrelated content; an empty state shows when no drill-down has been generated yet for that sub-trend.
- **Launch-4:** An external caller can trigger a trend-generation run and retrieve the resulting hierarchy through an API call alone, with no browser/Streamlit session involved — documented with a working example request/response in `india-trend-radar/README.md`.
- **KPI:** multi-tenant isolation — 0 cross-account data leaks across test accounts (hard requirement, not a target range, since any nonzero value is a data breach).
- **KPI:** % of trending non-India companies for which the app successfully surfaces at least one India lookalike.
- **KPI:** onboarding funnel — time from signup to first completed analysis run (baseline to be measured once Launch-1 exists).
- **KPI:** agent/API-triggered run success rate (target to be set once a baseline run exists, per the pattern used for other not-yet-baselined KPIs above).