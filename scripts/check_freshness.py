#!/usr/bin/env python3
"""
Freshness guard: fail loudly (exit 1) if any market data source has gone
stale, so the GitHub Actions run turns red instead of the site going quietly
wrong. Born from the Bank of Canada ordering bug, which served two-week-old
Canadian yields for days without a single error anywhere.

Runs as the LAST workflow step, after data is committed — a red run here
still ships whatever data was fetched; it just demands human attention.
"""

import json
import sys
from datetime import date, timedelta
from pathlib import Path

MARKET = Path(__file__).resolve().parent.parent / "data" / "market.json"
MAX_BUSINESS_DAYS = 6  # tolerant of long weekends + holiday clusters


def business_days_between(d0: date, d1: date) -> int:
    if d0 > d1:
        d0, d1 = d1, d0
    days, cur = 0, d0
    while cur < d1:
        cur += timedelta(days=1)
        if cur.weekday() < 5:
            days += 1
    return days


def main() -> int:
    if not MARKET.exists():
        print("STALE: data/market.json missing entirely", file=sys.stderr)
        return 1
    market = json.loads(MARKET.read_text())
    if market.get("demo"):
        print("Seed data — freshness check skipped.")
        return 0

    today = date.today()
    problems = []
    for key, label in (("us", "US (FRED)"), ("canada", "Canada (BoC)")):
        d = (market.get(key) or {}).get("date")
        if not d:
            problems.append(f"{label}: no date recorded")
            continue
        try:
            gap = business_days_between(date.fromisoformat(d[:10]), today)
        except ValueError:
            problems.append(f"{label}: unparseable date {d!r}")
            continue
        if gap > MAX_BUSINESS_DAYS:
            problems.append(f"{label}: last close {d} is {gap} business days old")
        else:
            print(f"OK {label}: {d} ({gap} business days old)")

    if problems:
        for p in problems:
            print("STALE:", p, file=sys.stderr)
        print("\nInvestigate the fetch logs above; a source has stopped "
              "updating or a series id changed.", file=sys.stderr)
        return 1
    print("All sources fresh.")
    return 0


if __name__ == "__main__":
    sys.exit(main())