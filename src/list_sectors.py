"""CLI: print unique sectors from sector_year_features.csv as JSON (n8n dropdown demo)."""

import json

import pandas as pd

from src.config import DATA_PROCESSED


def list_sectors() -> list[str]:
    df = pd.read_csv(DATA_PROCESSED / "sector_year_features.csv")
    return sorted(df["sector"].dropna().unique().tolist())


if __name__ == "__main__":
    print(json.dumps(list_sectors()))
