# GDPR Compliance Note

## Data processing brief
Beacon AI is built around public company and market data, not customer or employee data. The core tables hold company names, country, sector, funding round, amount, year, and quarter, plus derived scores and generated briefs. A few source rows can contain natural-person names inside a company field, so the raw inputs should be treated as potentially identifiable until cleaned.

## 1. Data flows

| Stage | Data | Purpose | Main storage / processor |
|---|---|---|---|
| `data/raw/` | Public funding and trend files | Ingest source data | Local repo |
| `data/interim/` | Cleaned company, sector, and funding rows | Standardise schema | Local repo |
| `data/processed/` | Sector-year features and maturity comparison | Build scoring inputs | Local repo |
| `outputs/signals/` | Transfer scores | Rank sectors | Local repo |
| `outputs/briefs/` | Generated Markdown and JSON briefs | Partner-facing output | Local repo |
| LLM path | Top sectors and score rows | Generate brief text | OpenAI API |
| Trace path | Prompt and run metadata | Observability | LangSmith |

## 2. Lawful bases

| Processing purpose | Proposed lawful basis | Notes |
|---|---|---|
| Public market research and sector scoring | Legitimate interests | The work is B2B market intelligence, not consumer profiling. Keep the data limited to what the score needs. |
| Brief generation from sector scores | Legitimate interests | The brief is generated for professional research use, with human review before reuse. |
| Trace logging and operational audit trail | Legitimate interests | Keep logs short and purpose-limited. |

If a future client adds identifiable personal data, revisit the lawful basis per purpose and record the balancing test.

## 3. Short DPIA

This current design does not look like a high-risk GDPR processing activity. It does not target natural persons, it does not do automated decisions with legal or similarly significant effects, and it does not process special-category data on purpose. A full DPIA is not clearly triggered on the present scope, but the main residual risk is incidental personal data in source rows and in third-party processing.

Risk summary:
- **Risk 1: incidental personal data in company fields**. Some source rows may name a person or sole trader. Minimise those rows or remove the name if it is not needed.
- **Risk 2: vendor exposure**. Prompts and brief content go to OpenAI and trace metadata goes to LangSmith. Keep that data limited and covered by the right contractual terms.
- **Risk 3: log retention**. Do not keep raw prompts or trace exports longer than needed.

Mitigations:
- send only the sector row needed for the brief
- strip names and other unnecessary identifiers before the LLM call
- keep retention short for raw, interim, and trace data
- review vendor terms before any production use

## 4. Data-subject rights

If identifiable personal data is present in a source row, the usual rights apply: access, rectification, erasure, restriction, objection, portability, and the right not to be subject to solely automated decisions. The system should be able to find and delete or export the affected raw row and any derived traces that still contain it.

Operationally, the hardest rights request here is erasure, because the same record can appear in raw data, interim data, outputs, and trace logs. Keep a simple lookup key so the same row can be removed everywhere.

## 5. Third-party transfers

OpenAI and LangSmith are the only third-party processors in the current design. If personal data leaves the EEA, the transfer needs an adequacy decision or an appropriate safeguard such as Standard Contractual Clauses. Treat that as a go-live requirement, not a nice-to-have.

## 6. Bottom line

Proceed with conditions:
1. Keep the system at company and sector level
2. Remove or pseudonymise any unnecessary personal identifiers before the LLM call
3. Put the right vendor transfer terms in place before production use
