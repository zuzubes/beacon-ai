"""Transfer probability scoring (plan.md Phase 3).

Maps the plan's four weighted components onto Phase 2's outputs:
  - china_us_velocity        <- each sector's latest-year velocity_score in China/US, averaged
  - historical_lag_match     <- maturity_comparison.china_us_maturity_score (see Phase 2 notes:
                                 this replaces the plan's literal "years of lag", which the data
                                 can't support)
  - india_still_early_signal <- 1 - maturity_comparison.india_early_presence_score
  - sector_size_potential    <- normalized total historical funding across China+US
"""

from pathlib import Path

import pandas as pd

from src.config import (
    DATA_PROCESSED,
    ORIGIN_COUNTRIES,
    OUTPUTS_SIGNALS,
    TRANSFER_SCORE_WEIGHTS,
)
from src.features import minmax_normalize


def latest_value_per_sector(df: pd.DataFrame, country: str, column: str) -> pd.Series:
    subset = df[df["country"] == country]
    latest_idx = subset.groupby("sector")["year"].idxmax()
    return subset.loc[latest_idx].set_index("sector")[column]


def total_funding_by_sector(df: pd.DataFrame, countries: list[str]) -> pd.Series:
    subset = df[df["country"].isin(countries)]
    return subset.groupby("sector")["total_funding"].sum(min_count=1)


def compute_transfer_scores(
    sector_year: pd.DataFrame,
    maturity: pd.DataFrame,
    weights: dict = TRANSFER_SCORE_WEIGHTS,
) -> pd.DataFrame:
    eligible = maturity[maturity["china_us_deal_count"] > 0].copy()

    velocity_by_country = pd.concat(
        [latest_value_per_sector(sector_year, c, "velocity_score") for c in ORIGIN_COUNTRIES],
        axis=1,
    )
    china_us_velocity = velocity_by_country.mean(axis=1, skipna=True)

    size_raw = total_funding_by_sector(sector_year, ORIGIN_COUNTRIES)
    sector_size_potential = minmax_normalize(size_raw.dropna())

    eligible["china_us_velocity"] = eligible["sector"].map(china_us_velocity)
    eligible["historical_lag_match"] = eligible["china_us_maturity_score"]
    eligible["india_still_early_signal"] = 1 - eligible["india_early_presence_score"]
    eligible["sector_size_potential"] = eligible["sector"].map(sector_size_potential)

    for component in weights:
        eligible[component] = eligible[component].fillna(0)

    eligible["transfer_score"] = sum(
        weights[component] * eligible[component] for component in weights
    )

    return eligible.sort_values("transfer_score", ascending=False).reset_index(drop=True)


def build_transfer_scores(
    processed_dir: Path = DATA_PROCESSED,
    output_dir: Path = OUTPUTS_SIGNALS,
) -> None:
    sector_year = pd.read_csv(processed_dir / "sector_year_features.csv")
    maturity = pd.read_csv(processed_dir / "maturity_comparison.csv")

    result = compute_transfer_scores(sector_year, maturity)

    output_dir.mkdir(parents=True, exist_ok=True)
    result.to_csv(output_dir / "transfer_scores.csv", index=False)


if __name__ == "__main__":
    build_transfer_scores()
