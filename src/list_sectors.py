"""CLI: print sectors with a computed transfer_score as JSON (n8n dropdown demo)."""

import json

import pandas as pd

from src.config import OUTPUTS_SIGNALS


def list_sectors() -> list[str]:
    df = pd.read_csv(OUTPUTS_SIGNALS / "transfer_scores.csv")
    return sorted(df["sector"].dropna().unique().tolist())


if __name__ == "__main__":
    print(json.dumps(list_sectors()))
