"""Paths, constants, and mapping tables shared across the pipeline (see plan.md)."""

from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

DATA_DIR = ROOT_DIR / "data"
DATA_RAW = DATA_DIR / "raw"
DATA_INTERIM = DATA_DIR / "interim"
DATA_PROCESSED = DATA_DIR / "processed"

OUTPUTS_DIR = ROOT_DIR / "outputs"
OUTPUTS_SIGNALS = OUTPUTS_DIR / "signals"
OUTPUTS_BRIEFS = OUTPUTS_DIR / "briefs"
OUTPUTS_DASHBOARD = OUTPUTS_DIR / "dashboard"

# Raw files actually used by src/load.py (see plan.md Phase 1 notes for why the
# rest of data/raw/ — the Crunchbase sample pair, vc_trend_data.csv, the CB
# Insights .xlsx reports — isn't in this pipeline: either a broken join or
# never selected as a source).
RAW_FILES = {
    "china_events": DATA_RAW / "China-invest_event.csv",
    "india_funding": DATA_RAW / "Indian_startups_funding.csv",
    "startup_funding_dataset": DATA_RAW / "startup_funding_dataset (1).csv",
}

# Normalise country codes / free-text variants seen across sources
# (Crunchbase ISO codes in funding_rounds/organizations/acquisitions,
# free text in startup_funding_dataset and vc_trend_data).
COUNTRY_MAP = {
    "CN": "China",
    "CHN": "China",
    "CHINA": "China",
    "US": "United States",
    "USA": "United States",
    "U.S.": "United States",
    "U.S.A.": "United States",
    "UNITED STATES": "United States",
    "UNITED STATES OF AMERICA": "United States",
    "IN": "India",
    "IND": "India",
    "INDIA": "India",
}

# Starter sector alias map — source vocabularies differ per dataset
# (Crunchbase category_list, vc_trend_data.sector, China-invest_event.field,
# Indian_startups_funding.vertical, startup_funding_dataset.Industry).
# Expand this during Phase 1 once each raw column's distinct values are profiled.
SECTOR_MAP = {
    "FINTECH": "FinTech",
    "FINANCIAL SERVICES": "FinTech",
    "FINANCIAL TECHNOLOGY": "FinTech",
    "EDTECH": "EdTech",
    "EDUCATION": "EdTech",
    "HEALTHTECH": "HealthTech",
    "HEALTH CARE": "HealthTech",
    "HEALTHCARE": "HealthTech",
    "E-COMMERCE": "E-Commerce",
    "ECOMMERCE": "E-Commerce",
    "ARTIFICIAL INTELLIGENCE": "AI",
    "AI": "AI",
    "MACHINE LEARNING": "AI",
    "SAAS": "SaaS",
    "SOFTWARE": "SaaS",
    "LOGISTICS": "Logistics",
    "SUPPLY CHAIN MANAGEMENT": "Logistics",
    "CLEAN ENERGY": "CleanTech",
    "CLEANTECH": "CleanTech",
    "RENEWABLE ENERGY": "CleanTech",
    "FINANCE": "FinTech",
    "HEALTH": "HealthTech",
    # Added after profiling Indian_startups_funding.csv's `vertical` column
    # (see plan.md Phase 2 notes) — only labels with an honest 1:1 match to
    # China's canonical categories (CHINA_FIELD_MAP) are added here. Genuinely
    # ambiguous India-only labels (Consumer Internet, Technology, Food,
    # Personal Care, ...) are left unmapped and fall back to title-case rather
    # than being force-fit into a China bucket.
    "TRANSPORTATION": "Auto & Transportation",
    "AUTOMOTIVE": "Auto & Transportation",
    "ENTERTAINMENT": "Entertainment",
    "MARKETING": "Advertising & Marketing",
    "DELIVERY": "Logistics",
    "REAL ESTATE": "Real Estate Services",
    "IT": "Enterprise Services",
}

# --- Phase 2 feature engineering ------------------------------------------
# velocity_score = growth_weight * normalized(yoy_deal_growth) + volume_weight * normalized(log1p(deal_count))
# normalized within each country (so China's much larger row count doesn't
# swamp India's/US's own sector landscape) via min-max scaling per year.
VELOCITY_GROWTH_WEIGHT = 0.5
VELOCITY_VOLUME_WEIGHT = 0.5
# yoy_deal_growth is winsorized to this range before normalizing, so a few
# small-denominator outliers (e.g. 1 deal -> 10 deals = 900% growth) don't
# dominate the min-max scale.
VELOCITY_GROWTH_CLIP = (-1.0, 3.0)

# rising_flag = yoy_deal_growth > threshold AND deal_count >= floor
RISING_GROWTH_THRESHOLD = 0.20
RISING_DEAL_COUNT_FLOOR = 5

# Maturity-comparison window sizes (see plan.md Phase 2 note): since China's
# and India's/US's data windows barely overlap, "lag in years" isn't
# estimable. Instead we compare China's/US's most recent N years (their most
# mature signal) against India's earliest N years (its least mature signal)
# per sector.
MATURITY_RECENT_YEARS_N = 3
INDIA_EARLY_YEARS_N = 3

ORIGIN_COUNTRIES = ["China", "United States"]
DESTINATION_COUNTRY = "India"

# --- Phase 3 transfer probability scoring ----------------------------------
# transfer_score = 0.40 * china_us_velocity + 0.25 * historical_lag_match
#                + 0.20 * india_still_early_signal + 0.15 * sector_size_potential
# See plan.md Phase 3 notes for how each component maps onto Phase 2's output
# (the plan's original "historical lag match" is Phase 2's maturity-comparison
# substitute, china_us_maturity_score).
TRANSFER_SCORE_WEIGHTS = {
    "china_us_velocity": 0.40,
    "historical_lag_match": 0.25,
    "india_still_early_signal": 0.20,
    "sector_size_potential": 0.15,
}

# --- Phase 4 brief generation ----------------------------------------------
BRIEF_MODEL = "gpt-4o-mini"
BRIEF_TOP_N = 5

# --- China-invest_event.csv specifics -------------------------------------
# The file is GB18030-encoded (Chinese GBK), not UTF-8.
CHINA_ENCODING = "gb18030"

# Chinese magnitude words used in precise amounts, e.g. "2000万人民币" = 2000 * 10,000 CNY.
CHINA_MAGNITUDE = {
    "万": 10_000,
    "亿": 100_000_000,
}

# ~52% of China rows report a vague bucket phrase instead of a precise amount
# (e.g. "数百万人民币" = "several million RMB"). Representative point estimates,
# in the ORIGINAL currency, chosen as the geometric-ish midpoint of each bucket's
# implied range. These are approximations for trend signal, not precise dollar
# amounts — flagged downstream via an `amount_precision` column.
CHINA_BUCKET_ESTIMATES = {
    "数十万": 500_000,        # "several hundred thousand" -> ~100K-1M range
    "数百万": 3_000_000,      # "several million" -> ~1M-10M range
    "数千万": 30_000_000,     # "tens of millions" -> ~10M-100M range
    "亿元及以上": 150_000_000,  # "100M+ " open-ended bucket -> representative floor+
}

# Approximate flat FX rates to USD (not date-specific — fine for trend signal,
# not for precise financial reporting).
CHINA_CURRENCY_TO_USD = {
    "人民币": 0.14,   # CNY
    "美元": 1.0,      # USD
    "港元": 0.128,    # HKD
    "新台币": 0.031,  # TWD
    "日元": 0.0067,   # JPY
    "英镑": 1.27,     # GBP
}
# "其他" (other/unspecified currency) is intentionally excluded — unconvertible.

# field (sector) values -> canonical English sector. "上海" (Shanghai, a city)
# appears as a data-entry error in the source `field` column, not a real sector.
CHINA_FIELD_MAP = {
    "企业服务": "Enterprise Services",
    "体育运动": "Sports",
    "医疗健康": "HealthTech",
    "工具软件": "SaaS",
    "广告营销": "Advertising & Marketing",
    "房产服务": "Real Estate Services",
    "教育": "EdTech",
    "文化娱乐": "Entertainment",
    "旅游": "Travel",
    "本地生活": "Local Services",
    "汽车交通": "Auto & Transportation",
    "游戏": "Gaming",
    "物流": "Logistics",
    "电子商务": "E-Commerce",
    "硬件": "Hardware",
    "社交网络": "Social Network",
    "移动互联网": "Mobile Internet",
    "金融": "FinTech",
    "上海": "Other",
}

# round (investment stage) values -> canonical English label.
# "盛大资本-盛大网络" is an investor name that leaked into the round column upstream.
CHINA_ROUND_MAP = {
    "种子轮": "Seed",
    "天使轮": "Angel",
    "Pre-A轮": "Pre-Series A",
    "A轮": "Series A",
    "A+轮": "Series A+",
    "Pre-B轮": "Pre-Series B",
    "B轮": "Series B",
    "B+轮": "Series B+",
    "C轮": "Series C",
    "D轮": "Series D",
    "E轮": "Series E",
    "F轮-上市前": "Series F (Pre-IPO)",
    "战略投资": "Strategic Investment",
    "新三板": "NEEQ Listing",
    "IPO上市": "IPO",
    "IPO上市后": "Post-IPO",
    "不明确": "Unspecified",
    "盛大资本-盛大网络": "Unspecified",
}
