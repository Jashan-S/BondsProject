#!/usr/bin/env python3
"""
Generate sitemap.xml for the public site.

Runs in the nightly workflow after the data update, so data-driven pages get
a fresh lastmod every market day. Add new pages to PAGES as they ship.

When the permanent brand domain is chosen, change BASE_URL here and in
robots.txt — nothing else needs to move.
"""

from datetime import date
from pathlib import Path

BASE_URL = "https://bondtracker.ca"

# (path, changefreq, priority, data_driven)
PAGES = [
    ("/",                          "weekly", "1.0", True),
    ("/pages/yield-curve.html",    "daily",  "0.9", True),
    ("/pages/2s10s.html",          "daily",  "0.8", True),
    ("/pages/credit-spreads.html", "daily",  "0.8", True),
    ("/pages/corporate-bonds.html","daily",  "0.8", True),
    ("/pages/ladder-builder.html", "weekly", "0.9", False),
    ("/pages/learn/index.html",    "weekly", "0.7", False),
    ("/pages/learn/bond-ladders-vs-gics.html", "monthly", "0.7", False),
    ("/pages/learn/duration.html", "monthly", "0.7", False),
]

STATIC_LASTMOD = "2026-07-09"  # bump when editing non-data page content


def main() -> None:
    today = date.today().isoformat()
    entries = []
    for path, freq, prio, data_driven in PAGES:
        lastmod = today if data_driven else STATIC_LASTMOD
        entries.append(
            f"  <url>\n"
            f"    <loc>{BASE_URL}{path}</loc>\n"
            f"    <lastmod>{lastmod}</lastmod>\n"
            f"    <changefreq>{freq}</changefreq>\n"
            f"    <priority>{prio}</priority>\n"
            f"  </url>"
        )
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(entries)
        + "\n</urlset>\n"
    )
    out = Path(__file__).resolve().parent.parent / "sitemap.xml"
    out.write_text(xml)
    print(f"Wrote {out} with {len(PAGES)} URLs")


if __name__ == "__main__":
    main()