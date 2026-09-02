# GDPR Compliance Note

## Data processing brief
Beacon AI is a B2B market-intelligence pipeline. It processes public company and funding data to rank sectors and generate partner briefs. The system is not built to target customers, employees, or applicants. The only personal-data risk is incidental: some source rows may contain a natural person’s name in a company field, or a sole trader that can still be identifiable.

## 1. Data inventory

| Data category | Source | Purpose | Retention | Crosses EU border? |
|---|---|---|---|---|
| Company name / identifier | Raw funding and trend files | Match and label sector records; generate briefs | Keep only while needed for the project; delete if not needed in outputs | Maybe, if sent to OpenAI or LangSmith |
| Country, sector, funding round, amount, year, quarter | Raw funding and trend files | Clean, aggregate, score, and brief | Keep in raw/interim/processed files for the project lifecycle | Maybe, if sent to OpenAI or LangSmith |
| Derived scores and briefs | `data/processed/`, `outputs/signals/`, `outputs/briefs/` | Rank sectors and create partner-facing output | Keep as project outputs; remove if source row is removed | No, unless exported to a third-party tool |
| Prompt text and trace metadata | OpenAI / LangSmith call path | Generate and audit the brief | Keep as short as possible; no long-term raw-prompt archive | Yes, if vendor storage is outside the EEA |

## 2. Role map

| Entity | Role | Processing activity | DPA / terms |
|---|---|---|---|
| You / this project | Controller for the demo build | Decide what goes into the pipeline and what gets sent to vendors | Owns the local processing |
| Future VC client | Controller for production use | Chooses whether to use the briefs and for what purpose | Needs its own review of terms |
| OpenAI | Processor or sub-processor | Generates the brief text | Needs vendor terms that cover the transfer route |
| LangSmith | Processor or sub-processor | Stores trace metadata and run history | Needs vendor terms that cover the transfer route |

## 3. Lawful bases

| Purpose | Lawful basis | One-line justification | Legal review? |
|---|---|---|---|
| Public market research and sector scoring | Legitimate interests | The project does B2B research, not consumer profiling, and only needs a narrow slice of the source data. | No, for the current scope |
| Brief generation from sector scores | Legitimate interests | The brief is a professional research output, not a decision about a person, and it can be generated from a single sector row. | No, for the current scope |
| Trace logging and QA | Legitimate interests | Trace data is needed to debug hallucinations, compare runs, and prove what was sent to the model. | No, if logs stay short |

If a future version adds person-level data, rerun the legitimate interests assessment:
1. Is the interest real and specific?
2. Is the processing necessary?
3. Do the individual’s rights override it?

## 4. Short DPIA

This scope does not clearly trigger a DPIA. It does not target natural persons, does not make decisions with legal or similarly significant effects, and does not intentionally process special-category data. The only DPIA-style pressure points are incidental identifiers in source rows and the use of third-party AI/tracing services. That is manageable at this stage, but it should be revisited if the system moves from company-level trend analysis to founder, customer, or employee profiling.

## 5. Data-subject rights

If a source row contains an identifiable person, the usual rights apply: access, rectification, erasure, restriction, objection, portability, and protection from solely automated decisions. The practical weak spot is erasure, because the same source row can appear in raw files, interim tables, processed outputs, and trace logs.

What the system should do:
- keep a stable row key or source ID
- remove the row from `data/raw/`, `data/interim/`, `data/processed/`, and outputs when needed
- purge or redact matching traces where the row content was sent to a vendor
- answer access requests with the source row and the generated output tied to it

## 6. Third-party transfers

OpenAI and LangSmith are the only third-party services in the current design. If any personal data is sent to them from the EEA, treat that as an international transfer and confirm the transfer route before production use. The safe default is:
- use only the minimum necessary text
- avoid sending raw names or other unnecessary identifiers
- rely on adequacy only if the vendor and account setup actually support it
- otherwise put Standard Contractual Clauses in place before go-live

## 7. Law stacking check

- **AI Act cross-check:** the current system is minimal risk, so the AI Act does not add a separate compliance duty beyond normal privacy and security controls.
- **ePrivacy:** no cookies, pixels, or device tracking are part of the current repo. If those get added later, review consent and notice.
- **Data Act:** not relevant to this build.

## 8. Bottom line

Proceed with conditions:
1. strip incidental personal identifiers before any vendor call
2. keep a simple deletion path across raw, processed, output, and trace data
3. confirm the transfer mechanism and vendor terms before production use

This note is not a legal opinion, a DPIA, or a certification.
