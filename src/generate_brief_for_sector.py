"""CLI: generate one partner-ready brief for a single user-chosen sector (n8n demo).

Unlike `src/briefs.py::build_briefs` (which regenerates the top-N ranked sectors),
this takes an arbitrary `--sector` argument, looks up its transfer-score signal,
and writes a single timestamped brief to OUTPUTS_BRIEFS.
"""

import argparse
import sys
from datetime import datetime, timezone

import pandas as pd
from openai import OpenAI

from src.briefs import generate_brief, render_brief_markdown, slugify_sector
from src.config import OUTPUTS_BRIEFS, OUTPUTS_SIGNALS


def generate_brief_for_sector(sector: str) -> str:
    transfer_scores = pd.read_csv(OUTPUTS_SIGNALS / "transfer_scores.csv")
    match = transfer_scores[transfer_scores["sector"].str.lower() == sector.strip().lower()]
    if match.empty:
        available = ", ".join(sorted(transfer_scores["sector"]))
        raise ValueError(f"No transfer-score signal for sector '{sector}'. Available: {available}")

    row = match.iloc[0].to_dict()
    client = OpenAI()
    brief = generate_brief(client, row)
    markdown = render_brief_markdown(row, brief)

    OUTPUTS_BRIEFS.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = OUTPUTS_BRIEFS / f"{slugify_sector(row['sector'])}_{timestamp}.md"
    out_path.write_text(markdown)

    return markdown


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sector", required=True)
    args = parser.parse_args()

    try:
        print(generate_brief_for_sector(args.sector))
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
