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
