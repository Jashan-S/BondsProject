#!/usr/bin/env python3
"""
Append today's market data to the yearly history files.

Runs right after fetch_data.py in the nightly workflow. Reads the fresh
data/market.json and appends one entry per country to:

    data/history/us-curve-<YEAR>.json
    data/history/ca-curve-<YEAR>.json
    data/history/spreads-<YEAR>.json

Entries are keyed by observation date — re-running on the same day just
replaces that day's entry, so the job is safe to run repeatedly.
Skips entirely if market.json is still seed/demo data.
"""

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MARKET = ROOT / "data" / "market.json"
HIST_DIR = ROOT / "data" / "history"


def load_history(path: Path, meta: dict) -> dict:
    if path.exists():
        try:
            return json.loads(path.read_text())
        except json.JSONDecodeError:
            print(f"WARN corrupt {path.name}, starting fresh", file=sys.stderr)
    return {**meta, "days": []}


def upsert(days: list, entry: dict) -> None:
    days[:] = [d for d in days if d.get("date") != entry["date"]]
    days.append(entry)
    days.sort(key=lambda d: d["date"])


def save(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, separators=(",", ":")) + "\n")


def main() -> int:
    if not MARKET.exists():
        print("ERROR: data/market.json not found", file=sys.stderr)
        return 1
    market = json.loads(MARKET.read_text())
    if market.get("demo"):
        print("Seed/demo data — nothing to record yet.")
        return 0

    wrote = []

    for key, country in (("us", "US"), ("canada", "CA")):
        block = market.get(key) or {}
        date, curve = block.get("date"), block.get("curve") or []
        if not date or not curve:
            print(f"WARN no {country} data to record", file=sys.stderr)
            continue
        year = date[:4]
        path = HIST_DIR / f"{country.lower()}-curve-{year}.json"
        hist = load_history(path, {"country": country, "year": int(year)})
        upsert(hist["days"], {
            "date": date,
            "yields": {p["tenor"]: p["yield"] for p in curve if p.get("yield") is not None},
        })
        save(path, hist)
        wrote.append(f"{country} {date} ({len(hist['days'])} days)")

    spreads = market.get("spreads") or {}
    if os.environ.get("INCLUDE_ICE_SPREADS") != "1":
        spreads = {k: v for k, v in spreads.items()
                   if k not in ("ig_oas_bp", "hy_oas_bp")}
    date = (market.get("us") or {}).get("date")
    if spreads and date:
        year = date[:4]
        path = HIST_DIR / f"spreads-{year}.json"
        hist = load_history(path, {"series": "spreads", "year": int(year)})
        upsert(hist["days"], {"date": date, **spreads})
        save(path, hist)
        wrote.append(f"spreads {date}")

    # Policy rates, real yield and breakeven: one row per US close date.
    macro = market.get("macro") or {}
    if macro and date:
        year = date[:4]
        path = HIST_DIR / f"macro-{year}.json"
        hist = load_history(path, {"series": "macro", "year": int(year)})
        upsert(hist["days"], {"date": date,
                              **{k: v.get("value") for k, v in macro.items()
                                 if isinstance(v, dict)}})
        save(path, hist)
        wrote.append(f"macro {date}")

    # ICE BofA spread values are copyrighted (see fetch_data.py). Unless the
    # opt-in flag is set, remove any that earlier runs recorded.
    if os.environ.get("INCLUDE_ICE_SPREADS") != "1":
        for path in sorted(HIST_DIR.glob("spreads-*.json")):
            try:
                hist = json.loads(path.read_text())
            except json.JSONDecodeError:
                continue
            removed = 0
            for day in hist.get("days", []):
                for key in ("ig_oas_bp", "hy_oas_bp"):
                    if key in day:
                        del day[key]
                        removed += 1
            if removed:
                save(path, hist)
                wrote.append(f"scrubbed {removed} ICE values from {path.name}")

    print("Recorded: " + "; ".join(wrote) if wrote else "Nothing recorded")
    return 0


if __name__ == "__main__":
    sys.exit(main())
