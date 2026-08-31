"""Pure transformation functions used to standardise raw datasets (see plan.md Phase 1)."""

import math
import re

import pandas as pd

from src.config import (
    CHINA_BUCKET_ESTIMATES,
    CHINA_CURRENCY_TO_USD,
    CHINA_FIELD_MAP,
    CHINA_MAGNITUDE,
    CHINA_ROUND_MAP,
    COUNTRY_MAP,
    SECTOR_MAP,
)

INDIA_AMOUNT_SCALE = 1_000_000  # `amount` column is in USD millions

_UNDISCLOSED_TOKENS = {"undisclosed", "n/a", "na", "unknown", ""}


def _is_nan(value) -> bool:
    return isinstance(value, float) and math.isnan(value)


def normalize_country(value) -> str | None:
    if value is None or _is_nan(value):
        return None
    return COUNTRY_MAP.get(str(value).strip().upper())


def parse_amount_usd(value, scale: float = 1.0) -> float | None:
    if value is None or _is_nan(value):
        return None
    if isinstance(value, (int, float)):
        return float(value) * scale
    text = str(value).strip()
    if text.lower() in _UNDISCLOSED_TOKENS:
        return None
    cleaned = re.sub(r"[$,]", "", text)
    try:
        return float(cleaned) * scale
    except ValueError:
        return None


_CHINA_MAGNITUDE_RE = re.compile(r"^([\d.]+)(万|亿)$")


def parse_china_amount(value) -> tuple[float | None, str]:
    if value is None or _is_nan(value):
        return (None, "undisclosed")
    text = str(value).strip()
    if text == "未透露":
        return (None, "undisclosed")

    currency = next((c for c in CHINA_CURRENCY_TO_USD if text.endswith(c)), None)
    if currency is None:
        if text.endswith("其他"):
            return (None, "unknown_currency")
        return (None, "unparsed")

    body = text[: -len(currency)]
    fx_rate = CHINA_CURRENCY_TO_USD[currency]

    if body in CHINA_BUCKET_ESTIMATES:
        return (CHINA_BUCKET_ESTIMATES[body] * fx_rate, "bucket_estimate")

    match = _CHINA_MAGNITUDE_RE.match(body)
    if match:
        number, unit = match.groups()
        return (float(number) * CHINA_MAGNITUDE[unit] * fx_rate, "exact")

    return (None, "unparsed")


def normalize_sector(value, mapping: dict) -> str | None:
    if value is None or _is_nan(value):
        return None
    text = str(value).strip()
    return mapping.get(text.upper(), text.title())


def translate_china_field(value, mapping: dict) -> str:
    return mapping.get(value, "Other")


def translate_china_round(value, mapping: dict) -> str:
    return mapping.get(value, "Unspecified")


def parse_year_quarter(value) -> tuple[int | None, int | None]:
    if value is None or _is_nan(value):
        return (None, None)
    if isinstance(value, (int, float)):
        return (int(value), None)
    text = str(value).strip()
    match = re.match(r"^(\d{4})-(\d{2})-\d{2}", text)
    if match:
        year, month = int(match.group(1)), int(match.group(2))
        return (year, (month - 1) // 3 + 1)
    if re.match(r"^\d{4}$", text):
        return (int(text), None)
    return (None, None)


def clean_china_table(raw: pd.DataFrame) -> pd.DataFrame:
    amounts = raw["amount"].apply(parse_china_amount)
    year_quarter = raw["date"].apply(parse_year_quarter)
    return pd.DataFrame(
        {
            "company": raw["company"],
            "country": "China",
            "sector": raw["field"].apply(translate_china_field, args=(CHINA_FIELD_MAP,)),
            "round": raw["round"].apply(translate_china_round, args=(CHINA_ROUND_MAP,)),
            "amount_usd": amounts.apply(lambda t: t[0]),
            "amount_precision": amounts.apply(lambda t: t[1]),
            "year": year_quarter.apply(lambda t: t[0]),
            "quarter": year_quarter.apply(lambda t: t[1]),
        }
    )


def clean_india_table(raw: pd.DataFrame) -> pd.DataFrame:
    # A raw amount of exactly 0 marks an undisclosed round in this dataset, not a $0 deal.
    amount_usd = raw["amount"].apply(
        lambda v: None if v == 0 else parse_amount_usd(v, scale=INDIA_AMOUNT_SCALE)
    )
    return pd.DataFrame(
        {
            "company": raw["startup"],
            "country": "India",
            "sector": raw["vertical"].apply(normalize_sector, args=(SECTOR_MAP,)),
            "round": raw["round"].str.strip(),
            "amount_usd": amount_usd,
            "amount_precision": amount_usd.apply(lambda v: "undisclosed" if pd.isna(v) else "exact"),
            "year": raw["year"].apply(lambda t: parse_year_quarter(t)[0]),
            "quarter": raw["year"].apply(lambda t: parse_year_quarter(t)[1]),
        }
    )


def clean_startup_funding_dataset_table(raw: pd.DataFrame) -> pd.DataFrame:
    year_quarter = raw["Funding Date"].apply(parse_year_quarter)
    return pd.DataFrame(
        {
            "company": raw["Startup Name"],
            "country": raw["Country"].apply(normalize_country),
            "sector": raw["Industry"].apply(normalize_sector, args=(SECTOR_MAP,)),
            "round": raw["Funding Stage"].str.strip(),
            "amount_usd": raw["Amount Raised (USD)"].apply(parse_amount_usd),
            "amount_precision": "exact",
            "year": year_quarter.apply(lambda t: t[0]),
            "quarter": year_quarter.apply(lambda t: t[1]),
        }
    )


def filter_country(df: pd.DataFrame, country: str) -> pd.DataFrame:
    return df[df["country"] == country].reset_index(drop=True)
