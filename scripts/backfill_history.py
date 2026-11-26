#!/usr/bin/env python3
"""
One-time backfill of daily history from BACKFILL_START, so charts and the
market brief have years of context instead of starting on the day the
pipeline was switched on.

Runs every night in the workflow but only does work while the history is
missing days before the first recorded date. It never overwrites a day that
is already recorded, so the nightly snapshots stay the source of truth.

Writes the same yearly files fetch_history.py writes:
    data/history/us-curve-<YEAR>.json   (FRED)
    data/history/ca-curve-<YEAR>.json   (Bank of Canada Valet)
    data/history/spreads-<YEAR>.json    (US 2s10s, computed)
    data/history/macro-<YEAR>.json      (policy rates, real yield, breakeven)

ICE BofA spread indices are deliberately not backfilled (copyrighted).
"""

import json
import os
import sys
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fetch_data import (  # noqa: E402
    BOC_MACRO, BOC_TENORS, FRED_KEY, FRED_MACRO, FRED_TENORS, get_json,
)

BACKFILL_START = "2024-01-01"
HIST_DIR = Path(__file__).resolve().parent.parent / "data" / "history"


def fred_series(series_id: str) -> dict[str, float]:
    params = urllib.parse.urlencode({
        "series_id": series_id, "api_key": FRED_KEY, "file_type": "json",
        "observation_start": BACKFILL_START,
    })
    data = get_json(f"https://api.stlouisfed.org/fred/series/observations?{params}", timeout=60)
    out = {}
    for obs in data.get("observations", []):
        if obs.get("value") not in (".", "", None):
            out[obs["date"]] = round(float(obs["value"]), 2)
    return out


def boc_series(series_id: str) -> dict[str, float]:
    url = (f"https://www.bankofcanada.ca/valet/observations/{series_id}/json"
           f"?start_date={BACKFILL_START}")
    data = get_json(url, timeout=60)
    out = {}
    for obs in data.get("observations", []):
        cell = obs.get(series_id) or {}
        if cell.get("v") not in (None, ""):
            out[obs["d"]] = round(float(cell["v"]), 2)
    return out


def load(name: str, year: str, meta: dict) -> dict:
    path = HIST_DIR / f"{name}-{year}.json"
    if path.exists():
        try:
            return json.loads(path.read_text())
        except json.JSONDecodeError:
            pass
    return {**meta, "year": int(year), "days": []}


def earliest(name: str) -> str | None:
    dates = []
    for path in HIST_DIR.glob(f"{name}-*.json"):
        try:
            dates += [d["date"] for d in json.loads(path.read_text()).get("days", [])]
        except (json.JSONDecodeError, KeyError):
            continue
    return min(dates) if dates else None


def merge(name: str, meta: dict, rows: dict[str, dict]) -> int:
    """Add rows (date -> fields) for dates not yet recorded. Returns count."""
    added = 0
    by_year: dict[str, dict[str, dict]] = {}
    for d, fields in rows.items():
        by_year.setdefault(d[:4], {})[d] = fields
    for year, days in by_year.items():
        hist = load(name, year, meta)
        have = {d["date"] for d in hist["days"]}
        for d, fields in days.items():
            if d not in have and fields:
                hist["days"].append({"date": d, **fields})
                added += 1
        hist["days"].sort(key=lambda r: r["date"])
        HIST_DIR.mkdir(parents=True, exist_ok=True)
        (HIST_DIR / f"{name}-{year}.json").write_text(
            json.dumps(hist, separators=(",", ":")) + "\n")
    return added


def pivot(series: dict[str, dict[str, float]]) -> dict[str, dict]:
    """{label: {date: value}} -> {date: {label: value}}"""
    out: dict[str, dict] = {}
    for label, points in series.items():
        for d, v in points.items():
            out.setdefault(d, {})[label] = v
    return out


def needs(name: str) -> bool:
    first = earliest(name)
    # A week of slack: the first trading day of the year is never 1 January.
    return first is None or first > "2024-01-08"


def main() -> int:
    if os.environ.get("SKIP_BACKFILL") == "1":
        return 0
    if not FRED_KEY:
        print("Backfill skipped: FRED_API_KEY not set")
        return 0
    report = []

    try:
        if needs("us-curve") or needs("spreads"):
            us = pivot({t: fred_series(s) for t, s, _ in FRED_TENORS})
            n = merge("us-curve", {"country": "US"},
                      {d: {"yields": y} for d, y in us.items()})
            s = merge("spreads", {"series": "spreads"},
                      {d: {"us_2s10s_bp": round((y["10Y"] - y["2Y"]) * 100)}
                       for d, y in us.items() if "2Y" in y and "10Y" in y})
            report.append(f"US curve +{n} days, spreads +{s}")
    except Exception as exc:  # noqa: BLE001
        print(f"WARN backfill US: {exc}", file=sys.stderr)

    try:
        if needs("ca-curve"):
            ca = {}
            for t, s, _ in BOC_TENORS:
                try:
                    ca[t] = boc_series(s)
                except Exception as exc:  # noqa: BLE001
                    print(f"WARN backfill BoC {s}: {exc}", file=sys.stderr)
            n = merge("ca-curve", {"country": "CA"},
                      {d: {"yields": y} for d, y in pivot(ca).items()})
            report.append(f"Canada curve +{n} days")
    except Exception as exc:  # noqa: BLE001
        print(f"WARN backfill Canada: {exc}", file=sys.stderr)

    try:
        if needs("macro"):
            series = {}
            for k, s in FRED_MACRO.items():
                try:
                    series[k] = fred_series(s)
                except Exception as exc:  # noqa: BLE001
                    print(f"WARN backfill FRED {s}: {exc}", file=sys.stderr)
            for k, s in BOC_MACRO.items():
                try:
                    series[k] = boc_series(s)
                except Exception as exc:  # noqa: BLE001
                    print(f"WARN backfill BoC {s}: {exc}", file=sys.stderr)
            # Keep only US trading days, carrying the BoC rate (which only
            # changes on decision dates) forward onto them.
            rows = pivot(series)
            us_days = sorted(d for d, r in rows.items() if "fed_upper" in r)
            boc = series.get("boc_target", {})
            last = None
            out = {}
            for d in sorted(set(us_days) | set(boc)):
                if d in boc:
                    last = boc[d]
                if d in us_days:
                    r = dict(rows[d])
                    if last is not None:
                        r["boc_target"] = last
                    out[d] = r
            n = merge("macro", {"series": "macro"}, out)
            report.append(f"macro +{n} days")
    except Exception as exc:  # noqa: BLE001
        print(f"WARN backfill macro: {exc}", file=sys.stderr)

    print("Backfill: " + ("; ".join(report) if report else "nothing to do"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
