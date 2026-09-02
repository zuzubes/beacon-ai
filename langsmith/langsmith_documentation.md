# LangSmith Monitoring — Evidence

**Evidence**: [`Screenshot-Langsmith-Round1.png`](Screenshot-Langsmith-Round1.png) — the Tracing
view for this project's LangSmith workspace (`pr-impassioned-hobby-36`, EU region, matching
`LANGSMITH_ENDPOINT` in `.env.example`).

A live shareable link isn't included here because it requires inviting instructors into the
LangSmith workspace itself; the screenshot stands in for that per the brief's own fallback
("screenshots ... if link sharing is blocked"). No separate trace export (JSON) accompanies it —
just the screenshot.

## What's being monitored

Every call to `generate_brief()` in [`src/briefs.py`](../src/briefs.py) is wrapped in
`@traceable(name="generate_brief")` from the `langsmith` SDK. That's the one place in the
pipeline where an LLM actually generates partner-facing content — the transfer-score numbers
feeding it are deterministic, so this is the step that most needs a paper trail: which prompt
produced which brief, how long it took, and whether it succeeded.

## What the screenshot shows

- **A live run history, not a one-off test**: runs span from `8/31/2026, 10:...` through
  `1:3...`, meaning the trace was capturing real activity across the working session, not a
  single manually-triggered call staged for the screenshot.
- **Real model calls vs. test runs, distinguished at a glance**: the `Input` column shows two
  different shapes — rows reading `gpt-4o-mini` / `<openai.OpenAI object at...>` are real API
  calls (from `src/generate_brief_for_sector.py` and manual runs of `src/briefs.py`); rows
  reading `<test_briefs._StubClient ...>` are `tests/test_briefs.py`'s unit tests, which pass a
  stub client instead of hitting OpenAI. Both get traced identically, which is what makes it
  possible to tell them apart after the fact instead of taking it on faith.
- **Latency makes that distinction visible without opening a single row**: stub-client runs
  complete in 0.00–0.06s; real `gpt-4o-mini` calls take 2.19s–9.08s. That spread alone is a
  useful signal — if a "real" run ever showed near-zero latency, that would mean the client
  wasn't actually reached, which is exactly the kind of silent failure tracing is meant to catch.
- **Output previews per row** (`Investment Brief: EdTech ...`, `FinTech: An Early Investm...`,
  `Stub headline`, etc.) mean a specific brief's provenance is checkable without re-running
  anything — if a partner ever questioned a brief's claim, the exact prompt and model output
  that produced it is right here.
- **One dataset already exists** (`Datasets & Experiments: 1` in the sidebar), meaning the
  tracing setup is already a step past ad-hoc logging — runs can be grouped for evaluation, not
  just inspected individually.

## What this shows about transparency/observability

For an LLM step that's explicitly instructed not to invent facts ("Do not invent specific
company names, deal amounts, or facts not given here" — the prompt in
[`build_brief_prompt`](../src/briefs.py)), being able to see the exact input row and raw model
output behind any brief is the actual mechanism for catching a hallucination, not just a nice-to-have.
It also means test coverage and production usage are auditable from the same place — anyone
reviewing this project doesn't have to trust that the test suite exercises the traced code path;
the stub-client rows in this same view prove it.

## Website → Industry Detection Eval

**Script**: [`eval_website_to_industry.py`](eval_website_to_industry.py). **Ground truth**:
[`eval-website-to-industry`](eval-website-to-industry) — 7 hand-curated VC funds with their
real website and the sectors they actually invest in. **Target**: the exact pipeline
`india-trend-radar/app.py`'s "Detect Industry from Website" button calls —
`research_search.find_official_website` → `company_sectors._fetch_company_text` →
`company_sectors._extract_sectors` — not a re-implementation.

Run it with `python langsmith/eval_website_to_industry.py`; it builds/reuses a `website-to-industry`
LangSmith dataset from the ground-truth file and logs a fresh experiment on every run, scored on
three axes:

- **Accuracy** — two deterministic checks: exact/partial website-URL match, and literal keyword
  overlap between the detector's fixed-taxonomy sectors and the analyst's free-text ground truth
  (kept intentionally coarse — it's a cross-reference against the judged score below, not a precise
  metric on its own, since e.g. "AI" and "artificial intelligence" share no literal words).
- **Honesty** (groundedness) — an LLM judge checks each detected sector against the *actual scraped
  website text*, scoring whether it's genuinely supported or looks guessed from the company name /
  outside knowledge not present in that text.
- **Helpfulness** — an LLM judge compares the detected sectors to the analyst's ground truth and
  scores whether the answer would actually help them, giving partial credit for same-idea/
  different-wording sectors instead of requiring an exact match.

### Latest run

[View the experiment in LangSmith](https://eu.smith.langchain.com/o/80bd18ed-fa6b-4055-96c9-9b77785a8b50/datasets/3595daf6-f4b7-4bc7-af04-f53e9a045ad7/compare?selectedSessions=c334da13-952f-4115-b8f9-522088ed9935)
(experiment `website-to-industry-c9ebe093`).

| Company | Website found | Accuracy | Keyword overlap | Honesty | Helpfulness |
|---|---|---:|---:|---:|---:|
| 12flags | exact match | 1.0 | 0.75 | 0.80 | 0.7 |
| peercheque | ✗ landed on a LinkedIn company page | 0.0 | 0.25 | 0.60 | 0.4 |
| axilor | exact match | 1.0 | 0.25 | 1.00 | 0.7 |
| stellaris venture partners | exact match | 1.0 | 0.17 | 1.00 | 0.5 |
| ventureast | exact match | 1.0 | 0.13 | 0.83 | 0.7 |
| Kae Capital | exact match | 1.0 | 0.00 | 0.80 | 0.6 |
| yournest venture capital | exact match | 1.0 | 0.00 | **0.00** | 0.1 |
| **Average** | | **0.86** | **0.22** | **0.72** | **0.53** |

**The finding this eval exists to catch**: for `yournest venture capital`, `_fetch_company_text`
only pulled 24 characters off the live page (just the title — the real content likely needs JS
rendering that a plain `requests` + BeautifulSoup fetch can't execute). With effectively no
evidence, `_extract_sectors` still confidently returned 5 taxonomy sectors, none close to the
ground truth ("DeepTech"). An accuracy-only eval would just record this as "wrong." The
groundedness judge instead explains *why*: *"the classification appears to be based on outside
knowledge or guessing from the company name alone."* That's the gap between getting an answer
wrong and the system being dishonest about how confident it should be — and it's the concrete
argument for adding an "I couldn't tell, please pick a sector" path when the scraped page is this
thin, rather than always forcing a guess.
