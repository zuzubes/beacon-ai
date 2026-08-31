# VC Trends Dashboard — Documentation

Tableau dashboard supporting Beacon AI's core thesis: **rising categories in the US and China
historically transfer to India with a lag.** Built for Indian VC partners (micro / emerging
managers, per [plan.md](plan.md)) who need a fast visual read on which sectors are heating up
abroad and whether India is following the same curve.

**Status**: 4 of 7 views are in the final presentation. 3 more were built during analysis but
left out of the final cut — see [Built for analysis but not used for the final
presentation](#built-for-analysis-but-not-used-for-the-final-presentation).

---

## Data Source

| | |
|---|---|
| **File** | `vc_trend_data.csv` |
| **Grain** | one row per `region` × `sector` × `year` (some views also break out `quarter`) |
| **Coverage** | ~1,080 rows, 2010–2028, three regions: USA, China, India |
| **Fields** | `year`, `quarter`, `region`, `sector`, `total_funding_millions`, `deal_count`, `momentum_score` |

**Setup note**: this file is referenced in [plan.md §5](plan.md) but is not currently present in
`data/raw/` (which is gitignored, so it isn't tracked in this repo). Anyone rebuilding the
dashboard from scratch needs to source or regenerate `vc_trend_data.csv` before connecting
Tableau.

**Sector vocabulary differs from the Python pipeline**: the dashboard uses a simplified,
Tableau-native sector list — `AI_ML`, `EVs_Automotive`, `Fintech`, `SaaS_Enterprise`,
`Semiconductors`, and others visible in the heatmap/Sankey. This is a *different* taxonomy from
`SECTOR_MAP` in [src/config.py](src/config.py), which the `load → clean → features → score`
pipeline uses (e.g. `FinTech`, `Enterprise Services`, `E-Commerce`). **The two are not currently
reconciled** — `vc_trend_data.csv` is a standalone dashboard source, not an output of
`src/export.py` (which doesn't exist yet). Don't assume a sector label means the same cohort of
companies in both places.

---

## Metrics Rationale

| Field | Why it's on the dashboard |
|---|---|
| `total_funding_millions` | The core volume signal — dollars are what stakeholders scan for first, and it's what makes the US-first / China-follows / India-lags pattern visible at a glance. |
| `deal_count` | Volume alone hides market structure. Pairing it with funding size distinguishes "many small early bets" from "few large late-stage rounds" — the maturity signal the scatter plot (built but not in the final presentation) is based on. |
| `region` (USA / China / India) | The three-market comparison *is* the product thesis — every chart either colors, filters, or flows by region. |
| `sector` | The unit of the transfer thesis: a "hot sector" claim is meaningless without naming which sector. Nodes on the Sankey; rows on the heatmap (built but not in the final presentation). |
| `year` (and `quarter` where used) | The x-axis for every time-lag argument — the thesis is fundamentally about *when* a sector rises in each market. |
| `momentum_score` | A pre-computed "heating up right now" signal, meant to answer the stakeholder question "what should I look at *today*" without them reading a whole time series. Built as a KPI card but not in the final presentation (see below). |
| `avg_round_size_millions` | `total_funding_millions / deal_count` — the other half of the maturity signal alongside `deal_count`. Not a field in the raw export; computed as a Tableau calculated field for the scatter plot, which is not in the final presentation (see below). |

---

## How to Navigate

The dashboard is one Tableau sheet arranged as a 2×2 grid. Filter by **sector** (top-level filter,
affects all four views) to drill into a single category's cross-market story.

### 1. Time-Lag Area Chart — "US peaks first, China follows, India lags"
**Type**: stacked area chart · **Encoding**: `year` (x) vs `total_funding_millions` (y), stacked
and colored by `region`

Read top-to-bottom which region's layer visibly starts climbing first. This is the headline chart
— it's the plainest visual evidence for the whole thesis, which is why it's positioned top-left.

`[Screenshot: top-left panel of the dashboard image shared 2026-08-31]`

### 2. USA vs India Overlay (+3yr shift)
**Type**: line chart · **Encoding**: `Shifted_Year` (x, India's `year + 3`) vs
`total_funding_millions` (y), colored by `region`

India's line is manually shifted forward 3 years so its curve sits on the same x-axis as USA's
un-shifted curve. If the India line (shifted) visually tracks the USA line, that's the "3-year lag"
thesis holding up for that sector; use the sector filter to check it market-by-market rather than
reading the blended view. This is a lighter-weight substitute for a literal dual-axis chart — same
comparison, one shared axis, no second y-axis to calibrate. See #4 below for the numeric version
of this same question.

`[Screenshot: top-right panel of the dashboard image shared 2026-08-31]`

### 3. Sankey — Flow of Hot Sectors, USA → China → India
**Type**: Sankey diagram · **Encoding**: `region` (left nodes, ordered USA → China → India) →
`sector` (right nodes), flow width = relative funding volume

Reads as "where the money went." A thick USA → Fintech band next to a thin India → Fintech band is
the visual version of "the US bet on this sector years ago; India hasn't caught up yet" — useful
for spotting sectors worth a transfer-probability brief even before checking the actual lag charts.

`[Screenshot: bottom-right panel of the dashboard image shared 2026-08-31]`

### 4. Correlation Analysis — USA Year X vs India Year X+3
**Type**: Tableau trend-line / analytics pane · **Encoding**: Pearson correlation between
`total_funding_millions` for USA in year X and India in year X+3, computed per `sector`

Turns the visual read from the overlay chart (#2 above) into a single number per sector, so
sectors can be ranked by how strongly their lag pattern actually holds rather than eyeballing two
lines. Run per sector via the sector filter.

`[Screenshot: pending — not captured in the dashboard image shared 2026-08-31]`

---

## Built for analysis but not used for the final presentation

These three were part of the original chart spec and were built while exploring the data, but
didn't make the cut for the final dashboard:

| Chart | Purpose |
|---|---|
| **Scatter Plot** — `avg_round_size_millions` vs `deal_count` | Market maturity signal: many small rounds = early-stage market, few large rounds = late-stage. |
| **Momentum Gauge** — `momentum_score` as a KPI card | "What's heating up right now" at-a-glance, without reading a full time series. |
| **VC Trends Sector Heatmap** — `sector`/`region` (rows) × `year` (columns), cell color = `total_funding_millions` | Scan a row across years to see a sector's funding wave move; scan a column to see what was hot in a given year across all three regions at once. Useful for spotting candidate sectors before switching to the time-lag or overlay charts for a closer look at one of them. |

