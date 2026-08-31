"""Sector-year feature engineering: velocity, growth, and maturity comparison (plan.md Phase 2)."""

from pathlib import Path

import numpy as np
import pandas as pd

from src.config import (
    DESTINATION_COUNTRY,
    INDIA_EARLY_YEARS_N,
    MATURITY_RECENT_YEARS_N,
    ORIGIN_COUNTRIES,
    DATA_INTERIM,
    DATA_PROCESSED,
    RISING_DEAL_COUNT_FLOOR,
    RISING_GROWTH_THRESHOLD,
    VELOCITY_GROWTH_CLIP,
    VELOCITY_GROWTH_WEIGHT,
    VELOCITY_VOLUME_WEIGHT,
)


def aggregate_by_country_sector_year(df: pd.DataFrame) -> pd.DataFrame:
    grouped = df.groupby(["country", "sector", "year"], as_index=False).agg(
        deal_count=("year", "size"),
        total_funding=("amount_usd", lambda s: s.sum(min_count=1)),
    )
    grouped["avg_deal_size"] = grouped["total_funding"] / grouped["deal_count"]
    return grouped


def _yoy_growth(current: pd.Series, previous: pd.Series) -> pd.Series:
    growth = (current - previous) / previous
    return growth.where((previous != 0) & previous.notna())


def add_yoy_growth(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values(["country", "sector", "year"]).reset_index(drop=True)
    group = df.groupby(["country", "sector"])
    prev_deal_count = group["deal_count"].shift(1)
    prev_total_funding = group["total_funding"].shift(1)

    df["yoy_deal_growth"] = _yoy_growth(df["deal_count"], prev_deal_count)
    df["yoy_funding_growth"] = _yoy_growth(df["total_funding"], prev_total_funding)
    return df


def minmax_normalize_within_group(series: pd.Series, group_key: pd.Series) -> pd.Series:
    group_min = series.groupby(group_key).transform("min")
    group_max = series.groupby(group_key).transform("max")
    span = group_max - group_min
    normalized = (series - group_min) / span
    return normalized.where(span != 0, 0.5)


def add_velocity_score(
    df: pd.DataFrame,
    growth_weight: float = VELOCITY_GROWTH_WEIGHT,
    volume_weight: float = VELOCITY_VOLUME_WEIGHT,
    growth_clip: tuple[float, float] = VELOCITY_GROWTH_CLIP,
) -> pd.DataFrame:
    df = df.copy()
    clipped_growth = df["yoy_deal_growth"].clip(*growth_clip)
    norm_growth = minmax_normalize_within_group(clipped_growth, df["country"])
    norm_volume = minmax_normalize_within_group(np.log1p(df["deal_count"]), df["country"])
    df["velocity_score"] = growth_weight * norm_growth + volume_weight * norm_volume
    return df


def minmax_normalize(series: pd.Series) -> pd.Series:
    span = series.max() - series.min()
    if span == 0:
        return pd.Series(0.5, index=series.index)
    return (series - series.min()) / span


def _recent_years(df: pd.DataFrame, n: int) -> pd.DataFrame:
    return df[df["year"] > df["year"].max() - n]


def _earliest_years(df: pd.DataFrame, n: int) -> pd.DataFrame:
    return df[df["year"] < df["year"].min() + n]


def compute_maturity_comparison(
    df: pd.DataFrame,
    china_recent_n: int = MATURITY_RECENT_YEARS_N,
    india_early_n: int = INDIA_EARLY_YEARS_N,
) -> pd.DataFrame:
    """Sector-level "still early in India, already maturing abroad" comparison.

    Replaces the plan's literal "average lag in years" feature: China's data
    ends right where India's/US's begins, so a real lag can't be estimated.
    Instead this compares China's/US's most recent years (their most mature
    signal) against India's earliest years (its least mature signal).
    """
    origin = df[df["country"].isin(ORIGIN_COUNTRIES)]
    destination = df[df["country"] == DESTINATION_COUNTRY]

    origin_window = pd.concat(
        [_recent_years(origin[origin["country"] == c], china_recent_n) for c in ORIGIN_COUNTRIES]
    )
    destination_window = _earliest_years(destination, india_early_n)

    origin_counts = origin_window.groupby("sector").size()
    destination_counts = destination_window.groupby("sector").size()

    sectors = sorted(set(origin_counts.index) | set(destination_counts.index))
    result = pd.DataFrame({"sector": sectors})
    result["china_us_deal_count"] = (
        result["sector"].map(origin_counts).fillna(0).astype(int)
    )
    result["india_early_deal_count"] = (
        result["sector"].map(destination_counts).fillna(0).astype(int)
    )

    result["china_us_maturity_score"] = minmax_normalize(result["china_us_deal_count"])
    result["india_early_presence_score"] = minmax_normalize(result["india_early_deal_count"])

    result["still_early_in_india"] = (
        result["china_us_maturity_score"] > result["china_us_maturity_score"].median()
    ) & (result["india_early_presence_score"] < result["india_early_presence_score"].median())

    return result


def add_rising_flag(
    df: pd.DataFrame,
    growth_threshold: float = RISING_GROWTH_THRESHOLD,
    deal_count_floor: int = RISING_DEAL_COUNT_FLOOR,
) -> pd.DataFrame:
    df = df.copy()
    df["rising"] = (df["yoy_deal_growth"] > growth_threshold) & (
        df["deal_count"] >= deal_count_floor
    )
    return df


def build_processed_features(
    china: pd.DataFrame,
    india: pd.DataFrame,
    us: pd.DataFrame,
    output_dir: Path = DATA_PROCESSED,
) -> None:
    combined = pd.concat([china, india, us], ignore_index=True)

    sector_year = aggregate_by_country_sector_year(combined)
    sector_year = add_yoy_growth(sector_year)
    sector_year = add_velocity_score(sector_year)
    sector_year = add_rising_flag(sector_year)

    maturity = compute_maturity_comparison(combined)

    output_dir.mkdir(parents=True, exist_ok=True)
    sector_year.to_csv(output_dir / "sector_year_features.csv", index=False)
    maturity.to_csv(output_dir / "maturity_comparison.csv", index=False)


def load_interim_tables(
    interim_dir: Path = DATA_INTERIM,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    china = pd.read_csv(interim_dir / "china_clean.csv")
    india = pd.read_csv(interim_dir / "india_clean.csv")
    us = pd.read_csv(interim_dir / "us_clean.csv")
    return china, india, us


if __name__ == "__main__":
    build_processed_features(*load_interim_tables())
