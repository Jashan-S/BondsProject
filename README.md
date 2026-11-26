# Basispoint — public site and data pipeline

The free, public half of the project: market-data pages, the ladder tool, the
education library, and the nightly job that fetches the data. Hosted on GitHub
Pages at bondtracker.ca. The signed-in app is a separate, private repo.

## What runs by itself

`.github/workflows/update-data.yml` runs at 22:30 UTC on weekdays (GitHub
usually starts it a few hours late) and commits fresh files under `data/`:

| Step | Script | Writes |
|---|---|---|
| Government yields | `scripts/fetch_data.py` | `data/market.json` |
| Daily history | `scripts/fetch_history.py` | `data/history/*-<year>.json` |
| FINRA corporate statistics | `scripts/fetch_trace.py` | `data/corporates.json` |
| Sitemap | `scripts/build_sitemap.py` | `sitemap.xml` |
| Staleness check | `scripts/check_freshness.py` | fails the run if data is old |

Everything under `data/` and `sitemap.xml` belongs to that job. Never edit
them by hand, and `git pull` before every session.

Repo secrets used: `FRED_API_KEY`, `FINRA_API_CLIENT_ID`,
`FINRA_API_CLIENT_SECRET`.

## The one settings file

`assets/config.js` switches three things on. Leave a value as `""` to keep it
off.

| Setting | What it does |
|---|---|
| `buttondownUser` | Makes the email form subscribe people to your Buttondown list |
| `appUrl` | Points "Start free", "Choose Pro" and "Sign in" at the app |
| `goatcounterCode` | Loads cookie-free page statistics |

## Data sources and their conditions

| Source | Used for | Condition |
|---|---|---|
| FRED API (Federal Reserve H.15) | US Treasury yields | Footer notice and link to FRED's terms on every page; a privacy policy |
| Bank of Canada Valet | Canadian yields | Attribution; if sold, say the data is free at the Bank |
| FINRA Query API | Corporate market statistics | Non-commercial only, free, FINRA named as owner; never part of a paid plan |
| ICE BofA indices (via FRED) | Not shown | Copyrighted; publishing needs ICE's written permission. `INCLUDE_ICE_SPREADS=1` re-enables the fetch only if you obtain it |

## Pages

```
index.html                      Home, pricing, email form
pages/yield-curve.html          US and Canada curves, daily changes, 10Y history
pages/2s10s.html                2s10s spread with history
pages/credit-spreads.html       Explainer; links to FRED for index levels
pages/corporate-bonds.html      FINRA breadth and activity (free)
pages/ladder-builder.html       Free ladder calculator
pages/learn/                    Education library
pages/terms.html, privacy.html  DRAFTS — fill the [brackets], then legal review
404.html
assets/style.css, charts.js     Shared design and charts
assets/config.js, site.js       Settings and the code that applies them
```

To add a page: put it in `pages/`, load `assets/style.css`, end the body with
the two `config.js` / `site.js` script tags, and add it to the list in
`scripts/build_sitemap.py`.
