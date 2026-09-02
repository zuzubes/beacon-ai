# Beacon AI

A minimalist internal tool for a micro-VC fund partner to scan macro-level trends emerging in the US and China, drill into the mega- and sub-trends they create, and get an India-investment read (Invest / Strategize / Watch / Stay away) on each.

## Workflow

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

## Setup

```bash
pip install -r requirements.txt
streamlit run app.py
```

Requires Python 3.9+.

## Data modes

The app works with **zero configuration** out of the box, using deterministic sample data (clearly labeled "sample" in the UI) so you can see the full workflow immediately.

To use live data, turn on the toggles in the sidebar and provide your own keys:

- **Trends** — add `openai_api_key` to a local `.env` file in the app folder, then turn on "Use live OpenAI API for trends" to generate the trend hierarchy with OpenAI.
- **Research search** — add `SERPER_API_KEY`, `SERP_API_KEY`, and `TAVILY_API_KEY` to the same `.env` file. The app runs a live research search before OpenAI, saves the raw search payload under `raw/research/`, extracts keywords from snippets, and uses those snippets plus local reports to inform macro, mega, and sub-trends.
- **News Signals** — add `NEWSAPI_KEY` and `CURRENTNEWS_API_KEY` to the same `.env` file, then turn on "Use live NewsAPI.org for signals" to fetch live articles. The app tries NewsAPI first and falls back to Currents Search if NewsAPI cannot return at least 5 articles. Currents uses `keywords=<industry>`, `language=en`, and `page_size=3` across multiple pages. The live query uses the selected industry/sector as the keyword, English-only results, `title,description` matching, and `sortBy=relevancy`.
- **Trend analysis report** — every run writes a markdown file named like `region_industry_timestamp.md` under `raw/analysis/`, then writes a combined `*_final.md` file that appends the structured output from `trends.py`.
If a live call fails (bad key, rate limit, network error) the app shows a warning and automatically falls back to sample data rather than crashing.

The app reads `openai_api_key` and `NEWSAPI_KEY` from the local `.env` file in `india-trend-radar/`.

## Project structure

```
app.py                 Main Streamlit app: layout, navigation, cards
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

## Notes

- Sample trend and news content is templated per your Industry/Sector input and seeded by your query, so the same inputs always return the same sample output (useful for demos), while different inputs produce different results.
- Sample news article sources are intentionally fictional (e.g. "Signal Wire (sample)") so they're never mistaken for real reporting.
- This is a single-user local tool; there is no authentication or multi-user state.
