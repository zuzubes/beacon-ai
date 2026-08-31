"""LLM-generated partner-ready briefs for the top-ranked sectors (plan.md Phase 4)."""

import json
import re
from pathlib import Path

import pandas as pd
from langsmith import traceable
from openai import OpenAI
from pydantic import BaseModel

from src.config import BRIEF_MODEL, BRIEF_TOP_N, DATA_PROCESSED, OUTPUTS_BRIEFS, OUTPUTS_SIGNALS


class Brief(BaseModel):
    headline: str
    why_rising_abroad: str
    india_opportunity: str
    key_risks: list[str]
    confidence_note: str


def slugify_sector(name: str) -> str:
    text = name.strip().lower().replace("&", "and")
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def select_top_sectors(df: pd.DataFrame, n: int = BRIEF_TOP_N) -> pd.DataFrame:
    return df.sort_values("transfer_score", ascending=False).head(n).reset_index(drop=True)


def build_brief_prompt(row: dict) -> str:
    return (
        f"Sector: {row['sector']}\n"
        f"Transfer score (0-1, higher = stronger signal it will transfer to India): "
        f"{row['transfer_score']:.2f}\n"
        f"China/US velocity (recent growth + deal volume, 0-1): {row['china_us_velocity']:.2f}\n"
        f"China/US maturity vs India's early presence (0-1): {row['historical_lag_match']:.2f}\n"
        f"India still-early signal (0-1, higher = less saturated in India so far): "
        f"{row['india_still_early_signal']:.2f}\n"
        f"Sector size potential, normalized total China/US funding (0-1): "
        f"{row['sector_size_potential']:.2f}\n"
        f"China+US deal count backing this signal: {row['china_us_deal_count']}\n"
        f"India early-window deal count: {row['india_early_deal_count']}\n\n"
        "Write a short partner-ready investment brief using ONLY the data above. "
        "Do not invent specific company names, deal amounts, or facts not given here."
    )


@traceable(name="generate_brief")
def generate_brief(client, row: dict, model: str = BRIEF_MODEL) -> Brief:
    response = client.responses.parse(
        model=model,
        instructions=(
            "You are a research analyst writing concise briefs for a small Indian VC firm "
            "about startup categories rising in China/US that may be early opportunities in "
            "India. Be grounded and specific to the provided numbers; do not fabricate facts."
        ),
        input=build_brief_prompt(row),
        text_format=Brief,
    )
    return response.output_parsed


def render_brief_markdown(row: dict, brief: Brief) -> str:
    risks = "\n".join(f"- {risk}" for risk in brief.key_risks)
    return (
        f"# {row['sector']}\n\n"
        f"**Transfer score**: {row['transfer_score']:.2f}\n\n"
        f"## {brief.headline}\n\n"
        f"### Why it's rising in China/US\n{brief.why_rising_abroad}\n\n"
        f"### India opportunity\n{brief.india_opportunity}\n\n"
        f"### Key risks\n{risks}\n\n"
        f"### Confidence note\n{brief.confidence_note}\n"
    )


def generate_briefs(
    transfer_scores: pd.DataFrame, client, top_n: int = BRIEF_TOP_N, model: str = BRIEF_MODEL
) -> list[dict]:
    top_sectors = select_top_sectors(transfer_scores, n=top_n)
    results = []
    for row in top_sectors.to_dict(orient="records"):
        brief = generate_brief(client, row, model=model)
        results.append({"sector": row["sector"], "transfer_score": row["transfer_score"], **brief.model_dump()})
    return results


def build_briefs(
    processed_dir: Path = DATA_PROCESSED,
    signals_dir: Path = OUTPUTS_SIGNALS,
    output_dir: Path = OUTPUTS_BRIEFS,
    top_n: int = BRIEF_TOP_N,
    model: str = BRIEF_MODEL,
) -> None:
    transfer_scores = pd.read_csv(signals_dir / "transfer_scores.csv")
    client = OpenAI()

    output_dir.mkdir(parents=True, exist_ok=True)
    briefs_json = []
    top_sectors = select_top_sectors(transfer_scores, n=top_n)
    for row in top_sectors.to_dict(orient="records"):
        brief = generate_brief(client, row, model=model)
        (output_dir / f"{slugify_sector(row['sector'])}.md").write_text(
            render_brief_markdown(row, brief)
        )
        briefs_json.append({"sector": row["sector"], "transfer_score": row["transfer_score"], **brief.model_dump()})

    (output_dir / "briefs.json").write_text(json.dumps(briefs_json, indent=2))


if __name__ == "__main__":
    build_briefs()
