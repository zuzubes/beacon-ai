"""
Momentum diagram: a radial (polar) chart that recreates the look of the
reference screenshot — trends scattered as dots at a radius proportional to
their strength, grouped into colored category arcs around the rim.

Color and typography follow Beacon AI's own design tokens (indigo accent,
slate ink/muted grays, Source Sans 3 — see .streamlit/config.toml and
app.py's injected CSS) rather than default Plotly styling, with an editorial
restraint on color: one accent, muted grays for everything else, and a
tasteful categorical set only where a chart genuinely needs to distinguish
several categories at once.
"""

from __future__ import annotations

import plotly.graph_objects as go

# ---------------------------------------------------------------------------
# Design tokens (mirrors app.py's --sds-* custom properties / config.toml)
# ---------------------------------------------------------------------------

INK = "#0F172A"
MUTED = "#475569"
SOFT = "#94A3B8"
RULE = "#E2E8F0"
RULE_SOFT = "#EEF2F6"
ACCENT = "#4F46E5"
FONT_FAMILY = "'Source Sans 3', 'Source Sans Pro', sans-serif"

TITLE_FONT = dict(family=FONT_FAMILY, color=INK, size=18)
BODY_FONT = dict(family=FONT_FAMILY, color=MUTED, size=11)
LEGEND = dict(
    orientation="h",
    yanchor="top",
    y=-0.16,
    xanchor="center",
    x=0.5,
    font=dict(family=FONT_FAMILY, color=MUTED, size=11),
)

# A restrained categorical palette: the brand accent first, then muted/desaturated
# complements -- never a clashing rainbow. Used only where a chart genuinely needs to
# tell several categories apart at once (the rim arcs below).
CATEGORY_COLORS = [
    ACCENT,     # indigo -- brand accent
    "#0EA5E9",  # sky
    "#0F766E",  # teal (dark, desaturated)
    "#B45309",  # amber (dark, desaturated)
    "#64748B",  # slate
    "#7C3AED",  # violet -- last resort
]

TIER_SIZE = {"Macro": 16, "Mega": 11, "Sub": 7}
TIER_OPACITY = {"Macro": 1.0, "Mega": 0.85, "Sub": 0.7}
# One focal tier (accent) plus two muted tiers, per the "accent on 1-2 elements" rule --
# tier is already distinguished by dot size in the momentum diagram, so color here only
# needs to carry it for the adoption S-curve's three lines.
TIER_COLORS = {"Macro": ACCENT, "Mega": MUTED, "Sub": SOFT}

# Recommendation labels map onto the app's own semantic status colors (success/info/
# warning/muted) rather than an unrelated ad-hoc palette.
RECOMMENDATION_COLORS = {
    "Invest": "#158237",
    "Strategize": ACCENT,
    "Watch": "#926C05",
    "Stay away": SOFT,
}


def _category_averages(trends: list[dict]) -> dict[str, float]:
    totals: dict[str, list[float]] = {}
    for item in trends:
        category = item.get("category", "General")
        totals.setdefault(category, []).append(float(item.get("strength", 0.0)))
    return {
        category: round(sum(values) / len(values), 2)
        for category, values in totals.items()
        if values
    }


def build_trend_radar_figure(trends: list[dict]) -> go.Figure:
    if not trends:
        fig = go.Figure()
        fig.update_layout(title="No trends to display yet — run an analysis first.")
        return fig

    averages = _category_averages(trends)
    categories = sorted(averages.keys())
    values = [averages[c] for c in categories]
    if categories:
        categories = categories + [categories[0]]
        values = values + [values[0]]

    fig = go.Figure(
        data=[
            go.Scatterpolar(
                theta=categories,
                r=values,
                fill="toself",
                fillcolor="rgba(79, 70, 229, 0.12)",
                line=dict(color=ACCENT, width=2.5),
                marker=dict(color=ACCENT, size=6),
                hoverinfo="text",
                text=[f"{c}: {v:.1f}" for c, v in zip(categories, values)],
                showlegend=False,
            )
        ]
    )
    fig.update_layout(
        title=dict(text="Trend Radar", font=TITLE_FONT, x=0, xanchor="left"),
        font=BODY_FONT,
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 10],
                gridcolor=RULE,
                linecolor=RULE,
                tickfont=dict(family=FONT_FAMILY, color=SOFT, size=9),
            ),
            angularaxis=dict(
                gridcolor=RULE_SOFT,
                linecolor=RULE_SOFT,
                tickfont=dict(family=FONT_FAMILY, color=MUTED, size=11),
            ),
            bgcolor="rgba(0,0,0,0)",
        ),
        margin=dict(l=100, r=100, t=60, b=40),
        height=560,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def build_adoption_s_curve_figure(trends: list[dict]) -> go.Figure:
    if not trends:
        fig = go.Figure()
        fig.update_layout(title="No trends to display yet — run an analysis first.")
        return fig

    tiers = ["Macro", "Mega", "Sub"]
    stages = ["Early", "Growing", "Mainstream", "Mature", "Declining"]
    stage_multipliers = [0.28, 0.45, 0.67, 0.84, 0.76]
    tier_series = {}
    for tier in tiers:
        tier_trends = [float(item.get("strength", 0.0)) for item in trends if item.get("tier") == tier]
        avg_strength = sum(tier_trends) / len(tier_trends) if tier_trends else 0.0
        tier_series[tier] = [min(100.0, round(avg_strength * factor * 10, 1)) for factor in stage_multipliers]

    fig = go.Figure()
    for tier in tiers:
        is_focal = tier == "Macro"
        fig.add_trace(
            go.Scatter(
                x=stages,
                y=tier_series[tier],
                mode="lines+markers",
                name=tier,
                line=dict(color=TIER_COLORS[tier], width=3 if is_focal else 2),
                marker=dict(size=8 if is_focal else 6),
            )
        )

    fig.update_layout(
        title=dict(text="Adoption S-Curve", font=TITLE_FONT, x=0, xanchor="left"),
        font=BODY_FONT,
        yaxis=dict(
            title=dict(text="Adoption / momentum (%)", font=dict(family=FONT_FAMILY, color=MUTED, size=11)),
            range=[0, 100],
            gridcolor=RULE,
            linecolor=RULE,
            tickfont=dict(family=FONT_FAMILY, color=SOFT, size=10),
        ),
        xaxis=dict(
            title="",
            gridcolor=RULE_SOFT,
            linecolor=RULE,
            tickfont=dict(family=FONT_FAMILY, color=MUTED, size=11),
        ),
        margin=dict(l=20, r=20, t=60, b=80),
        height=560,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend=LEGEND,
    )
    return fig


def build_momentum_figure(trends: list[dict], color_by: str = "category") -> go.Figure:
    """Builds a Plotly polar scatter figure from the flat trend list.

    color_by: "category" (cluster arcs, closer to the reference image) or
    "recommendation" (colored by Invest/Strategize/Watch/Stay away).
    """
    if not trends:
        fig = go.Figure()
        fig.update_layout(
            title="No trends to display yet — run an analysis first.",
            polar=dict(radialaxis=dict(visible=False), angularaxis=dict(visible=False)),
        )
        return fig

    categories = sorted({t["category"] for t in trends})
    cat_color = {c: CATEGORY_COLORS[i % len(CATEGORY_COLORS)] for i, c in enumerate(categories)}

    # Assign each category an angular segment around the circle.
    n_cats = len(categories)
    segment_width = 360.0 / n_cats
    cat_range = {}
    for i, c in enumerate(categories):
        start = i * segment_width
        end = start + segment_width
        cat_range[c] = (start, end)

    # Place trends within their category's segment, spreading by tier so
    # points don't overlap, with a small deterministic jitter.
    by_cat: dict[str, list[dict]] = {c: [] for c in categories}
    for t in trends:
        by_cat[t["category"]].append(t)

    theta_all, r_all, color_all, size_all, opacity_all, text_all, line_color_all = [], [], [], [], [], [], []

    for c, items in by_cat.items():
        start, end = cat_range[c]
        pad = segment_width * 0.12
        usable_start, usable_end = start + pad, end - pad
        n = len(items)
        for i, t in enumerate(sorted(items, key=lambda x: x["name"])):
            frac = (i + 0.5) / n if n else 0.5
            theta = usable_start + frac * (usable_end - usable_start)
            r = max(0.15, min(10, t["strength"]))
            theta_all.append(theta)
            r_all.append(r)
            size_all.append(TIER_SIZE.get(t["tier"], 8))
            opacity_all.append(TIER_OPACITY.get(t["tier"], 0.8))
            if color_by == "recommendation":
                color_all.append(RECOMMENDATION_COLORS.get(t["recommendation"], SOFT))
            else:
                color_all.append(cat_color[c])
            line_color_all.append("#ffffff")
            text_all.append(
                f"<b>{t['name']}</b><br>{t['tier']} · {c}<br>"
                f"Strength {t['strength']:.1f} · {t['growth_pct']:+.0f}% · {t['time_horizon']}<br>"
                f"{t['recommendation']}"
            )

    fig = go.Figure()

    # Category rim arcs (drawn just outside the outer gridline) -- thin hairline
    # rather than a thick "wheel", so the categorical color reads as a label, not
    # decoration.
    for c in categories:
        start, end = cat_range[c]
        pad = segment_width * 0.06
        arc_theta = [start + pad + (end - start - 2 * pad) * i / 40 for i in range(41)]
        fig.add_trace(
            go.Scatterpolar(
                theta=arc_theta,
                r=[10.6] * len(arc_theta),
                mode="lines",
                line=dict(color=cat_color[c], width=4),
                hoverinfo="text",
                text=[c] * len(arc_theta),
                showlegend=False,
            )
        )

    # Trend points.
    fig.add_trace(
        go.Scatterpolar(
            theta=theta_all,
            r=r_all,
            mode="markers",
            marker=dict(
                size=size_all,
                color=color_all,
                opacity=opacity_all,
                line=dict(color=line_color_all, width=1),
            ),
            hoverinfo="text",
            text=text_all,
            showlegend=False,
        )
    )

    # Legend proxy traces (category or recommendation).
    legend_map = cat_color if color_by == "category" else RECOMMENDATION_COLORS
    for label, color in legend_map.items():
        fig.add_trace(
            go.Scatterpolar(
                theta=[None],
                r=[None],
                mode="markers",
                marker=dict(size=10, color=color),
                name=label,
                showlegend=True,
            )
        )

    fig.update_layout(
        font=BODY_FONT,
        polar=dict(
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(
                range=[0, 11],
                tickvals=[0, 2, 4, 6, 8, 10],
                angle=0,
                showline=False,
                gridcolor=RULE,
                tickfont=dict(family=FONT_FAMILY, size=9, color=SOFT),
            ),
            angularaxis=dict(
                showticklabels=False,
                showline=False,
                gridcolor=RULE_SOFT,
                rotation=90,
                direction="clockwise",
            ),
        ),
        showlegend=True,
        legend=LEGEND,
        margin=dict(l=20, r=20, t=30, b=80),
        height=560,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig
