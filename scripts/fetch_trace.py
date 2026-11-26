#!/usr/bin/env python3
"""
Fetch FINRA TRACE corporate bond aggregate data via the FINRA Query API and
write it to data/corporates.json.

Datasets (group FixedIncomeMarket):
  - corporateMarketBreadth   : advances/declines, volume, highs/lows by segment
  - corporateMarketSentiment : trade counts and volume by trade type and segment

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
from datetime import date, datetime, timedelta, timezone
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
MAX_SENTIMENT_ROWS = 60
LOOKBACK_DAYS = 14      # window asked of FINRA
MAX_AGE_DAYS = 30       # older than this is never written to the site


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


def post_dataset(name: str, token: str | None, body: dict):
    """POST query: the only way to filter by date on the FINRA Query API."""
    headers = {"Accept": "application/json",
               "Content-Type": "application/json",
               "User-Agent": "basispoint-data/0.3"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(f"{API_BASE}/{name}", method="POST",
                                 data=json.dumps(body).encode(),
                                 headers=headers)
    with urllib.request.urlopen(req, timeout=45) as resp:
        raw = resp.read()
    if not raw.strip():          # FINRA answers 204/empty when nothing matches
        return []
    data = json.loads(raw)
    if isinstance(data, dict):
        for key in ("data", "results", "records"):
            if isinstance(data.get(key), list):
                return data[key]
        return []
    return data if isinstance(data, list) else []


def fetch_rows(name: str, token: str | None, today: date | None = None):
    """Fetch the most recent rows.

    History of this function, so nobody repeats it:
      1. Unsorted GET  -> the API returns the OLDEST rows (a 2024 date on a
         2026 site).
      2. GET with sortFields -> HTTP 400. FINRA only allows sortFields when
         the request also carries an EQUAL compareFilter on every partition
         field, so that silently fell back to (1).
    What works is asking for a date window, then picking the newest date
    locally:
      A. POST dateRangeFilters for the last LOOKBACK_DAYS days.
      B. If that is refused or empty, POST an EQUAL compareFilter one day at
         a time, newest first (the form FINRA requires for partition fields).
      C. Last resort: the unsorted GET, which main() will reject as stale.
    """
    today = today or date.today()
    sample = fetch_dataset(name, token, "limit=5")
    date_field = detect_date_field(sample) or "tradeReportDate"

    start = (today - timedelta(days=LOOKBACK_DAYS)).isoformat()
    try:
        rows = post_dataset(name, token, {
            "limit": 5000,
            "dateRangeFilters": [{"fieldName": date_field,
                                  "startDate": start,
                                  "endDate": today.isoformat()}],
        })
        if rows:
            return rows
        print(f"WARN {name}: no rows between {start} and {today}",
              file=sys.stderr)
    except Exception as exc:  # noqa: BLE001
        print(f"WARN {name}: date-range query failed ({exc})", file=sys.stderr)

    for back in range(0, LOOKBACK_DAYS + 1):
        day = today - timedelta(days=back)
        if day.weekday() >= 5:
            continue
        try:
            rows = post_dataset(name, token, {
                "limit": 5000,
                "compareFilters": [{"fieldName": date_field,
                                    "fieldValue": day.isoformat(),
                                    "compareType": "EQUAL"}],
            })
        except Exception as exc:  # noqa: BLE001
            print(f"WARN {name}: day query {day} failed ({exc})",
                  file=sys.stderr)
            break
        if rows:
            return rows

    print(f"WARN {name}: falling back to unsorted GET", file=sys.stderr)
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
        "source": "FINRA",
        "notice": ("Data owned and provided by FINRA. Shown free of charge "
                   "for non-commercial use; not to be redistributed."),
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
        if date:
            try:
                age = (datetime.now(timezone.utc).date()
                       - datetime.fromisoformat(date[:10]).date()).days
            except ValueError:
                age = 0
            if age > MAX_AGE_DAYS:
                print(f"WARN {dataset}: newest row is {date} ({age} days old) "
                      f"— not publishing it", file=sys.stderr)
                continue
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
