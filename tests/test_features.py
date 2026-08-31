import numpy as np
import pandas as pd
import pytest

from src.features import (
    add_rising_flag,
    add_velocity_score,
    add_yoy_growth,
    aggregate_by_country_sector_year,
    build_processed_features,
    compute_maturity_comparison,
)


def test_aggregate_computes_deal_count_and_total_funding():
    df = pd.DataFrame(
        {
            "country": ["China", "China", "China", "India"],
            "sector": ["FinTech", "FinTech", "FinTech", "FinTech"],
            "year": [2015, 2015, 2016, 2015],
            "amount_usd": [1_000_000.0, 2_000_000.0, np.nan, 500_000.0],
        }
    )

    result = aggregate_by_country_sector_year(df)

    row_2015 = result[
        (result["country"] == "China") & (result["year"] == 2015)
    ].iloc[0]
    assert row_2015["deal_count"] == 2
    assert row_2015["total_funding"] == pytest.approx(3_000_000.0)
    assert row_2015["avg_deal_size"] == pytest.approx(1_500_000.0)

    row_2016 = result[
        (result["country"] == "China") & (result["year"] == 2016)
    ].iloc[0]
    assert row_2016["deal_count"] == 1
    assert pd.isna(row_2016["total_funding"])
    assert pd.isna(row_2016["avg_deal_size"])


def test_add_yoy_growth_first_year_is_nan_and_second_year_computed():
    df = pd.DataFrame(
        {
            "country": ["China", "China", "China"],
            "sector": ["FinTech", "FinTech", "FinTech"],
            "year": [2014, 2015, 2016],
            "deal_count": [10, 20, 10],
            "total_funding": [1_000_000.0, 3_000_000.0, 0.0],
        }
    )

    result = add_yoy_growth(df)

    row_2014 = result[result["year"] == 2014].iloc[0]
    assert pd.isna(row_2014["yoy_deal_growth"])
    assert pd.isna(row_2014["yoy_funding_growth"])

    row_2015 = result[result["year"] == 2015].iloc[0]
    assert row_2015["yoy_deal_growth"] == pytest.approx(1.0)
    assert row_2015["yoy_funding_growth"] == pytest.approx(2.0)

    row_2016 = result[result["year"] == 2016].iloc[0]
    assert row_2016["yoy_deal_growth"] == pytest.approx(-0.5)


def test_add_yoy_growth_guards_against_division_by_zero_previous_year():
    df = pd.DataFrame(
        {
            "country": ["India", "India"],
            "sector": ["EdTech", "EdTech"],
            "year": [2019, 2020],
            "deal_count": [0, 5],
            "total_funding": [0.0, 1_000_000.0],
        }
    )

    result = add_yoy_growth(df)

    row_2020 = result[result["year"] == 2020].iloc[0]
    assert pd.isna(row_2020["yoy_deal_growth"])
    assert pd.isna(row_2020["yoy_funding_growth"])


def test_add_velocity_score_min_max_normalizes_within_country():
    df = pd.DataFrame(
        {
            "country": ["China", "China", "China"],
            "sector": ["X", "Y", "Z"],
            "deal_count": [10, 50, 100],
            "yoy_deal_growth": [0.0, 1.0, 2.0],
        }
    )

    result = add_velocity_score(df)

    row_x = result[result["sector"] == "X"].iloc[0]
    row_z = result[result["sector"] == "Z"].iloc[0]
    assert row_x["velocity_score"] == pytest.approx(0.0)
    assert row_z["velocity_score"] == pytest.approx(1.0)


def test_add_velocity_score_clips_extreme_growth_outliers():
    df = pd.DataFrame(
        {
            "country": ["India", "India"],
            "sector": ["X", "Y"],
            "deal_count": [10, 10],
            "yoy_deal_growth": [0.0, 50.0],
        }
    )

    result = add_velocity_score(df, growth_clip=(-1.0, 3.0))

    row_y = result[result["sector"] == "Y"].iloc[0]
    # 50.0 clipped to 3.0 before normalizing -> same as if it were exactly 3.0.
    # deal_count is equal (10 vs 10) for both rows, so the volume component
    # is neutral (0.5) for both; only the growth half of the score differs:
    # 0.5 * norm_growth(1.0) + 0.5 * neutral_volume(0.5) = 0.75
    assert row_y["velocity_score"] == pytest.approx(0.75)


def test_add_rising_flag_requires_both_growth_and_volume():
    df = pd.DataFrame(
        {
            "sector": ["above_both", "growth_only", "volume_only", "no_growth_data"],
            "yoy_deal_growth": [0.30, 0.30, 0.05, float("nan")],
            "deal_count": [10, 2, 10, 10],
        }
    )

    result = add_rising_flag(df, growth_threshold=0.20, deal_count_floor=5)

    assert result.set_index("sector")["rising"].to_dict() == {
        "above_both": True,
        "growth_only": False,
        "volume_only": False,
        "no_growth_data": False,
    }


def test_compute_maturity_comparison_flags_sectors_mature_abroad_but_early_in_india():
    rows = (
        # China: FinTech mature in the recent 3-year window (2014-2016), one
        # 2010 row is outside the window and must be excluded.
        [{"country": "China", "sector": "FinTech", "year": y} for y in [2010, 2014, 2014, 2015, 2015, 2016]]
        + [{"country": "China", "sector": "Gaming", "year": 2016}]
        # US: FinTech has some presence too (US window = all years, it's a short series).
        + [{"country": "United States", "sector": "FinTech", "year": 2020}] * 2
        # India: FinTech barely present in its early window (2015-2017);
        # Gaming is already well established there. The 2020 Gaming row is
        # outside the early window and must be excluded.
        + [{"country": "India", "sector": "FinTech", "year": 2015}]
        + [{"country": "India", "sector": "Gaming", "year": y} for y in [2015, 2015, 2016, 2016, 2017]]
        + [{"country": "India", "sector": "Gaming", "year": 2020}]
    )
    df = pd.DataFrame(rows)

    result = compute_maturity_comparison(df, china_recent_n=3, india_early_n=3).set_index("sector")

    assert result.loc["FinTech", "china_us_deal_count"] == 7  # 5 China (in-window) + 2 US
    assert result.loc["Gaming", "china_us_deal_count"] == 1
    assert result.loc["FinTech", "india_early_deal_count"] == 1
    assert result.loc["Gaming", "india_early_deal_count"] == 5

    assert bool(result.loc["FinTech", "still_early_in_india"]) is True
    assert bool(result.loc["Gaming", "still_early_in_india"]) is False


def test_build_processed_features_writes_both_outputs(tmp_path):
    china = pd.DataFrame(
        {
            "country": ["China"] * 3,
            "sector": ["FinTech", "FinTech", "FinTech"],
            "year": [2014, 2015, 2016],
            "amount_usd": [1_000_000.0, 2_000_000.0, 3_000_000.0],
        }
    )
    india = pd.DataFrame(
        {
            "country": ["India"] * 2,
            "sector": ["FinTech", "FinTech"],
            "year": [2015, 2016],
            "amount_usd": [100_000.0, 200_000.0],
        }
    )
    us = pd.DataFrame(
        {
            "country": ["United States"] * 2,
            "sector": ["FinTech", "FinTech"],
            "year": [2016, 2017],
            "amount_usd": [500_000.0, 600_000.0],
        }
    )

    build_processed_features(china, india, us, output_dir=tmp_path)

    sector_year = pd.read_csv(tmp_path / "sector_year_features.csv")
    maturity = pd.read_csv(tmp_path / "maturity_comparison.csv")

    for col in ["deal_count", "total_funding", "yoy_deal_growth", "velocity_score", "rising"]:
        assert col in sector_year.columns
    assert set(sector_year["country"]) == {"China", "India", "United States"}

    for col in ["china_us_maturity_score", "india_early_presence_score", "still_early_in_india"]:
        assert col in maturity.columns
    assert maturity["sector"].tolist() == ["FinTech"]
