"""Read raw datasets from data/raw/ and assemble the Phase 1 interim tables (see plan.md)."""

from pathlib import Path

import pandas as pd

from src.clean import (
    clean_china_table,
    clean_india_table,
    clean_startup_funding_dataset_table,
    filter_country,
)
from src.config import CHINA_ENCODING, DATA_INTERIM, RAW_FILES


def load_china() -> pd.DataFrame:
    return pd.read_csv(RAW_FILES["china_events"], encoding=CHINA_ENCODING)


def load_india() -> pd.DataFrame:
    return pd.read_csv(RAW_FILES["india_funding"])


def load_startup_funding_dataset() -> pd.DataFrame:
    return pd.read_csv(RAW_FILES["startup_funding_dataset"])


def build_interim_tables(output_dir: Path = DATA_INTERIM) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    clean_china_table(load_china()).to_csv(output_dir / "china_clean.csv", index=False)
    clean_india_table(load_india()).to_csv(output_dir / "india_clean.csv", index=False)

    us = filter_country(
        clean_startup_funding_dataset_table(load_startup_funding_dataset()), "United States"
    )
    us.to_csv(output_dir / "us_clean.csv", index=False)


if __name__ == "__main__":
    build_interim_tables()
