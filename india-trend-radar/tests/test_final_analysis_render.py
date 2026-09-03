"""Tests for engine/final_analysis_render.py."""

from engine.final_analysis_render import render_final_analysis_html


def test_render_final_analysis_html_includes_branding_and_sections():
    report_markdown = """\
# Trend Analysis: Apparel in US

**Date**: 2026-09-02 12:00

**Industry**: Apparel

**Geographic scope**: US

**Time range**: Past 1 week

## Executive Summary
Short summary.
"""
    combined_markdown = report_markdown + "\n\n## Sources\n- [Example](https://example.com)"
    html = render_final_analysis_html(
        report_markdown,
        combined_markdown,
        trend_data=[{"name": "Trend A", "strength": 8.2, "description": "Up", "tier": "Sub"}],
        research_context=None,
        generated_at="2026-09-02 12:00",
        region="US",
        industry="Apparel",
    )

    assert "Beacon AI analysis" in html
    assert "Beacon AI final analysis" not in html
    assert "Trend Analysis: Apparel in US" in html
    assert "Trend A" in html
    assert "example.com" in html
    assert "Local reports" not in html
    assert "Top signal" not in html


def test_render_final_analysis_html_strips_script_tags():
    report_markdown = """\
# Trend Analysis: Apparel in US

**Date**: 2026-09-02 12:00

**Industry**: Apparel

**Geographic scope**: US

**Time range**: Past 1 week

## Executive Summary
<script>alert('xss')</script>Safe text.
"""
    html = render_final_analysis_html(
        report_markdown,
        report_markdown,
        trend_data=[],
        research_context=None,
        generated_at="2026-09-02 12:00",
        region="US",
        industry="Apparel",
    )

    assert "<script>" not in html
    assert "Safe text." in html
