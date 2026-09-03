"""Run-level cost tracking for Beacon AI analysis requests."""

from __future__ import annotations

import csv
import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_DIR = ROOT_DIR / "raw" / "cost_tracking"

# Internal estimate basis. Keep this easy to audit and update.
OPENAI_PRICING_USD_PER_1M = {
    "gpt-4.1-mini": {
        "input": 0.40,
        "cached_input": 0.10,
        "output": 1.60,
    }
}


def _slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_") or "run"


def _safe_int(value: Any) -> int:
    try:
        return int(float(value or 0))
    except Exception:  # noqa: BLE001
        return 0


def _safe_float(value: Any) -> float:
    try:
        return float(value or 0.0)
    except Exception:  # noqa: BLE001
        return 0.0


def _extract_attr(obj: Any, *path: str) -> Any:
    current = obj
    for name in path:
        if current is None:
            return None
        current = getattr(current, name, None)
    return current


def _extract_usage(response: Any) -> dict[str, int]:
    usage = getattr(response, "usage", None)
    input_tokens = _safe_int(getattr(usage, "input_tokens", 0))
    output_tokens = _safe_int(getattr(usage, "output_tokens", 0))
    cached_tokens = _safe_int(_extract_attr(usage, "input_tokens_details", "cached_tokens"))
    reasoning_tokens = _safe_int(_extract_attr(usage, "output_tokens_details", "reasoning_tokens"))
    return {
        "input_tokens": input_tokens,
        "cached_tokens": cached_tokens,
        "output_tokens": output_tokens,
        "reasoning_tokens": reasoning_tokens,
    }


def estimate_cost_usd(model: str, input_tokens: int, output_tokens: int, cached_tokens: int = 0) -> float:
    pricing = OPENAI_PRICING_USD_PER_1M.get(model)
    if not pricing:
        return 0.0
    billable_input = max(input_tokens - cached_tokens, 0)
    return (
        billable_input * pricing["input"]
        + cached_tokens * pricing["cached_input"]
        + output_tokens * pricing["output"]
    ) / 1_000_000


@dataclass
class CostLogEntry:
    request_id: str
    timestamp: str
    company: str
    run_id: str
    provider: str
    model: str
    feature: str
    endpoint: str
    status: str
    input_tokens: int = 0
    cached_tokens: int = 0
    output_tokens: int = 0
    reasoning_tokens: int = 0
    retries: int = 0
    tool_calls: int = 0
    latency_ms: int = 0
    estimated_cost_usd: float = 0.0
    error: str | None = None
    notes: str | None = None


@dataclass
class CostRunTracker:
    company: str
    timestamp: str
    region: str
    industry: str
    time_range: str
    run_type: str = "analysis"
    base_dir: Path = DEFAULT_OUTPUT_DIR
    run_id: str = field(init=False)
    run_dir: Path = field(init=False)
    json_path: Path = field(init=False)
    csv_path: Path = field(init=False)
    entries: list[CostLogEntry] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.company = (self.company or "Unknown").strip() or "Unknown"
        self.timestamp = (self.timestamp or datetime.now().strftime("%Y%m%d_%H%M%S")).strip()
        self.region = (self.region or "").strip()
        self.industry = (self.industry or "").strip()
        self.time_range = (self.time_range or "").strip()
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.run_id = f"{_slugify(self.company)}_{self.timestamp}"
        self.run_dir = self.base_dir / self.run_id
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.json_path = self.run_dir / "cost_log.json"
        self.csv_path = self.run_dir / "cost_log.csv"
        self.flush()

    @property
    def output_paths(self) -> dict[str, str]:
        return {
            "json": str(self.json_path.relative_to(ROOT_DIR)) if self.json_path.is_relative_to(ROOT_DIR) else str(self.json_path),
            "csv": str(self.csv_path.relative_to(ROOT_DIR)) if self.csv_path.is_relative_to(ROOT_DIR) else str(self.csv_path),
        }

    def add_entry(
        self,
        *,
        feature: str,
        provider: str,
        model: str,
        endpoint: str,
        status: str,
        response: Any = None,
        latency_ms: int = 0,
        retries: int = 0,
        tool_calls: int = 0,
        error: str | None = None,
        notes: str | None = None,
        timestamp: str | None = None,
    ) -> CostLogEntry:
        usage = _extract_usage(response) if response is not None else {}
        input_tokens = _safe_int(usage.get("input_tokens"))
        cached_tokens = _safe_int(usage.get("cached_tokens"))
        output_tokens = _safe_int(usage.get("output_tokens"))
        reasoning_tokens = _safe_int(usage.get("reasoning_tokens"))
        estimated_cost = estimate_cost_usd(model, input_tokens, output_tokens, cached_tokens)
        entry = CostLogEntry(
            request_id=f"{self.run_id}:{len(self.entries) + 1:03d}",
            timestamp=timestamp or datetime.now().isoformat(timespec="seconds"),
            company=self.company,
            run_id=self.run_id,
            provider=provider,
            model=model,
            feature=feature,
            endpoint=endpoint,
            status=status,
            input_tokens=input_tokens,
            cached_tokens=cached_tokens,
            output_tokens=output_tokens,
            reasoning_tokens=reasoning_tokens,
            retries=retries,
            tool_calls=tool_calls,
            latency_ms=int(latency_ms),
            estimated_cost_usd=estimated_cost,
            error=error,
            notes=notes,
        )
        self.entries.append(entry)
        self.flush()
        return entry

    def flush(self) -> None:
        summary = {
            "company": self.company,
            "timestamp": self.timestamp,
            "run_id": self.run_id,
            "run_type": self.run_type,
            "region": self.region,
            "industry": self.industry,
            "time_range": self.time_range,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "paths": self.output_paths,
            "pricing_basis": {
                "currency": "USD",
                "openai_pricing_usd_per_1m": OPENAI_PRICING_USD_PER_1M,
            },
            "totals": self._totals(),
            "entries": [asdict(entry) for entry in self.entries],
        }
        self.json_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
        self._write_csv()

    def _totals(self) -> dict[str, Any]:
        return {
            "requests": len(self.entries),
            "input_tokens": sum(entry.input_tokens for entry in self.entries),
            "cached_tokens": sum(entry.cached_tokens for entry in self.entries),
            "output_tokens": sum(entry.output_tokens for entry in self.entries),
            "reasoning_tokens": sum(entry.reasoning_tokens for entry in self.entries),
            "estimated_cost_usd": round(sum(entry.estimated_cost_usd for entry in self.entries), 6),
            "tool_calls": sum(entry.tool_calls for entry in self.entries),
            "retries": sum(entry.retries for entry in self.entries),
        }

    def _write_csv(self) -> None:
        fieldnames = [
            "request_id",
            "timestamp",
            "company",
            "run_id",
            "provider",
            "model",
            "feature",
            "endpoint",
            "status",
            "input_tokens",
            "cached_tokens",
            "output_tokens",
            "reasoning_tokens",
            "retries",
            "tool_calls",
            "latency_ms",
            "estimated_cost_usd",
            "error",
            "notes",
        ]
        with self.csv_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for entry in self.entries:
                writer.writerow(asdict(entry))
