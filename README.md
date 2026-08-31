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
