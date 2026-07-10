#!/usr/bin/env python3
"""
Fetch US Treasury yields (FRED) and Government of Canada yields (Bank of
Canada Valet), plus credit spreads, and write them to data/market.json.

Runs nightly via GitHub Actions. Requires env var FRED_API_KEY
(free key: https://fred.stlouisfed.org/docs/api/api_key.html).
Bank of Canada Valet needs no key.

Uses only the Python standard library — no pip installs needed.
"""

import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

FRED_KEY = os.environ.get("FRED_API_KEY", "")

# (tenor label, FRED series id, maturity in years)
FRED_TENORS = [
    ("3M", "DGS3MO", 0.25),
    ("6M", "DGS6MO", 0.5),
    ("1Y", "DGS1", 1),
    ("2Y", "DGS2", 2),
    ("5Y", "DGS5", 5),
    ("7Y", "DGS7", 7),
    ("10Y", "DGS10", 10),
    ("20Y", "DGS20", 20),
    ("30Y", "DGS30", 30),
]

# ICE BofA option-adjusted spreads, reported in percent on FRED
FRED_SPREADS = {
    "ig_oas": "BAMLC0A0CM",    # US corporate investment grade
    "hy_oas": "BAMLH0A0HYM2",  # US high yield
}

# (tenor label, Bank of Canada Valet series id, maturity in years)
# Verify ids at https://www.bankofcanada.ca/valet/docs if any fail.
BOC_TENORS = [
    ("3M", "TB.CDN.90D.DQ.YLD", 0.25),
    ("2Y", "BD.CDN.2YR.DQ.YLD", 2),
    ("3Y", "BD.CDN.3YR.DQ.YLD", 3),
    ("5Y", "BD.CDN.5YR.DQ.YLD", 5),
    ("7Y", "BD.CDN.7YR.DQ.YLD", 7),
    ("10Y", "BD.CDN.10YR.DQ.YLD", 10),
    ("30Y", "BD.CDN.LONG.DQ.YLD", 30),
]

OUT_PATH = Path(__file__).resolve().parent.parent / "data" / "market.json"


def get_json(url: str, timeout: int = 30) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "basispoint-data/0.1"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.load(resp)


def fred_latest(series_id: str):
    """Return (value, date) for the most recent non-empty observation."""
    params = urllib.parse.urlencode({
        "series_id": series_id,
        "api_key": FRED_KEY,
        "file_type": "json",
        "sort_order": "desc",
        "limit": "12",
    })
    data = get_json(f"https://api.stlouisfed.org/fred/series/observations?{params}")
    for obs in data.get("observations", []):
        if obs.get("value") not in (".", "", None):
            return float(obs["value"]), obs["date"]
    return None, None


def boc_latest(series_id: str):
    """Return (value, date) for the most recent non-empty observation.

    Valet's `recent=N` does not guarantee observation order, so never assume
    it: sort by date descending ourselves, then take the first real value.
    """
    url = f"https://www.bankofcanada.ca/valet/observations/{series_id}/json?recent=10"
    data = get_json(url)
    observations = sorted(
        data.get("observations", []),
        key=lambda o: o.get("d", ""),
        reverse=True,  # newest first
    )
    for obs in observations:
        cell = obs.get(series_id) or {}
        if cell.get("v") not in (None, ""):
            return float(cell["v"]), obs.get("d")
    return None, None


def build_curve(tenors, fetch_fn, label):
    curve, latest_date = [], None
    for tenor, series_id, years in tenors:
        try:
            value, date = fetch_fn(series_id)
        except Exception as exc:  # noqa: BLE001 - log and continue
            print(f"WARN {label} {series_id}: {exc}", file=sys.stderr)
            value, date = None, None
        if value is not None:
            curve.append({"tenor": tenor, "years": years, "yield": round(value, 2)})
            if date and (latest_date is None or date > latest_date):
                latest_date = date
        else:
            print(f"WARN {label} {series_id}: no recent value", file=sys.stderr)
    return curve, latest_date


def main() -> int:
    if not FRED_KEY:
        print("ERROR: FRED_API_KEY is not set", file=sys.stderr)
        return 1

    us_curve, us_date = build_curve(FRED_TENORS, fred_latest, "FRED")
    ca_curve, ca_date = build_curve(BOC_TENORS, boc_latest, "BoC")

    spreads = {}
    by_tenor = {p["tenor"]: p["yield"] for p in us_curve}
    if "2Y" in by_tenor and "10Y" in by_tenor:
        spreads["us_2s10s_bp"] = round((by_tenor["10Y"] - by_tenor["2Y"]) * 100)
    for key, series_id in FRED_SPREADS.items():
        try:
            value, _ = fred_latest(series_id)
            if value is not None:
                spreads[f"{key}_bp"] = round(value * 100)
        except Exception as exc:  # noqa: BLE001
            print(f"WARN FRED {series_id}: {exc}", file=sys.stderr)

    if len(us_curve) < 4:
        print("ERROR: US curve too sparse, refusing to overwrite data", file=sys.stderr)
        return 1

    payload = {
        "updated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "demo": False,
        "us": {"date": us_date, "curve": us_curve},
        "canada": {"date": ca_date, "curve": ca_curve},
        "spreads": spreads,
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(payload, indent=2) + "\n")
    print(f"Wrote {OUT_PATH} — US {len(us_curve)} pts ({us_date}), "
          f"CA {len(ca_curve)} pts ({ca_date}), spreads: {spreads}")
    return 0


if __name__ == "__main__":
    sys.exit(main())