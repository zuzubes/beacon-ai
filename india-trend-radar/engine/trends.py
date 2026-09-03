"""
Trend engine: produces the Macro / Mega / Sub-trend hierarchy for a given
(time_range, region, industry) query.

Two modes:
  - mock (default): deterministic, seeded sample data so the UI works with
    zero setup. Content is generic/curated and templated with the user's
    industry so it reads sensibly for any sector.
  - live: calls the OpenAI API with the user's own key.

Both modes return the same schema:
{
  "tier": "Macro" | "Mega" | "Sub",
  "id": str,
  "parent": str | None,   # name of the parent trend, for context
  "category": str,        # used to group trends in the momentum chart
  "name": str,
  "description": str,
  "strength": float,      # 0-10
  "growth_pct": float,    # can be negative
  "time_horizon": str,
  "recommendation": str,  # Invest | Strategize | Watch | Stay away
}
"""

from __future__ import annotations

import hashlib
import json
import random
import re
from time import perf_counter

from engine.cost_tracking import CostRunTracker

RECOMMENDATIONS = ["Invest", "Strategize", "Watch", "Stay away"]

_SLUG_REPLACEMENTS = {
    "broad-based": "broad based",
    "cross-border": "cross-border",
}

_FILLER_PHRASES = (
    "in today's world",
    "at its core",
    "going forward",
    "when it comes to",
    "the reality is",
    "the truth is",
    "it's worth noting",
    "it's important to note",
    "let's dive in",
    "cutting-edge",
    "game changer",
    "ever-evolving",
    "transformative",
    "robust",
    "meticulous",
    "intricate",
)


def _polish_text(text: str) -> str:
    value = (text or "").strip()
    if not value:
        return value

    for phrase in _FILLER_PHRASES:
        value = re.sub(re.escape(phrase), "", value, flags=re.IGNORECASE)

    for src, dst in _SLUG_REPLACEMENTS.items():
        value = re.sub(re.escape(src), dst, value, flags=re.IGNORECASE)

    value = re.sub(r"\b(delve|foster|leverage|utilize|facilitate|empower|streamline|harness)\b", "", value, flags=re.IGNORECASE)
    value = re.sub(r",\s*(highlighting|underscoring|reflecting|showcasing)\b[^.]*", "", value, flags=re.IGNORECASE)
    value = re.sub(r"\s{2,}", " ", value)
    value = re.sub(r"\s+,", ",", value)
    value = re.sub(r"\s+\.", ".", value)
    value = re.sub(r"\(\s+", "(", value)
    value = re.sub(r"\s+\)", ")", value)
    value = value.strip(" ,;:-")
    if value and value[0].islower():
        value = value[0].upper() + value[1:]
    return value


def _polish_trend_item(item: dict) -> dict:
    cleaned = dict(item)
    for field in ("name", "description", "category", "parent"):
        if cleaned.get(field):
            cleaned[field] = _polish_text(str(cleaned[field]))
    return cleaned


def polish_trends_for_app(trends: list[dict]) -> list[dict]:
    return [_polish_trend_item(item) for item in trends]

# ---------------------------------------------------------------------------
# Curated content bank (mock mode). {industry} is substituted at runtime.
# ---------------------------------------------------------------------------

MACRO_BANK = [
    dict(
        id="m1",
        name="Energy Transition & Decarbonization",
        category="Energy & Climate",
        desc=(
            "A multi-decade global shift away from fossil fuels toward renewable, "
            "low-carbon, and circular energy systems is reordering capital flows, "
            "industrial policy, and trade routes across the US and China, with direct "
            "spillover into {industry} supply chains that India is positioned to capture."
        ),
        mega=[
            dict(
                name="Grid-Scale Storage & Reliability Gap",
                desc=(
                    "Renewable penetration is outpacing grid balancing capacity, creating "
                    "urgent demand for storage, flexibility, and demand-response solutions "
                    "adjacent to {industry}."
                ),
                sub=[
                    dict(
                        name="Behind-the-Meter Battery Systems",
                        desc="Commercial and industrial sites are installing on-site storage to hedge against grid instability and time-of-use pricing, a near-term hardware and financing opportunity in {industry}.",
                    ),
                    dict(
                        name="Virtual Power Plant Aggregation",
                        desc="Software that pools distributed storage and flexible load into a tradeable grid resource is scaling fastest in the US and China, with India's grid operators beginning to pilot similar models relevant to {industry}.",
                    ),
                ],
            ),
            dict(
                name="Green Industrial Feedstock Shift",
                desc=(
                    "Heavy industry (steel, chemicals, shipping) is under pressure to "
                    "decarbonize feedstocks, opening a multi-billion-dollar retrofit and "
                    "green-input opportunity for {industry} suppliers."
                ),
                sub=[
                    dict(
                        name="Green Hydrogen for Industrial Heat",
                        desc="Electrolysis-based hydrogen is being piloted to replace natural gas in high-heat industrial processes, with India's low-cost renewable power giving {industry} players a structural cost edge.",
                    ),
                    dict(
                        name="Recycled & Bio-Based Materials Sourcing",
                        desc="Regulatory pressure in the US and China is pushing manufacturers to qualify recycled or bio-based inputs, creating a sourcing opportunity for India-based {industry} suppliers.",
                    ),
                ],
            ),
        ],
    ),
    dict(
        id="m2",
        name="AI-Driven Industrial Transformation",
        category="Technology & AI",
        desc=(
            "Foundation models, agentic software, and autonomous systems are being "
            "embedded into core enterprise and industrial workflows in the US and "
            "China, compressing R&D cycles and redefining competitive moats in "
            "{industry}."
        ),
        mega=[
            dict(
                name="Enterprise Agentic Workflow Adoption",
                desc=(
                    "Businesses want AI systems that execute multi-step work, not just "
                    "chat, creating tension between legacy software vendors and a new "
                    "generation of agentic {industry} tooling."
                ),
                sub=[
                    dict(
                        name="Vertical AI Copilots for SMBs",
                        desc="Narrow, workflow-specific copilots are outperforming general assistants for small and mid-size {industry} operators, a segment India's SaaS builders can serve at lower cost than US incumbents.",
                    ),
                    dict(
                        name="Agentic Back-Office Automation",
                        desc="Finance, compliance, and operations teams are automating multi-step processes end-to-end, reducing headcount growth needs in {industry} back offices across both US and China corporates.",
                    ),
                ],
            ),
            dict(
                name="Compute Scarcity & Edge Inference",
                desc=(
                    "Accelerator scarcity and data-sovereignty rules are pushing "
                    "{industry} workloads toward edge and regionally hosted inference "
                    "rather than centralized US or China clouds."
                ),
                sub=[
                    dict(
                        name="On-Device / Edge Model Optimization",
                        desc="Model compression and edge-inference toolchains are letting {industry} products run AI features without dependence on scarce, expensive US/China cloud compute.",
                    ),
                    dict(
                        name="India-Hosted Inference Infrastructure",
                        desc="Data-residency rules and cost pressure are creating early demand for India-based inference capacity serving {industry} companies that cannot rely solely on US or Chinese hyperscalers.",
                    ),
                ],
            ),
        ],
    ),
    dict(
        id="m3",
        name="Geopolitical Fragmentation & Supply Chain Reshoring",
        category="Geopolitics & Trade",
        desc=(
            "Escalating US-China strategic competition is pushing governments and "
            "corporates to diversify manufacturing, sourcing, and data infrastructure "
            "away from single-country dependence, a structural tailwind for "
            "India-based {industry} capacity."
        ),
        mega=[
            dict(
                name="China+1 Manufacturing Diversification",
                desc=(
                    "Global brands are actively qualifying non-China manufacturing "
                    "partners; India's {industry} base is a leading beneficiary but "
                    "faces execution and quality-consistency scrutiny."
                ),
                sub=[
                    dict(
                        name="Contract Manufacturing Capacity Build-Out",
                        desc="India-based contract manufacturers in {industry} are raising capital to add capacity qualified against US and China buyer standards, shortening the diversification timeline.",
                    ),
                    dict(
                        name="Quality & Traceability Tooling for Exporters",
                        desc="Software that gives US and China buyers real-time quality and provenance data is becoming a prerequisite for India-based {industry} exporters to win contracts.",
                    ),
                ],
            ),
            dict(
                name="Critical Minerals & Component Sovereignty",
                desc=(
                    "Export controls and tariff volatility between the US and China are "
                    "forcing {industry} companies to secure alternative sourcing for "
                    "critical inputs, favoring India-based processing and assembly."
                ),
                sub=[
                    dict(
                        name="Critical Minerals Processing & Refining",
                        desc="India is courting investment into midstream processing of critical minerals to reduce {industry} companies' reliance on Chinese refining capacity.",
                    ),
                    dict(
                        name="Component-Level Localization",
                        desc="{industry} companies are localizing sub-assembly and component production in India to hedge against US-China trade restrictions on finished goods.",
                    ),
                ],
            ),
        ],
    ),
    dict(
        id="m4",
        name="Climate Adaptation & Physical Risk Economy",
        category="Energy & Climate",
        desc=(
            "Rising physical climate risk is forcing infrastructure, insurance, "
            "agriculture, and logistics players in both the US and China to invest "
            "defensively, creating a durable, multi-decade capex cycle that touches "
            "{industry}."
        ),
        mega=[
            dict(
                name="Parametric & Climate-Linked Insurance Demand",
                desc=(
                    "Traditional insurers are pulling back from high-risk geographies, "
                    "creating unmet demand for parametric and data-driven risk products "
                    "relevant to {industry}."
                ),
                sub=[
                    dict(
                        name="Satellite & IoT-Based Risk Underwriting",
                        desc="Real-time sensor and satellite data is enabling faster, cheaper climate-risk underwriting for {industry} assets in markets US and China insurers are exiting.",
                    ),
                    dict(
                        name="Parametric Insurance-as-a-Service",
                        desc="Embedded, trigger-based insurance products are being bundled into {industry} platforms serving climate-exposed customers in the US, China, and India.",
                    ),
                ],
            ),
            dict(
                name="Resilient Infrastructure Retrofit Wave",
                desc=(
                    "Aging infrastructure in the US and expanding infrastructure in "
                    "China both require climate-hardening, a design and materials "
                    "opportunity for {industry} players entering via India-based "
                    "manufacturing."
                ),
                sub=[
                    dict(
                        name="Climate-Resilient Building Materials",
                        desc="Heat- and flood-resistant materials developed for the US and Chinese retrofit markets are finding a manufacturing base in India's {industry} sector.",
                    ),
                    dict(
                        name="Infrastructure Monitoring & Predictive Maintenance",
                        desc="Sensor-driven monitoring of aging infrastructure is scaling in the US and China, with India-built {industry} platforms competing on cost.",
                    ),
                ],
            ),
        ],
    ),
    dict(
        id="m5",
        name="Demographic & Labor Market Realignment",
        category="Demographics & Capital",
        desc=(
            "Aging populations and slowing workforce growth in the US and China are "
            "colliding with India's younger demographic base, altering global labor "
            "cost structures and consumption patterns relevant to {industry}."
        ),
        mega=[
            dict(
                name="Skilled Talent Arbitrage",
                desc=(
                    "US and Chinese firms face rising domestic talent costs and "
                    "shortages, increasing outsourcing and hiring of India-based "
                    "{industry} talent and remote teams."
                ),
                sub=[
                    dict(
                        name="Global Capability Centers 2.0",
                        desc="US and China-headquartered {industry} companies are expanding higher-value (not just cost-arbitrage) engineering and product functions into India-based capability centers.",
                    ),
                    dict(
                        name="Cross-Border Contractor Platforms",
                        desc="Platforms that handle compliant cross-border hiring are making it easier for US and China {industry} firms to tap India-based specialist talent directly.",
                    ),
                ],
            ),
            dict(
                name="Aging-Population Service Demand",
                desc=(
                    "Healthcare, eldercare, and automation demand is rising sharply in "
                    "the US and China as populations age, creating export opportunities "
                    "for India-built {industry} solutions."
                ),
                sub=[
                    dict(
                        name="Remote & Home-Based Care Tech",
                        desc="India-built {industry} products for remote patient monitoring and home care are finding early export demand from aging-population markets in the US and China.",
                    ),
                    dict(
                        name="Care-Sector Labor Automation",
                        desc="Automation tools that offset caregiver shortages are gaining traction in {industry}, with India positioned as a low-cost development and BPO base.",
                    ),
                ],
            ),
        ],
    ),
    dict(
        id="m6",
        name="Digital Sovereignty & Data Localization",
        category="Technology & AI",
        desc=(
            "Nations are asserting control over data, compute, and critical digital "
            "infrastructure, driving regional platform build-outs and compliance "
            "requirements that shape how {industry} companies architect for the US, "
            "China, and India."
        ),
        mega=[
            dict(
                name="Sovereign Cloud & Compute Build-Out",
                desc=(
                    "Governments are mandating in-country data residency, pushing "
                    "{industry} vendors to localize infrastructure across the US, "
                    "China, and India rather than relying on a single global stack."
                ),
                sub=[
                    dict(
                        name="India Data-Residency Compliance Tooling",
                        desc="{industry} companies serving Indian customers need compliance tooling to meet data-localization rules while still integrating with US/China-built platforms.",
                    ),
                    dict(
                        name="Regional Sovereign Cloud Providers",
                        desc="Non-hyperscaler cloud providers focused on data sovereignty are winning {industry} workloads that US and Chinese hyperscalers cannot serve compliantly.",
                    ),
                ],
            ),
            dict(
                name="Platform De-Risking from Single-Vendor Lock-in",
                desc=(
                    "Enterprises are diversifying away from single-cloud and "
                    "single-model dependency, creating demand for interoperable, "
                    "India-friendly {industry} infrastructure."
                ),
                sub=[
                    dict(
                        name="Multi-Model Orchestration Layers",
                        desc="Tooling that lets {industry} companies swap between US and Chinese foundation models without rearchitecting is becoming a procurement requirement.",
                    ),
                    dict(
                        name="Open-Standard Interop Middleware",
                        desc="Middleware built to open standards is reducing {industry} buyers' exposure to a single US or China vendor's roadmap and pricing.",
                    ),
                ],
            ),
        ],
    ),
    dict(
        id="m7",
        name="Capital Cost Normalization",
        category="Demographics & Capital",
        desc=(
            "A structurally higher interest-rate regime versus the 2010s is "
            "repricing growth capital in the US and China, rewarding "
            "capital-efficient, cash-generative {industry} business models over "
            "growth-at-all-costs."
        ),
        mega=[
            dict(
                name="Profitability-First Growth Mandate",
                desc=(
                    "LPs and public markets are rewarding {industry} companies that "
                    "show a path to profitability over pure top-line growth, changing "
                    "how US and China investors underwrite deals."
                ),
                sub=[
                    dict(
                        name="Efficient-Growth SaaS Metrics",
                        desc="India-based {industry} SaaS companies benchmarking to Rule-of-40 style efficiency metrics are attracting more US/China cross-border capital than growth-only peers.",
                    ),
                    dict(
                        name="Bootstrapped-to-Scale Playbooks",
                        desc="A cohort of {industry} founders is scaling with minimal dilution before raising, a pattern increasingly rewarded by both India-domestic and international investors.",
                    ),
                ],
            ),
            dict(
                name="Private Credit Substituting for Equity",
                desc=(
                    "As equity capital gets pricier, private credit and structured "
                    "finance are filling funding gaps for growth-stage {industry} "
                    "companies in the US and China, a model India's market is starting "
                    "to import."
                ),
                sub=[
                    dict(
                        name="Venture Debt for Asset-Light Scale-Ups",
                        desc="Venture debt providers are extending non-dilutive capital to India-based {industry} companies following US/China playbooks, reducing early equity dilution.",
                    ),
                    dict(
                        name="Revenue-Based Financing",
                        desc="Revenue-based financing structures popularized in the US are reaching India's {industry} scale-ups as an alternative to priced equity rounds.",
                    ),
                ],
            ),
        ],
    ),
]


def _seed_from(*parts: str) -> random.Random:
    key = "|".join(parts)
    h = hashlib.sha256(key.encode("utf-8")).hexdigest()
    return random.Random(int(h[:16], 16))


def _pick_recommendation(strength: float, growth_pct: float, rng: random.Random) -> str:
    score = strength * 0.65 + (max(min(growth_pct, 150.0), -50.0) / 150.0) * 10 * 0.35
    score += rng.uniform(-0.4, 0.4)
    if score >= 7.3:
        return "Invest"
    if score >= 5.3:
        return "Strategize"
    if score >= 3.2:
        return "Watch"
    return "Stay away"


def _tier_ranges(tier: str) -> dict:
    if tier == "Macro":
        return dict(strength=(5.0, 8.5), growth=(20, 140), horizons=["5-10y", "10y+"])
    if tier == "Mega":
        return dict(strength=(3.5, 7.8), growth=(15, 190), horizons=["3-7y", "2-5y"])
    return dict(strength=(2.0, 9.2), growth=(-15, 260), horizons=["<1y", "1-2y", "2-5y"])


def _score_trend(name: str, tier: str, seed_key: str) -> dict:
    rng = _seed_from(seed_key, name, tier)
    ranges = _tier_ranges(tier)
    strength = round(rng.uniform(*ranges["strength"]), 1)
    growth = round(rng.uniform(*ranges["growth"]), 0)
    horizon = rng.choice(ranges["horizons"])
    recommendation = _pick_recommendation(strength, growth, rng)
    return dict(strength=strength, growth_pct=growth, time_horizon=horizon, recommendation=recommendation)


def generate_mock_trends(time_range: str, region: str, industry: str, max_macro: int = 5) -> list[dict]:
    """Deterministic, seeded sample trend hierarchy. Same inputs -> same output."""
    industry_label = industry.strip() or "the sector"
    seed_key = f"{time_range}|{region}|{industry_label}"
    rng = _seed_from(seed_key, "macro-select")

    macro_pool = list(MACRO_BANK)
    rng.shuffle(macro_pool)
    chosen = macro_pool[: max(3, min(max_macro, len(macro_pool)))]

    results: list[dict] = []
    for macro in chosen:
        macro_name = macro["name"]
        macro_desc = macro["desc"].format(industry=industry_label)
        scores = _score_trend(macro_name, "Macro", seed_key)
        results.append(
            dict(
                tier="Macro",
                id=macro["id"],
                parent=None,
                category=macro["category"],
                name=macro_name,
                description=macro_desc,
                **scores,
            )
        )
        for mi, mega in enumerate(macro["mega"]):
            mega_name = mega["name"]
            mega_desc = mega["desc"].format(industry=industry_label)
            mega_id = f"{macro['id']}-mega{mi}"
            scores = _score_trend(mega_name, "Mega", seed_key)
            results.append(
                dict(
                    tier="Mega",
                    id=mega_id,
                    parent=macro_name,
                    category=macro["category"],
                    name=mega_name,
                    description=mega_desc,
                    **scores,
                )
            )
            for si, sub in enumerate(mega["sub"]):
                sub_name = sub["name"]
                sub_desc = sub["desc"].format(industry=industry_label)
                scores = _score_trend(sub_name, "Sub", seed_key)
                results.append(
                    dict(
                        tier="Sub",
                        id=f"{mega_id}-sub{si}",
                        parent=mega_name,
                        category=macro["category"],
                        name=sub_name,
                        description=sub_desc,
                        **scores,
                    )
                )
    return polish_trends_for_app(results)


# ---------------------------------------------------------------------------
# Live mode (OpenAI API)
# ---------------------------------------------------------------------------

LIVE_PROMPT_TEMPLATE = """You are a research analyst for an India-focused micro-VC fund partner. \
The partner tracks trends emerging in the US and China to find investable signal for India.

Query context:
- Time range: {time_range}
- Region focus: {region}
- Industry / Sector: {industry}

Research context:
{research_context}

Produce a trend hierarchy with exactly three tiers, using this working definition for each tier:

Macro-Trends: long-term, macro changes that play out across many years or decades with large-scale \
impact, summarizing major forces across society, technology, economy, ecology, and politics.

Mega-Trends: the building blocks of the arena — points of tension that macro-trends create when they \
intersect with consumers' or businesses' basic needs.

Sub-Trends: emerging, actionable trends arising from that tension, highlighting how an investor could \
act on emerging expectations today, with explicit relevance to India as an investment destination \
given developments in the US and China.

Return 4-6 Macro-Trends. Each Macro-Trend has 2 Mega-Trends. Each Mega-Trend has 2 Sub-Trends.

Respond with ONLY valid JSON (no markdown fences, no commentary), an array of objects, each with this \
exact shape:
{{
  "tier": "Macro" | "Mega" | "Sub",
  "parent": string or null (the exact name of the parent trend, null for Macro tier),
  "category": string (a short cluster label shared by a Macro-Trend and its children, e.g. "Energy & Climate"),
  "name": string (trend name, concise),
  "description": string (2-3 sentences, specific and non-generic),
  "strength": number from 0 to 10 (current momentum/strength of the trend),
  "growth_pct": number (year-over-year mention/interest growth, can be negative),
  "time_horizon": string (e.g. "<1y", "1-2y", "2-5y", "5-10y", "10y+"),
  "recommendation": "Invest" | "Strategize" | "Watch" | "Stay away"
}}
"""


def extract_response_text(response) -> str:
    """Pulls the plain text out of an OpenAI Responses API result, working around
    output_text sometimes being empty even though `output` has the content."""
    text = getattr(response, "output_text", "")
    if not text:
        chunks = []
        for item in getattr(response, "output", []) or []:
            for content in getattr(item, "content", []) or []:
                if getattr(content, "type", "") == "output_text":
                    chunks.append(getattr(content, "text", ""))
        text = "".join(chunks)
    return text.strip()


def parse_live_trends_json(text: str) -> list[dict]:
    """Parses+normalizes a trend-hierarchy JSON array from the model's raw text into this
    module's schema. Shared by call_live_trends and the combined trends+report call."""
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"could not parse the model's JSON response ({exc})") from exc
    if not isinstance(data, list):
        raise ValueError("Expected a JSON array of trend objects")

    normalized = []
    for i, item in enumerate(data):
        normalized.append(
            dict(
                tier=item.get("tier", "Sub"),
                id=f"live-{i}",
                parent=item.get("parent"),
                category=item.get("category", "General"),
                name=item.get("name", "Untitled trend"),
                description=item.get("description", ""),
                strength=float(item.get("strength", 5.0)),
                growth_pct=float(item.get("growth_pct", 0.0)),
                time_horizon=item.get("time_horizon", "1-2y"),
                recommendation=item.get("recommendation", "Watch"),
            )
        )
    return normalized


def call_live_trends(
    time_range: str,
    region: str,
    industry: str,
    api_key: str,
    research_context: str | None = None,
    cost_tracker: CostRunTracker | None = None,
) -> list[dict]:
    """Calls the OpenAI API to generate the trend hierarchy. Raises on failure."""
    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    prompt = LIVE_PROMPT_TEMPLATE.format(
        time_range=time_range,
        region=region,
        industry=industry or "General",
        research_context=research_context or "- Not available",
    )
    started = perf_counter()
    # Up to 6 Macro-Trends x 7 items (1 macro + 2 mega + 4 sub) = 42 JSON objects; 4000 tokens was
    # cutting the response off mid-string on anything but the most terse output. 12000 leaves
    # comfortable headroom (~280 tokens/object) without being unreasonably large for gpt-4.1-mini.
    try:
        response = client.responses.create(
            model="gpt-4.1-mini",
            input=prompt,
            max_output_tokens=12000,
        )
    except Exception as exc:  # noqa: BLE001
        elapsed_ms = int((perf_counter() - started) * 1000)
        if cost_tracker:
            cost_tracker.add_entry(
                feature="trend generation",
                provider="openai",
                model="gpt-4.1-mini",
                endpoint="responses.create",
                status="error",
                latency_ms=elapsed_ms,
                error=f"{type(exc).__name__}: {exc}",
            )
        raise
    elapsed_ms = int((perf_counter() - started) * 1000)
    if getattr(response, "status", None) == "incomplete":
        reason = getattr(getattr(response, "incomplete_details", None), "reason", "unknown")
        if cost_tracker:
            cost_tracker.add_entry(
                feature="trend generation",
                provider="openai",
                model="gpt-4.1-mini",
                endpoint="responses.create",
                status="error",
                response=response,
                latency_ms=elapsed_ms,
                error=f"truncated: {reason}",
            )
        raise RuntimeError(f"response truncated by the API before it finished ({reason})")
    text = extract_response_text(response)
    try:
        result = parse_live_trends_json(text)
    except Exception as exc:
        if cost_tracker:
            cost_tracker.add_entry(
                feature="trend generation",
                provider="openai",
                model="gpt-4.1-mini",
                endpoint="responses.create",
                status="error",
                response=response,
                latency_ms=elapsed_ms,
                error=f"{type(exc).__name__}: {exc}",
            )
        raise

    if cost_tracker:
        cost_tracker.add_entry(
            feature="trend generation",
            provider="openai",
            model="gpt-4.1-mini",
            endpoint="responses.create",
            status="success",
            response=response,
            latency_ms=elapsed_ms,
        )
    return result
