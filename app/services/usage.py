"""Lightweight per-key LLM token-usage tracking.

Records one entry per LLM call to ``storage/usage.json`` and exposes simple
aggregates for the dashboard. Deliberately best-effort: recording must never
raise into the generation path, so every write is wrapped in try/except.

# ponytail: flat JSON file + global lock. Fine for a single-node local app;
# swap for SQLite if this ever runs multi-process at volume.
"""

import json
import os
import threading
from datetime import datetime, timezone

from loguru import logger

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
_USAGE_FILE = os.path.join(_ROOT, "storage", "usage.json")
_LOCK = threading.Lock()
_MAX_RECORDS = 5000


def _mask_key(api_key: str) -> str:
    api_key = (api_key or "").strip()
    if not api_key:
        return "env/no-key"
    return f"…{api_key[-4:]}" if len(api_key) >= 4 else "…"


def _load() -> list:
    try:
        with open(_USAGE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return []


def record(provider: str, model: str, api_key: str,
           input_tokens: int, output_tokens: int) -> None:
    """Append one usage record. Never raises."""
    try:
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "provider": provider or "",
            "model": model or "",
            "key": _mask_key(api_key),
            "input_tokens": int(input_tokens or 0),
            "output_tokens": int(output_tokens or 0),
        }
        with _LOCK:
            os.makedirs(os.path.dirname(_USAGE_FILE), exist_ok=True)
            data = _load()
            data.append(entry)
            if len(data) > _MAX_RECORDS:
                data = data[-_MAX_RECORDS:]
            with open(_USAGE_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
    except Exception as e:  # pragma: no cover - tracking must not break generation
        logger.warning(f"usage.record failed (ignored): {e}")


def summary_by_key() -> list:
    """Usage aggregated by (provider, masked key, model), sorted by total tokens desc."""
    agg: dict = {}
    for r in _load():
        k = (r.get("provider", ""), r.get("key", ""), r.get("model", ""))
        a = agg.setdefault(k, {
            "provider": k[0], "key": k[1], "model": k[2],
            "calls": 0, "input_tokens": 0, "output_tokens": 0,
        })
        a["calls"] += 1
        a["input_tokens"] += int(r.get("input_tokens", 0) or 0)
        a["output_tokens"] += int(r.get("output_tokens", 0) or 0)
    rows = list(agg.values())
    for a in rows:
        a["total_tokens"] = a["input_tokens"] + a["output_tokens"]
    rows.sort(key=lambda x: x["total_tokens"], reverse=True)
    return rows


def totals() -> dict:
    data = _load()
    inp = sum(int(r.get("input_tokens", 0) or 0) for r in data)
    out = sum(int(r.get("output_tokens", 0) or 0) for r in data)
    return {"calls": len(data), "input_tokens": inp,
            "output_tokens": out, "total_tokens": inp + out}


if __name__ == "__main__":
    # Self-check: record two calls and verify aggregation.
    before = totals()["calls"]
    record("demo", "m1", "abcd1234", 10, 5)
    record("demo", "m1", "abcd1234", 20, 7)
    t = totals()
    s = summary_by_key()
    assert t["calls"] >= before + 2, t
    row = next(r for r in s if r["provider"] == "demo" and r["key"] == "…1234")
    assert row["input_tokens"] >= 30 and row["output_tokens"] >= 12, row
    print("usage self-check OK:", row)
