#!/usr/bin/env python3
"""
Build data/brief.json: the numbers behind the Market brief page.

Everything here is arithmetic on data the pipeline already collected:
moves over standard windows, curve slopes, the US–Canada gap, how far
2-year yields sit from each central bank's policy rate, whether a move in
the US 10-year came from real yields or from inflation expectations, and
where today's level sits in its recorded range. The "observations" are
sentences generated from fixed rules over those numbers. They describe;
they never recommend.

Reads:  data/market.json, data/history/*.json, assets/calendar.json (hand-kept)
Writes: data/brief.json
"""

import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
HIST = DATA / "history"

WINDOWS = [("1d", 1), ("1w", 7), ("1m", 30), ("3m", 91), ("1y", 365)]
KEY_TENORS = ["2Y", "5Y", "10Y", "30Y"]


def load_series(name: str) -> list[dict]:
    rows = []
    for path in sorted(HIST.glob(f"{name}-*.json")):
        try:
            rows += json.loads(path.read_text()).get("days", [])
        except json.JSONDecodeError:
            print(f"WARN unreadable {path.name}", file=sys.stderr)
    seen = {}
    for r in rows:
        if r.get("date"):
            seen[r["date"]] = r
    return [seen[d] for d in sorted(seen)]


def on_or_before(rows: list[dict], target: str) -> dict | None:
    lo, hi, best = 0, len(rows) - 1, None
    while lo <= hi:
        mid = (lo + hi) // 2
        if rows[mid]["date"] <= target:
            best, lo = rows[mid], mid + 1
        else:
            hi = mid - 1
    return best


def days_before(d: str, n: int) -> str:
    return (date.fromisoformat(d) - timedelta(days=n)).isoformat()


def bp(a, b):
    return None if a is None or b is None else round((a - b) * 100)


def curve_value(row, tenor):
    return (row or {}).get("yields", {}).get(tenor)


def moves(rows: list[dict], getter) -> dict:
    """Level now and change in bp over each window, for one series."""
    if not rows:
        return {}
    last = rows[-1]
    now = getter(last)
    out = {"level": now, "date": last["date"]}
    for label, n in WINDOWS:
        if label == "1d":
            prev = rows[-2] if len(rows) > 1 else None
        else:
            prev = on_or_before(rows, days_before(last["date"], n))
            # A window reaching before recorded history has no answer.
            if prev is not None and prev["date"] == rows[0]["date"] and \
                    rows[0]["date"] > days_before(last["date"], n):
                prev = None
        out[label] = bp(now, getter(prev)) if prev else None
    return out


def range_stats(rows: list[dict], getter, days: int = 365) -> dict | None:
    if not rows:
        return None
    start = days_before(rows[-1]["date"], days)
    # Only call it a one-year range when history actually covers the year.
    if rows[0]["date"] > days_before(start, -14):
        return None
    vals = [(r["date"], getter(r)) for r in rows if r["date"] >= start]
    vals = [(d, v) for d, v in vals if v is not None]
    if len(vals) < 20:
        return None
    now = vals[-1][1]
    lo = min(vals, key=lambda x: x[1])
    hi = max(vals, key=lambda x: x[1])
    below = sum(1 for _, v in vals if v < now)
    return {
        "window_days": days, "from": vals[0][0], "n": len(vals),
        "low": lo[1], "low_date": lo[0], "high": hi[1], "high_date": hi[0],
        "percentile": round(100 * below / (len(vals) - 1)) if len(vals) > 1 else None,
    }


def fmt_bp(v):
    return f"{'+' if v > 0 else ''}{v}bp"


def direction(v, up="rose", down="fell"):
    return up if v > 0 else down


def observations(b: dict) -> list[str]:
    """Rule-based sentences. Facts and conventional readings only."""
    out = []
    us10 = b["us"]["moves"].get("10Y", {})
    ca10 = b["canada"]["moves"].get("10Y", {})
    for name, m in (("US", us10), ("Canadian", ca10)):
        w = m.get("1w")
        if w is not None and abs(w) >= 10:
            out.append(f"The {name} 10-year yield {direction(w)} {abs(w)}bp over the past week, "
                       f"to {m['level']:.2f}%.")

    s = b["us"]["slopes"].get("2s10s")
    if s and s.get("level") is not None:
        lvl, m1 = s["level"], s.get("1m")
        shape = "inverted" if lvl < 0 else "positively sloped"
        line = f"The US curve is {shape}: the 10-year yields {abs(lvl)}bp {'less' if lvl < 0 else 'more'} than the 2-year"
        if m1 is not None and abs(m1) >= 8:
            line += f", {'steeper' if m1 > 0 else 'flatter'} by {abs(m1)}bp than a month ago"
        out.append(line + ".")

    for key, label, bank in (("us", "US", "Fed funds target midpoint"),
                             ("canada", "Canadian", "Bank of Canada's target rate")):
        g = b["policy"].get(f"{key}_2y_minus_policy_bp")
        if g is None:
            continue
        if g >= 15:
            out.append(f"The {label} 2-year yield is {g}bp above the {bank}. A 2-year yield above the "
                       f"policy rate is consistent with markets expecting rates to average higher over "
                       f"the next two years.")
        elif g <= -15:
            out.append(f"The {label} 2-year yield is {abs(g)}bp below the {bank}, consistent with "
                       f"markets expecting rate cuts over the next two years.")
        else:
            out.append(f"The {label} 2-year yield is within 15bp of the {bank}, consistent with "
                       f"markets expecting little net change in rates over two years.")

    # The shortest of one or three months in which the 10-year moved 10bp+.
    for win, words in (("1m", "month"), ("3m", "three months")):
        d = b.get("decomposition", {}).get(win)
        if d and d.get("nominal") is not None and abs(d["nominal"]) >= 10 \
                and d.get("real") is not None and d.get("breakeven") is not None:
            break
    else:
        d = None
    if d:
        driver = "real yields" if abs(d["real"]) >= abs(d["breakeven"]) else "inflation expectations"
        out.append(f"Over the past {words} the US 10-year moved {fmt_bp(d['nominal'])}: real yield "
                   f"{fmt_bp(d['real'])}, inflation breakeven {fmt_bp(d['breakeven'])}. Most of the "
                   f"move came from {driver}.")

    gap = b["cross_border"].get("10Y")
    if gap and gap.get("level") is not None:
        line = f"US 10-year bonds yield {gap['level']}bp more than Canadian 10-year bonds"
        if gap.get("1m") is not None and abs(gap["1m"]) >= 8:
            line += f", a gap that {'widened' if gap['1m'] > 0 else 'narrowed'} by {abs(gap['1m'])}bp over the month"
        out.append(line + ".")

    r = b["us"]["range_1y"].get("10Y")
    if r and r.get("percentile") is not None:
        if r["percentile"] >= 85:
            out.append(f"The US 10-year is near the top of its one-year range "
                       f"({r['low']:.2f}% to {r['high']:.2f}%).")
        elif r["percentile"] <= 15:
            out.append(f"The US 10-year is near the bottom of its one-year range "
                       f"({r['low']:.2f}% to {r['high']:.2f}%).")

    for ev in b.get("calendar", [])[:2]:
        if ev.get("days_away") is not None and ev["days_away"] <= 21:
            out.append(f"Next {ev['bank']} decision: {ev['date_label']}, in {ev['days_away']} days.")
    return out


def main() -> int:
    market_path = DATA / "market.json"
    if not market_path.exists():
        print("ERROR: data/market.json missing", file=sys.stderr)
        return 1
    market = json.loads(market_path.read_text())
    if market.get("demo"):
        print("Seed data — brief not built.")
        return 0

    us = load_series("us-curve")
    ca = load_series("ca-curve")
    macro = load_series("macro")
    if len(us) < 2:
        print("Not enough history for a brief yet.")
        return 0

    brief = {
        "updated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "asof": {"us": us[-1]["date"], "canada": ca[-1]["date"] if ca else None},
        "history_from": {"us": us[0]["date"], "canada": ca[0]["date"] if ca else None},
    }

    for key, rows in (("us", us), ("canada", ca)):
        tenors = [t for t in KEY_TENORS if rows and curve_value(rows[-1], t) is not None]
        slopes = {}
        for label, a, b2 in (("2s10s", "2Y", "10Y"), ("5s30s", "5Y", "30Y"), ("3m10y", "3M", "10Y")):
            def slope(r, a=a, b2=b2):
                x, y = curve_value(r, a), curve_value(r, b2)
                return None if x is None or y is None else round(y - x, 4)
            m = moves(rows, slope)
            if m.get("level") is not None:
                m["level"] = round(m["level"] * 100)
                slopes[label] = m
        brief[key] = {
            "moves": {t: moves(rows, lambda r, t=t: curve_value(r, t)) for t in tenors},
            "slopes": slopes,
            "range_1y": {t: range_stats(rows, lambda r, t=t: curve_value(r, t))
                         for t in ("2Y", "10Y") if t in tenors},
        }

    # US minus Canada, matched by date.
    ca_by_date = {r["date"]: r for r in ca}
    paired = [{"date": r["date"], "us": r, "ca": ca_by_date[r["date"]]}
              for r in us if r["date"] in ca_by_date]
    brief["cross_border"] = {}
    for t in ("2Y", "10Y"):
        m = moves(paired, lambda r, t=t: (None if curve_value(r["us"], t) is None
                                         or curve_value(r["ca"], t) is None
                                         else curve_value(r["us"], t) - curve_value(r["ca"], t)))
        if m.get("level") is not None:
            m["level"] = round(m["level"] * 100)
            brief["cross_border"][t] = m

    # Policy rates against 2-year yields.
    mc = market.get("macro") or {}
    val = lambda k: (mc.get(k) or {}).get("value")
    policy = {}
    if val("fed_upper") is not None and val("fed_lower") is not None:
        mid = (val("fed_upper") + val("fed_lower")) / 2
        policy["fed_range"] = [val("fed_lower"), val("fed_upper")]
        policy["fed_mid"] = round(mid, 3)
        policy["us_2y_minus_policy_bp"] = bp(curve_value(us[-1], "2Y"), mid)
    if val("boc_target") is not None:
        policy["boc_target"] = val("boc_target")
        if ca:
            policy["canada_2y_minus_policy_bp"] = bp(curve_value(ca[-1], "2Y"), val("boc_target"))
    # When each policy rate last changed, from the recorded macro history.
    for k in ("fed_upper", "boc_target"):
        pts = [(r["date"], r.get(k)) for r in macro if r.get(k) is not None]
        for i in range(len(pts) - 1, 0, -1):
            if pts[i][1] != pts[i - 1][1]:
                policy[f"{k}_last_change"] = {"date": pts[i][0], "from": pts[i - 1][1], "to": pts[i][1]}
                break
    brief["policy"] = policy

    # US 10-year: nominal = real + breakeven (approximately).
    decomp = {}
    # Only days carrying both real yield and breakeven, and a US close:
    # policy rates are published on weekends and holidays, these are not.
    us_dates = {r["date"] for r in us}
    split = [r for r in macro if r.get("us_real_10y") is not None
             and r.get("us_breakeven_10y") is not None and r["date"] in us_dates]
    if len(split) > 1:
        macro = split
        last = macro[-1]
        for label, n in (("1w", 7), ("1m", 30), ("3m", 91)):
            prev = on_or_before(macro, days_before(last["date"], n))
            if not prev or prev["date"] == last["date"]:
                continue
            nominal_now = curve_value(on_or_before(us, last["date"]), "10Y")
            nominal_then = curve_value(on_or_before(us, prev["date"]), "10Y")
            decomp[label] = {
                "from": prev["date"], "to": last["date"],
                "nominal": bp(nominal_now, nominal_then),
                "real": bp(last.get("us_real_10y"), prev.get("us_real_10y")),
                "breakeven": bp(last.get("us_breakeven_10y"), prev.get("us_breakeven_10y")),
            }
    brief["decomposition"] = decomp
    brief["levels"] = {"us_real_10y": val("us_real_10y"),
                       "us_breakeven_10y": val("us_breakeven_10y")}

    # Upcoming central bank decisions.
    today = date.today()
    cal = []
    cal_path = ROOT / "assets" / "calendar.json"
    if cal_path.exists():
        for ev in json.loads(cal_path.read_text()).get("decisions", []):
            d = date.fromisoformat(ev["date"])
            if d >= today:
                cal.append({**ev, "days_away": (d - today).days,
                            "date_label": d.strftime("%a %d %b %Y")})
    cal.sort(key=lambda e: e["date"])
    brief["calendar"] = cal[:6]

    brief["observations"] = observations(brief)
    (DATA / "brief.json").write_text(json.dumps(brief, indent=2) + "\n")
    print(f"Wrote data/brief.json: {len(brief['observations'])} observations, "
          f"history from {brief['history_from']['us']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
