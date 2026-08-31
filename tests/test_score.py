import pandas as pd
import pytest

from src.score import (
    compute_transfer_scores,
    latest_value_per_sector,
    total_funding_by_sector,
)


def test_latest_value_per_sector_picks_each_sectors_own_max_year():
    df = pd.DataFrame(
        {
            "country": ["China", "China", "China", "United States"],
            "sector": ["FinTech", "FinTech", "Gaming", "FinTech"],
            "year": [2015, 2016, 2016, 2020],
            "velocity_score": [0.6, 0.8, 0.2, 0.4],
        }
    )

    result = latest_value_per_sector(df, "China", "velocity_score")

    assert result.to_dict() == {"FinTech": 0.8, "Gaming": 0.2}


def test_total_funding_by_sector_sums_across_given_countries():
    df = pd.DataFrame(
        {
            "country": ["China", "United States", "India"],
            "sector": ["FinTech", "FinTech", "FinTech"],
            "total_funding": [1_000_000.0, 500_000.0, 999.0],
        }
    )

    result = total_funding_by_sector(df, ["China", "United States"])

    assert result.to_dict() == {"FinTech": 1_500_000.0}


def test_compute_transfer_scores_ranks_and_excludes_sectors_absent_from_origin():
    sector_year = pd.DataFrame(
        {
            "country": [
                "China", "China", "United States", "United States", "India", "China",
            ],
            "sector": ["FinTech", "FinTech", "FinTech", "FinTech", "FinTech", "Gaming"],
            "year": [2015, 2016, 2020, 2021, 2015, 2016],
            "velocity_score": [0.6, 0.8, 0.4, 0.6, 0.1, 0.2],
            "total_funding": [1_000_000.0, 2_000_000.0, 500_000.0, 800_000.0, 100_000.0, 50_000.0],
        }
    )
    maturity = pd.DataFrame(
        {
            "sector": ["FinTech", "Gaming", "ZeroPresence"],
            "china_us_deal_count": [10, 3, 0],
            "china_us_maturity_score": [1.0, 0.3, 0.0],
            "india_early_presence_score": [0.2, 0.8, 0.1],
        }
    )

    result = compute_transfer_scores(sector_year, maturity)

    assert result["sector"].tolist() == ["FinTech", "Gaming"]
    assert result.iloc[0]["transfer_score"] == pytest.approx(0.84)
    assert result.iloc[1]["transfer_score"] == pytest.approx(0.195)
    assert result["transfer_score"].is_monotonic_decreasing
