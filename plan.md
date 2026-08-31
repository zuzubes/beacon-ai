# Beacon AI — Cross-Border Trend Intelligence — Python Project Plan
**Primary Use Case**: Detect rising categories / business models in China & US that historically transfer to India.
**Output**: Ranked "transfer probability" briefs + analogous Indian opportunity sizing.
**Target**: Small Indian VC firms (micro / emerging managers).
**Round 1 goal**: Working data pipeline + simple scoring + brief generation that can feed PowerBI, n8n, and LangSmith.

---

## 1. Project Goals (MVP Scope)

| Goal | Description | Success Criteria |
|------|-------------|------------------|
| Data foundation | Clean & unify global + India funding datasets | Consistent country, sector, year, amount columns |
| Trend detection | Identify rising categories in China & US | Funding velocity / deal-count growth by sector-year |
| Transfer scoring | Historical lag pattern → probability score | Ranked list of categories with score 0–1 |
| Brief generation | LLM-produced partner-ready cards | 5–10 ranked briefs with sources & opportunity note |
| Observability | Traceable LLM calls | LangSmith-compatible traces |
| Export | Clean tables for dashboard + n8n | CSVs / JSON that PowerBI and n8n can consume |

**Out of scope for first Python iteration**
- Real-time news/hiring APIs
- Autonomous investment recommendations
- Production multi-tenant SaaS
- Live Chinese proprietary data

---

## 2. Recommended Project Structure

```
beacon-ai/
├── data/
│   ├── raw/                  # original Kaggle CSVs (do not edit)
│   ├── interim/              # cleaned intermediate files
│   └── processed/            # final feature tables + signals
├── src/
│   ├── __init__.py
│   ├── config.py             # paths, constants, sector mappings
│   ├── load.py                # read raw files
│   ├── clean.py               # standardise columns, types, countries
│   ├── features.py            # velocity, growth rates, lag features
│   ├── score.py                # transfer probability heuristics / simple model
│   ├── briefs.py               # LLM prompt + brief generation
│   └── export.py               # write dashboard-ready CSVs + JSON
├── notebooks/
│   ├── 01_eda.ipynb
│   ├── 02_feature_exploration.ipynb
│   └── 03_score_validation.ipynb
├── outputs/
│   ├── signals/               # ranked category signals
│   ├── briefs/                # generated markdown/JSON briefs
│   └── dashboard/              # PowerBI-ready extracts
├── tests/
│   └── test_clean.py
├── .env.example
├── requirements.txt
├── plan.md                     # this file
└── README.md
```

---

## 3. Datasets (Expected in `data/raw/`)

Place these (or their equivalents) in `data/raw/`:

| Dataset | Expected key files | Role |
|---------|---------------------|------|
| Global Startup Funding Rounds 2020–2026 | `funding_rounds.csv`, `startups.csv` | China + US funding velocity |
| Global Startup Funding & VC Trends 2015–2026 | main CSV | Longer history + India comparison |
| Indian Startup Funding (2010–2025 or 2020–2025) | main CSV | India-side lag / adoption patterns |
| AI Company & Startup Funding (optional) | main CSV | High-signal AI category examples |

**Minimum viable set for first run**
1. One global rounds file with country + sector + amount + date
2. One India funding file with sector + amount + year

---

## 4. Step-by-Step Build Plan

### Phase 0 — Setup (30–60 min)
- [ ] Create the folder structure above
- [ ] `python -m venv .venv && source .venv/bin/activate`
- [ ] `pip install pandas numpy scikit-learn python-dotenv openai anthropic langsmith pyyaml`
- [ ] Copy downloaded CSVs into `data/raw/`
- [ ] Create `.env` with `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` + `LANGCHAIN_API_KEY` (for LangSmith)
- [ ] Write `src/config.py` with paths and a basic sector mapping dictionary

### Phase 1 — Load & Clean (Day 1)
**Files**: `src/load.py`, `src/clean.py`

Tasks:
1. Load each raw CSV with robust encoding / separator handling
2. Standardise column names (e.g. `country`, `sector`, `amount_usd`, `year`, `date`)
3. Normalise country values → `China`, `United States`, `India` (handle variants)
4. Clean `amount_usd` (remove $, commas, "undisclosed", convert to float)
5. Parse dates → extract `year` and `quarter`
6. Harmonise sector labels (create a mapping: "Fintech" / "Financial Technology" → `FinTech`, etc.)
7. Drop rows missing critical fields (country, sector, year)
8. Save cleaned frames to `data/interim/`
9. Translate all fields to english language

**Deliverable**: `data/interim/global_clean.csv` and `data/interim/india_clean.csv`

### Phase 1 — Implementation Notes (2026-08-31, done)

Decisions made while building `src/load.py`/`src/clean.py` against the real files in §5:

- **Source assignment**: `China-invest_event.csv` = China, `Indian_startups_funding.csv` = India,
  `startup_funding_dataset (1).csv` (filtered to `Country == "USA"`) = United States.
- **`funding_rounds.csv` + `organizations.csv` dropped**: originally planned to join them
  (`org_uuid` → `uuid`) to get sector labels, but the join returns **zero matches** — the two
  files are independently-sampled 50-row exports, not a relational pair. No sector data is
  obtainable from them, so they're excluded from the pipeline.
- **China encoding**: the file is `gb18030` (Chinese GBK), not UTF-8.
- **China amounts are often fuzzy**: ~52% of rows report a bucket phrase (e.g. "several million
  RMB") instead of an exact figure. Resolved as: assign a representative point estimate per bucket,
  flagged via an `amount_precision` column (`exact` / `bucket_estimate` / `undisclosed` /
  `unknown_currency`) so later scoring can weight or discount them. Multi-currency amounts
  (CNY/USD/HKD/TWD/JPY/GBP) are converted to USD via flat approximate FX rates — not
  date-accurate, fine for trend signal, not for financial precision. See `CHINA_BUCKET_ESTIMATES`,
  `CHINA_CURRENCY_TO_USD` in `src/config.py`.
- **India `amount` unit**: confirmed as USD millions (not raw USD or thousands) — `amount_usd =
  amount * 1_000_000`. A raw value of exactly `0` is treated as undisclosed, not a literal $0 round
  (~31% of rows).
- **Output schema** (all three interim tables share it): `company, country, sector, round,
  amount_usd, amount_precision, year, quarter`.
- **Interim files produced**: `data/interim/china_clean.csv` (15,304 rows), `india_clean.csv`
  (5,074 rows), `us_clean.csv` (240 rows) — renamed from the original `global_clean.csv` since
  "global" now means "US-filtered" given China and India each have a dedicated source.
- Sector/round vocab translated via `SECTOR_MAP`, `CHINA_FIELD_MAP`, `CHINA_ROUND_MAP` in
  `src/config.py` — starter maps with a title-case/`"Other"`/`"Unspecified"` fallback for anything
  unmapped, so unrecognised values degrade gracefully instead of being dropped.

### Phase 2 — Feature Engineering (Day 1–2)
**File**: `src/features.py`

Core features to compute (grouped by country + sector + year):

| Feature | Formula / Logic |
|---------|-----------------|
| `deal_count` | number of rounds |
| `total_funding` | sum of amount_usd |
| `avg_deal_size` | total_funding / deal_count |
| `yoy_funding_growth` | (this_year – last_year) / last_year |
| `yoy_deal_growth` | same for deal_count |
| `velocity_score` | weighted combination of growth + absolute volume |
| `china_us_rising_flag` | True if growth > threshold and absolute volume above floor |

Then create lag / transfer features:
- For each sector, compute average lag (years) between peak growth in China/US and subsequent growth in India (where historical data allows)
- Simple historical success rate: "Did India later see funding growth in the same sector?"

**Deliverable**: `data/processed/sector_year_features.csv`

### Phase 2 — Implementation Notes (2026-08-31, done)

- **Lag feature redefined**: China's data (1999–2016) ends right where India's (2015–2021) and
  US's (2016–2025) begin, so a real "years of lag" can't be estimated — there's essentially one
  transition point, not a multi-year panel. Replaced with a **maturity comparison**
  (`compute_maturity_comparison` in `src/features.py`): for each sector, compare China's/US's most
  recent years (`MATURITY_RECENT_YEARS_N=3` for China, all years for US since its window is
  already short) against India's earliest years (`INDIA_EARLY_YEARS_N=3`) — giving a defensible
  "already maturing abroad, still early in India" flag (`still_early_in_india`) instead of a
  fabricated lag number.
- **`velocity_score` formula** (plan left this as "weighted combination", made concrete):
  `0.5 * normalized(yoy_deal_growth, winsorized to [-1, 3]) + 0.5 * normalized(log1p(deal_count))`,
  min-max normalized *within each country* (so China's much larger row count doesn't dominate
  India's/US's own sector landscape). See `VELOCITY_*` constants in `src/config.py`.
- **`rising_flag`**: `yoy_deal_growth > 0.20` AND `deal_count >= 5` (`RISING_GROWTH_THRESHOLD`,
  `RISING_DEAL_COUNT_FLOOR`) — thresholds are a reasonable starting point, not tuned against any
  ground truth yet.
- **`SECTOR_MAP` expanded**: profiling India's `vertical` column found only 10/67 distinct values
  were mapped, with the two largest unmapped ones ("Consumer Internet" 738 rows, "Technology" 578
  rows — ~26% of all India rows) invisible to the China/US comparison as a result. Added 7 more
  labels that have an honest 1:1 match to China's canonical categories; left genuinely ambiguous
  ones (Consumer Internet, Technology, Food, Personal Care, ...) unmapped rather than force-fit.
- **Outputs**: `data/processed/sector_year_features.csv` (590 rows: country × sector × year, with
  `deal_count`, `total_funding`, `avg_deal_size`, `yoy_deal_growth`, `yoy_funding_growth`,
  `velocity_score`, `rising`) and `data/processed/maturity_comparison.csv` (56 rows: one per
  sector, with `china_us_maturity_score`, `india_early_presence_score`, `still_early_in_india`) —
  two files instead of one, since the maturity comparison is sector-level, not sector-year-level.
- **Known limitation carried forward**: `maturity_comparison.csv` still only "sees" sectors that
  exist in `SECTOR_MAP`'s canonical vocabulary on both sides — India's largest genuinely-unmapped
  categories (Consumer Internet, Technology) can never show up as `still_early_in_india` even if
  they should, since they have no China/US counterpart to compare against. Worth another pass if
  Phase 3 scoring leans on this file.

### Phase 3 — Transfer Probability Scoring (Day 2)
**File**: `src/score.py`

Start with a transparent heuristic (easier to explain to partners and to monitor in LangSmith):

```text
transfer_score = (
    0.40 * china_us_velocity_normalised +
    0.25 * historical_lag_match +
    0.20 * india_still_early_signal +
    0.15 * sector_size_potential
)
```

### Phase 3 — Implementation Notes (2026-08-31, done)

`src/score.py` maps the four weighted components onto Phase 2's output (`TRANSFER_SCORE_WEIGHTS` in
`src/config.py`):

- **`china_us_velocity_normalised`**: each sector's most recent `velocity_score` in China and in
  US (independently — each sector uses its own latest available year per country, not a shared
  cutoff year), averaged across whichever of the two are present.
- **`historical_lag_match`**: reuses `maturity_comparison.china_us_maturity_score` from Phase 2 —
  the plan's literal "historical lag" isn't estimable (see Phase 2 notes), so this is the honest
  substitute: how mature/active the sector already is in China+US's recent years.
- **`india_still_early_signal`**: `1 - maturity_comparison.india_early_presence_score` — high when
  the sector barely showed up in India's earliest years.
- **`sector_size_potential`**: normalized (min-max) total historical `total_funding` summed across
  *all* China+US years (not just the recent window) — a deliberately different base metric from
  `historical_lag_match` (deal-count-based) so the two components aren't measuring the same thing
  twice; this one captures absolute dollar scale as a market-size proxy.
- **Eligibility**: a sector only gets a `transfer_score` if `china_us_deal_count > 0` in
  `maturity_comparison.csv` — a sector with zero China/US presence has no meaningful "transfer
  from China/US" claim, so it's excluded from the ranked output entirely rather than scored as 0.
  Individual missing components (e.g. no velocity data) are filled with 0 for sectors that do
  qualify.
- **Output**: `outputs/signals/transfer_scores.csv`, 20 ranked sectors, top-ranked: FinTech,
  Enterprise Services, E-Commerce, Entertainment, Local Services.
- **Known limitation inherited from Phase 2**: this ranking is still built on the sector vocabulary
  gap noted above — India's "Consumer Internet"/"Technology" rows can't appear here since they
  have no `maturity_comparison` row with `china_us_deal_count > 0`.

> **Note**: the source plan as pasted into the assistant ends here. Phases 4+ (brief generation
> in `src/briefs.py`, LangSmith observability wiring, and the `src/export.py` dashboard/n8n
> exports referenced in the goals table and folder structure above) still need to be detailed
> before implementation reaches those files.

### Phase 4 — Brief Generation (2026-08-31, done)

**Files**: `src/briefs.py`

Never detailed in the original pasted plan, so scoped via clarifying questions before building:

- **Provider**: OpenAI (`OPENAI_API_KEY`), model `gpt-4o-mini` (`BRIEF_MODEL` in `src/config.py`).
  Uses the SDK's `responses.parse(..., text_format=Brief)` structured-output API (openai==3.6.0) —
  a Pydantic `Brief` model (`headline`, `why_rising_abroad`, `india_opportunity`, `key_risks`,
  `confidence_note`) instead of hand-parsing JSON.
- **Scope**: top 5 sectors from `outputs/signals/transfer_scores.csv` (`BRIEF_TOP_N=5`), matching
  the low end of the plan's "5–10 ranked briefs" target.
- **Grounding**: the prompt (`build_brief_prompt`) passes only the sector's own score-table numbers
  and instructs the model not to invent company names or facts beyond them — a partner-ready brief
  citing numbers the pipeline can't back up would be worse than no brief.
- **LangSmith wired in now** (not deferred): `generate_brief` is wrapped in `@traceable` from
  `langsmith`. Found along the way that the current LangSmith SDK env vars are `LANGSMITH_TRACING`
  / `LANGSMITH_ENDPOINT` / `LANGSMITH_API_KEY` / `LANGSMITH_PROJECT`, not the `LANGCHAIN_*` names
  the Phase 0 `.env.example` guessed — corrected there.
- **`.env` wasn't actually being loaded**: none of the earlier phases needed real env vars, so it
  went unnoticed that nothing called `load_dotenv()`. Added to `src/config.py` (loads `.env` once,
  at import time, before any other module reads an env var) — this was a real bug, not just a
  Phase 4 concern, it just hadn't surfaced yet.
- **Testing**: `generate_brief`/`generate_briefs` are I/O against a paid external API, so per TDD's
  "mock only when unavoidable" guidance they're tested via a stub client (dependency-injected, no
  network) rather than a real call. `build_briefs` (the real `OpenAI()` entrypoint) itself isn't
  unit-tested — it was run once for real, live, with your approval, to produce the actual output.
- **Output**: `outputs/briefs/{sector-slug}.md` (one per sector) + `outputs/briefs/briefs.json`
  (all 5, structured — for n8n/PowerBI per the plan's integration goal).

---

## 5. Actual raw data on disk (verified 2026-08-31)

`data/raw/` currently contains a mix of a small Crunchbase-style sample export (50 rows, joined by
`uuid`) plus several standalone datasets. Recorded here so Phase 1 (`load.py`/`clean.py`) maps real
columns instead of the illustrative ones above:

| File | Rows | Key columns |
|------|------|--------------|
| `funding_rounds.csv` | 51 | `org_uuid`, `org_name`, `country_code`, `announced_on`, `raised_amount_usd`, `investment_type` |
| `organizations.csv` | 51 | `uuid`, `name`, `country_code`, `category_list`, `category_groups_list`, `total_funding_usd`, `founded_on` |
| `investments.csv` | 51 | `funding_round_uuid`, `investor_name`, `investor_type`, `is_lead_investor` |
| `acquisitions.csv` | 51 | `acquirer_country_code`, `acquiree_country_code`, `acquired_on`, `price_usd` |
| `org_parents.csv` | 51 | `uuid`, `parent_uuid`, `parent_name` |
| `organization_descriptions.csv` | 51 | `uuid`, `description` |
| `China-invest_event.csv` | 15,305 | `date`, `company`, `field`, `place`, `round`, `amount`, `investor` |
| `Indian_startups_funding.csv` | 5,075 | `startup`, `vertical`, `city`, `investors`, `round`, `amount`, `year`, `state` |
| `vc_trend_data.csv` | 1,080 | `year`, `quarter`, `region`, `sector`, `total_funding_millions`, `deal_count`, `momentum_score` |
| `startup_funding_dataset (1).csv` | 2,001 | `Startup Name`, `Industry`, `Country`, `Funding Stage`, `Amount Raised (USD)`, `Funding Date` |
| `CB-Insights_Venture-Report-2024.xlsx` / `2025.xlsx` / `Venture-Trends-2021.xlsx` | — | Excel reports, not yet parsed |

`funding_rounds.csv` (the "global rounds" source in section 3) only has 51 rows — nowhere near the "2020–2026 global rounds" scale implied by the plan. `China-invest_event.csv` is the real China-side volume source, and `vc_trend_data.csv` looks like a pre-aggregated sector/year trend table that could shortcut a lot of Phase 2. This should be confirmed before Phase 1 locks in which files are load-bearing.
