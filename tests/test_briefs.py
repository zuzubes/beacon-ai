import pandas as pd
import pytest

from src.briefs import (
    Brief,
    build_brief_prompt,
    generate_briefs,
    render_brief_markdown,
    select_top_sectors,
    slugify_sector,
)


class _StubParseResult:
    def __init__(self, output_parsed):
        self.output_parsed = output_parsed


class _StubResponses:
    def __init__(self):
        self.calls = []

    def parse(self, *, model, instructions, input, text_format):
        self.calls.append({"model": model, "input": input})
        return _StubParseResult(
            text_format(
                headline="Stub headline",
                why_rising_abroad="Stub reason.",
                india_opportunity="Stub opportunity.",
                key_risks=["Stub risk"],
                confidence_note="Stub confidence.",
            )
        )


class _StubClient:
    def __init__(self):
        self.responses = _StubResponses()


def test_slugify_sector_lowercases_and_hyphenates():
    assert slugify_sector("FinTech") == "fintech"


def test_slugify_sector_handles_ampersand_and_spaces():
    assert slugify_sector("Advertising & Marketing") == "advertising-and-marketing"


def test_select_top_sectors_returns_n_highest_scores():
    df = pd.DataFrame(
        {
            "sector": ["A", "B", "C", "D"],
            "transfer_score": [0.5, 0.9, 0.3, 0.7],
        }
    )

    result = select_top_sectors(df, n=2)

    assert result["sector"].tolist() == ["B", "D"]


def test_build_brief_prompt_includes_sector_and_key_numbers():
    row = {
        "sector": "FinTech",
        "transfer_score": 0.6907,
        "china_us_velocity": 0.5571,
        "historical_lag_match": 0.7816,
        "india_still_early_signal": 0.7473,
        "sector_size_potential": 0.8201,
        "china_us_deal_count": 1102,
        "india_early_deal_count": 162,
    }

    prompt = build_brief_prompt(row)

    assert "FinTech" in prompt
    assert "1102" in prompt
    assert "162" in prompt
    assert "0.69" in prompt


def test_render_brief_markdown_includes_headline_and_score():
    row = {"sector": "FinTech", "transfer_score": 0.6907}
    brief = Brief(
        headline="FinTech is heating up",
        why_rising_abroad="Explanation here.",
        india_opportunity="Opportunity here.",
        key_risks=["Risk one", "Risk two"],
        confidence_note="Based on limited China/US overlap data.",
    )

    markdown = render_brief_markdown(row, brief)

    assert "# FinTech" in markdown
    assert "FinTech is heating up" in markdown
    assert "0.69" in markdown
    assert "Risk one" in markdown
    assert "Risk two" in markdown


def test_generate_briefs_calls_client_once_per_top_sector():
    df = pd.DataFrame(
        {
            "sector": ["FinTech", "Gaming", "EdTech"],
            "transfer_score": [0.9, 0.5, 0.7],
            "china_us_velocity": [0.5, 0.5, 0.5],
            "historical_lag_match": [0.5, 0.5, 0.5],
            "india_still_early_signal": [0.5, 0.5, 0.5],
            "sector_size_potential": [0.5, 0.5, 0.5],
            "china_us_deal_count": [100, 100, 100],
            "india_early_deal_count": [10, 10, 10],
        }
    )
    client = _StubClient()

    results = generate_briefs(df, client, top_n=2)

    assert len(client.responses.calls) == 2
    assert [r["sector"] for r in results] == ["FinTech", "EdTech"]
    assert results[0]["headline"] == "Stub headline"
    assert results[0]["key_risks"] == ["Stub risk"]
    assert results[0]["transfer_score"] == 0.9
