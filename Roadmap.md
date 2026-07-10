# Basispoint / bondtracker.ca — Build Roadmap

From current state to a fully functioning paid product. Each phase ends with a
"done means" test — we don't advance until it passes. Order matters: audience
and data are built before the app, the app before payments, payments before
launch. Timelines assume part-time work alongside your MEng.

**Current state (done):** Landing page + custom domain + HTTPS. Nightly
pipeline (FRED + Bank of Canada) writing market.json and daily history.
Yield-curve SEO page with live charts. Repo hygiene, secrets, workflows all
working.

---

## Phase 1.6 — Complete the free public site (1–2 weeks)

The goal: every page, button, and link on the public site works, the site is
discoverable, and the audience engine is on.

**Build (Claude):**
1. `pages/2s10s.html` — the recession-watch page: 2s10s spread history chart,
   what inversion means, current reading vs history.
2. `pages/credit-spreads.html` — IG/HY option-adjusted spreads with history,
   what spreads say about risk appetite.
3. First two education articles in `pages/learn/` — topics chosen from your
   keyword research (candidates: bond ladders vs GICs, how to read bond
   quotes, duration explained, T-bill ladders).
4. Site plumbing: `sitemap.xml` (updated by the nightly workflow),
   `robots.txt`, favicon, Open Graph/social preview tags, custom 404 page.
5. Analytics: GoatCounter or Plausible snippet (privacy-friendly; no cookie
   banner needed).

**Configure (you):**
- Buttondown account + replace the form action → working email capture.
- Google Search Console: verify domain, submit sitemap.
- First weekly letter drafted and sent (even to 5 subscribers — the habit is
  the point).

**Done means:** every nav link resolves to a real page; the email form
delivers a confirmation email; GSC shows pages indexed; analytics records
visits.

---

## Phase 2 — Corporate bond data layer (2–3 weeks)

The fuel for everything paid. No user accounts yet — this is pipeline + one
public page + one private analysis.

**Build:**
1. `scripts/fetch_trace.py` — download FINRA TRACE end-of-day corporate bond
   files, compute *derived aggregates only*: median yield/spread by rating
   bucket and sector, trade-count and volume stats, retail-vs-institutional
   size-bucket price gaps.
2. `data/corporates.json` + history — nightly, same pattern as yields.
3. `pages/corporate-bonds.html` — public aggregate dashboard (the teaser for
   the paid screener).
4. Fair-value model prototype — offline notebook first: given a bond's recent
   institutional prints, estimate fair retail price. This is the Pro tier's
   headline feature and your AI-in-finance background applied for real.

**Checkpoint (you, before Phase 4):** one consultation with a securities
lawyer covering (a) TRACE/MSRB data redistribution and derived-analytics
posture, (b) Ontario publisher exemption + US users, (c) ToS/privacy review.
Budget ~$1–2K. Blocks charging money, not building.

**Done means:** nightly corporates.json committing; public corporate page
live; fair-value prototype produces sane estimates on known bonds.

---

## Phase 3 — The app: accounts and tools (3–5 weeks)

The paid product, built free-first. Separate Next.js codebase deployed on
Vercel at `app.bondtracker.ca`. The static site stays the marketing front
door.

**Build order (each step ships something usable):**
1. Scaffold: Next.js + Tailwind, deployed to Vercel, subdomain DNS (one more
   CNAME in Cloudflare — grey cloud again).
2. Database: Neon Postgres + Prisma. Tables: users, subscriptions, bonds,
   saved_screens, portfolios, alerts. Pipeline dual-writes: JSON for the
   public site, Postgres for the app.
3. Auth: Clerk (email + Google sign-in). Free accounts exist from day one.
4. Tool 1 — Screener: filter corporates by yield/rating-bucket/sector/
   maturity. Free tier: 10 results; full results flagged "Pro" (gate exists
   before billing does).
5. Tool 2 — Ladder builder: pick amount + maturities → cash-flow schedule,
   reinvestment modeling. Free: 1 saved ladder.
6. Tool 3 — Fair-value check: productize the Phase 2 model.
7. Landing page buttons rewire: "Start free" → app sign-up; pricing buttons →
   app with plan preselected.

**Done means:** a stranger can sign up free, screen bonds, build and save a
ladder; Pro features visibly gated; data fresh nightly.

---

## Phase 4 — Payments (1–2 weeks + legal/banking lead time)

Deliberately last — by now there are free users to convert and something
worth paying for.

**Configure (you, has lead time — start paperwork during Phase 3):**
- Business structure decision (sole proprietorship vs incorporating —
  discuss with an accountant; affects Stripe setup and taxes).
- Business bank account; Stripe account with identity verification.
- HST registration timing (mandatory at $30K revenue; registering earlier
  lets you claim input credits — accountant question).
- Legal checkpoint from Phase 2 cleared; ToS + privacy published.

**Build:**
1. Stripe products: Pro $29/mo · $290/yr, Desk $99/mo · $990/yr.
2. Stripe Checkout for upgrade, Customer Portal for cancel/card changes
   (never build billing UI yourself).
3. Webhooks → subscriptions table; middleware gates Pro/Desk features off
   subscription status.
4. Dunning defaults + email receipts on; test end-to-end in Stripe test mode,
   then one real $29 charge (your own card) before opening it up.

**Done means:** test-mode user can upgrade, access opens instantly, cancel
downgrades at period end; a real charge settles into the business account.

---

## Phase 5 — Launch and the growth loop (ongoing)

1. Founding-member pre-launch to the email list: first 50 Pro subscribers at
   $19/mo locked for life. This is the real demand test.
2. Public launch: Reddit (r/bonds, r/fixedincome, r/PersonalFinanceCanada —
   follow each sub's self-promo rules), Hacker News Show HN, X/LinkedIn.
3. Alerts engine (yield targets, downgrade watch) — the retention feature.
4. Desk-tier API (read-only, keyed, rate-limited).
5. Weekly letter → the content flywheel from the business plan, forever.

**Metrics that decide everything:** email-list growth, free→paid conversion
(healthy: 3–5%), monthly churn (<5–7%), MRR. If conversion is <1% after a
real launch, revisit pricing/positioning before building more features.

---

## Standing rules

- Pull before every session (`git pull`); the bot commits nightly.
- `data/` is bot-owned; never hand-edit.
- New pages import `assets/style.css` + `assets/charts.js`; no copy-paste.
- Nothing that looks like personalized investment advice, anywhere, ever.
- Brand name decision (bondtracker.ca is scaffolding) must land before
  Phase 5 launch; earlier is better for SEO accrual.