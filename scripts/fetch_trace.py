#!/usr/bin/env python3
"""
Fetch FINRA TRACE corporate bond aggregate data via the FINRA Query API and
write it to data/corporates.json.

Datasets (group FixedIncomeMarket):
  - corporateMarketBreadth   : advances/declines, volume, highs/lows by segment
  - corporateMarketSentiment : most-active IG/HY/convertible bonds with prices

Auth: many FINRA datasets allow unauthenticated access at low rate limits;
higher limits require a free API account. This script tries the token flow
when FINRA_API_CLIENT_ID / FINRA_API_CLIENT_SECRET are set (repo secrets),
and falls back to unauthenticated requests otherwise.

Design notes (learned the hard way from the BoC ordering bug):
  - Never assume field names or row order. Dates are detected from candidate
    field names and rows are sorted by the detected date, descending.
  - On any failure this script exits 0 WITHOUT touching an existing good
    corporates.json — a failed TRACE fetch must not break the nightly run.
  - Raw rows for the latest date are stored verbatim alongside detected
    fields, so the front end can render whatever schema FINRA actually sends.
  - CUSIP-like fields are stripped before writing (identifier licensing).
"""

import base64
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

API_BASE = "https://api.finra.org/data/group/FixedIncomeMarket/name"
TOKEN_URL = ("https://ews.fip.finra.org/fip/rest/ews/oauth2/access_token"
             "?grant_type=client_credentials")
DATASETS = {
    "breadth": "corporateMarketBreadth",
    "sentiment": "corporateMarketSentiment",
}
DATE_FIELD_CANDIDATES = [
    "tradeDate", "tradeReportDate", "asOfDate", "date", "reportDate",
    "weekStartDate", "processDate",
]
OUT_PATH = Path(__file__).resolve().parent.parent / "data" / "corporates.json"
MAX_SENTIMENT_ROWS = 15


def get_token():
    cid = os.environ.get("FINRA_API_CLIENT_ID", "")
    secret = os.environ.get("FINRA_API_CLIENT_SECRET", "")
    if not cid or not secret:
        return None
    basic = base64.b64encode(f"{cid}:{secret}".encode()).decode()
    req = urllib.request.Request(TOKEN_URL, method="POST",
                                 headers={"Authorization": f"Basic {basic}"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.load(resp).get("access_token")
    except Exception as exc:  # noqa: BLE001
        print(f"WARN token request failed ({exc}); trying unauthenticated",
              file=sys.stderr)
        return None


def fetch_dataset(name: str, token: str | None, query: str = "limit=100"):
    url = f"{API_BASE}/{name}?{query}"
    headers = {"Accept": "application/json",
               "User-Agent": "basispoint-data/0.2"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=45) as resp:
        data = json.load(resp)
    if isinstance(data, dict):  # some responses wrap rows
        for key in ("data", "results", "records"):
            if isinstance(data.get(key), list):
                return data[key]
        return []
    return data if isinstance(data, list) else []


def fetch_rows(name: str, token: str | None):
    """Fetch rows newest-first.

    The API may return records oldest-first, and datasets span years — so an
    unsorted `limit=N` can silently deliver ancient data (this happened:
    a 2024 date on a 2026 site). Two passes: sample a few rows to detect the
    date field, then request the real page sorted descending on it. If the
    sort parameter is rejected, fall back to unsorted and let latest_rows()
    salvage what it can.
    """
    sample = fetch_dataset(name, token, "limit=5")
    date_field = detect_date_field(sample)
    if date_field:
        try:
            rows = fetch_dataset(name, token,
                                 f"limit=100&sortFields=-{date_field}")
            if rows:
                return rows
        except Exception as exc:  # noqa: BLE001
            print(f"WARN {name}: sorted fetch failed ({exc}); "
                  f"falling back to unsorted", file=sys.stderr)
    return fetch_dataset(name, token)


def detect_date_field(rows):
    if not rows:
        return None
    keys = rows[0].keys()
    for cand in DATE_FIELD_CANDIDATES:
        for k in keys:
            if k.lower() == cand.lower():
                return k
    # fallback: any key containing 'date'
    for k in keys:
        if "date" in k.lower():
            return k
    return None


def strip_identifiers(row: dict) -> dict:
    return {k: v for k, v in row.items() if not re.search(r"cusip", k, re.I)}


def latest_rows(rows):
    """Return (date_string, rows_for_that_date) — order-agnostic."""
    date_field = detect_date_field(rows)
    if not date_field:
        return None, [strip_identifiers(r) for r in rows[:MAX_SENTIMENT_ROWS]]
    dated = [r for r in rows if r.get(date_field)]
    if not dated:
        return None, []
    latest = max(str(r[date_field])[:10] for r in dated)
    todays = [strip_identifiers(r) for r in dated
              if str(r[date_field])[:10] == latest]
    return latest, todays


def main() -> int:
    token = get_token()
    result = {
        "updated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "demo": False,
        "source": "FINRA Query API (TRACE aggregates)",
    }
    got_anything = False

    for label, dataset in DATASETS.items():
        try:
            rows = fetch_rows(dataset, token)
        except urllib.error.HTTPError as exc:
            print(f"WARN {dataset}: HTTP {exc.code} — "
                  f"{'check FINRA_API_CLIENT_ID/SECRET secrets' if exc.code in (401, 403) else 'see developer.finra.org'}",
                  file=sys.stderr)
            continue
        except Exception as exc:  # noqa: BLE001
            print(f"WARN {dataset}: {exc}", file=sys.stderr)
            continue
        date, rows_latest = latest_rows(rows)
        if rows_latest:
            result[label] = {"date": date, "rows": rows_latest[:MAX_SENTIMENT_ROWS]
                             if label == "sentiment" else rows_latest}
            got_anything = True
            print(f"OK {dataset}: {len(rows_latest)} rows for {date}")
        else:
            print(f"WARN {dataset}: no rows returned", file=sys.stderr)

    if not got_anything:
        print("TRACE fetch produced nothing — leaving existing "
              "data/corporates.json untouched.", file=sys.stderr)
        return 0  # never fail the nightly run over the corporate layer

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(result, indent=2) + "\n")
    print(f"Wrote {OUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())