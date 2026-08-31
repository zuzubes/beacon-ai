import math

import pandas as pd
import pytest

from src.clean import (
    clean_china_table,
    clean_india_table,
    clean_startup_funding_dataset_table,
    filter_country,
    normalize_country,
    normalize_sector,
    parse_amount_usd,
    parse_china_amount,
    parse_year_quarter,
    translate_china_field,
    translate_china_round,
)
from src.config import CHINA_FIELD_MAP, CHINA_ROUND_MAP, SECTOR_MAP


def test_normalize_country_maps_iso3_code():
    assert normalize_country("USA") == "United States"


def test_normalize_country_is_case_insensitive():
    assert normalize_country("india") == "India"


def test_normalize_country_strips_whitespace():
    assert normalize_country("  USA  ") == "United States"


def test_normalize_country_returns_none_for_unmapped_value():
    assert normalize_country("Australia") is None


def test_normalize_country_returns_none_for_nan():
    assert normalize_country(math.nan) is None


def test_parse_amount_usd_passes_through_plain_float():
    assert parse_amount_usd(55997.0) == 55997.0


def test_parse_amount_usd_strips_dollar_sign_and_commas():
    assert parse_amount_usd("$1,200,000") == 1_200_000.0


def test_parse_amount_usd_treats_undisclosed_as_none():
    assert parse_amount_usd("undisclosed") is None


def test_parse_amount_usd_returns_none_for_nan():
    assert parse_amount_usd(math.nan) is None


def test_parse_amount_usd_applies_scale_factor():
    assert parse_amount_usd(82.5, scale=1_000_000) == 82_500_000.0


def test_parse_china_amount_exact_yi_usd():
    amount, precision = parse_china_amount("1.35亿美元")
    assert amount == pytest.approx(135_000_000.0)
    assert precision == "exact"


def test_parse_china_amount_exact_wan_rmb_converts_to_usd():
    amount, precision = parse_china_amount("2000万人民币")
    assert amount == pytest.approx(20_000_000 * 0.14)
    assert precision == "exact"


def test_parse_china_amount_undisclosed():
    assert parse_china_amount("未透露") == (None, "undisclosed")


def test_parse_china_amount_bucket_several_million_rmb():
    amount, precision = parse_china_amount("数百万人民币")
    assert amount == pytest.approx(3_000_000 * 0.14)
    assert precision == "bucket_estimate"


def test_parse_china_amount_bucket_several_hundred_thousand_usd():
    amount, precision = parse_china_amount("数十万美元")
    assert amount == pytest.approx(500_000.0)
    assert precision == "bucket_estimate"


def test_parse_china_amount_open_ended_hundred_million_plus_bucket():
    amount, precision = parse_china_amount("亿元及以上人民币")
    assert amount == pytest.approx(150_000_000 * 0.14)
    assert precision == "bucket_estimate"


def test_parse_china_amount_unknown_currency_is_unconvertible():
    assert parse_china_amount("亿其他") == (None, "unknown_currency")


def test_parse_china_amount_returns_undisclosed_for_nan():
    assert parse_china_amount(math.nan) == (None, "undisclosed")


def test_normalize_sector_maps_known_alias_case_insensitively():
    assert normalize_sector("fintech", SECTOR_MAP) == "FinTech"


def test_normalize_sector_falls_back_to_title_case_for_unmapped_value():
    assert normalize_sector("robotics", SECTOR_MAP) == "Robotics"


def test_normalize_sector_returns_none_for_nan():
    assert normalize_sector(math.nan, SECTOR_MAP) is None


def test_translate_china_field_known_value():
    assert translate_china_field("电子商务", CHINA_FIELD_MAP) == "E-Commerce"


def test_translate_china_field_unknown_value_falls_back_to_other():
    assert translate_china_field("未知类别", CHINA_FIELD_MAP) == "Other"


def test_translate_china_round_known_value():
    assert translate_china_round("天使轮", CHINA_ROUND_MAP) == "Angel"


def test_translate_china_round_unknown_value_falls_back_to_unspecified():
    assert translate_china_round("???", CHINA_ROUND_MAP) == "Unspecified"


def test_parse_year_quarter_from_iso_date():
    assert parse_year_quarter("2016-07-03") == (2016, 3)


def test_parse_year_quarter_first_quarter_boundary():
    assert parse_year_quarter("2015-01-01") == (2015, 1)


def test_parse_year_quarter_from_bare_year_int():
    assert parse_year_quarter(2015) == (2015, None)


def test_parse_year_quarter_returns_none_none_for_nan():
    assert parse_year_quarter(math.nan) == (None, None)


def test_clean_china_table_standardises_columns():
    raw = pd.DataFrame(
        {
            "date": ["2016-09-10", "2016-09-09", "2016-01-01"],
            "company": ["新浪微博", "直麦网", "小公司"],
            "field": ["社交网络", "电子商务", "未知类别"],
            "place": ["北京", "北京", "上海"],
            "round": ["IPO上市后", "天使轮", "不明确"],
            "amount": ["1.35亿美元", "2000万人民币", "未透露"],
            "investor": ["软银", "投资方未透露", "投资方未透露"],
        }
    )

    result = clean_china_table(raw)

    assert list(result.columns) == [
        "company",
        "country",
        "sector",
        "round",
        "amount_usd",
        "amount_precision",
        "year",
        "quarter",
    ]
    assert (result["country"] == "China").all()
    assert result.loc[0, "sector"] == "Social Network"
    assert result.loc[0, "round"] == "Post-IPO"
    assert result.loc[0, "amount_usd"] == pytest.approx(135_000_000.0)
    assert result.loc[0, "amount_precision"] == "exact"
    assert result.loc[0, "year"] == 2016
    assert result.loc[0, "quarter"] == 3
    assert result.loc[2, "sector"] == "Other"
    assert pd.isna(result.loc[2, "amount_usd"])
    assert result.loc[2, "amount_precision"] == "undisclosed"


def test_clean_india_table_standardises_columns():
    raw = pd.DataFrame(
        {
            "startup": ["1mg", "SomeStartup", "Robotics Co"],
            "vertical": ["Healthcare", "eCommerce", "Robotics"],
            "round": ["Private Equity", "Seed Funding", "Seed Funding"],
            "amount": [49.5, 0.0, 2.5],
            "year": [2015, 2016, 2017],
        }
    )

    result = clean_india_table(raw)

    assert list(result.columns) == [
        "company",
        "country",
        "sector",
        "round",
        "amount_usd",
        "amount_precision",
        "year",
        "quarter",
    ]
    assert (result["country"] == "India").all()
    assert result.loc[0, "amount_usd"] == pytest.approx(49_500_000.0)
    assert result.loc[0, "amount_precision"] == "exact"
    assert pd.isna(result.loc[1, "amount_usd"])
    assert result.loc[1, "amount_precision"] == "undisclosed"
    assert result.loc[2, "sector"] == "Robotics"
    assert result.loc[0, "year"] == 2015
    assert pd.isna(result.loc[0, "quarter"])


def test_clean_startup_funding_dataset_table_standardises_columns():
    raw = pd.DataFrame(
        {
            "Startup Name": ["Acme Inc", "Beta LLC"],
            "Industry": ["Finance", "AI"],
            "Country": ["USA", "India"],
            "Funding Stage": ["Seed", "Series C"],
            "Amount Raised (USD)": [304706.0, 641212096.0],
            "Funding Date": ["2016-07-03", "2025-08-10"],
        }
    )

    result = clean_startup_funding_dataset_table(raw)

    assert list(result.columns) == [
        "company",
        "country",
        "sector",
        "round",
        "amount_usd",
        "amount_precision",
        "year",
        "quarter",
    ]
    assert result.loc[0, "country"] == "United States"
    assert result.loc[0, "sector"] == "FinTech"
    assert result.loc[0, "amount_usd"] == pytest.approx(304706.0)
    assert result.loc[0, "amount_precision"] == "exact"
    assert result.loc[0, "year"] == 2016
    assert result.loc[0, "quarter"] == 3


def test_filter_country_keeps_only_matching_rows():
    df = pd.DataFrame({"country": ["United States", "India", "United States"], "x": [1, 2, 3]})

    result = filter_country(df, "United States")

    assert result["country"].tolist() == ["United States", "United States"]
    assert result["x"].tolist() == [1, 3]
    assert result.index.tolist() == [0, 1]
