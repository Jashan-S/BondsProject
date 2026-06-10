# Basispoint — Business Plan
*Fixed income intelligence for investors locked out of the terminal.*
*(Working name — rename freely. Last updated: June 2026.)*

---

## 1. The Opportunity

The global bond market is roughly $140 trillion in outstanding debt, larger than the global equity market, yet the retail tooling gap between the two is enormous. An equity investor gets free real-time quotes, screeners, charts, and analyst coverage from a dozen apps. A bond investor gets almost nothing: corporate bond prices are scattered across dealer networks, yield analytics require a Bloomberg terminal (~$28,000/year/seat), and most brokerages show bond inventory with markups baked invisibly into the price.

This opacity is not an accident — it is how fixed income intermediaries earn their spread. Studies of FINRA TRACE data consistently show retail-sized corporate bond trades paying markups of 50–150 basis points versus institutional prints on the same bond, same day. A retail investor buying $25,000 of a corporate bond may silently pay $250–$375 more than the fair price simply because they cannot see the tape.

**The product thesis: we don't sell bonds, we sell sight.** Tools that let a self-directed investor see fair value, compare yields properly, and construct portfolios (ladders, barbells) the way professionals do.

## 2. Who Pays: Retail vs. Institutional (the honest answer)

Institutional investors are *not* the better first market, despite being where the money is. Asset managers, banks, and insurers already pay for Bloomberg, ICE, Refinitiv, and MarketAxess. They require audited data lineage, redistribution licenses, SOC 2 compliance, and procurement cycles measured in quarters. A two-person startup cannot win that sale, and the underlying data licenses needed to serve them cost six to seven figures annually.

The serviceable market is the layer *between* free and Bloomberg:

1. **Self-directed retail investors** (core, launch market): people holding bonds, GICs, T-bills, and bond ETFs in brokerage accounts, especially in the current environment where cash and fixed income yields are meaningful again. Willing to pay $15–$40/month for an edge, same as they pay Seeking Alpha or Morningstar.
2. **Prosumers and finance professionals off-desk**: advisors at small shops, CFA candidates, fintech builders, finance academics. Willing to pay $50–$150/month, especially for API access.
3. **Small RIAs and family offices** (year 2+): too small for a terminal seat per person, big enough to pay $200–$500/month for a team plan. This is the "institutional-lite" path — it captures the higher willingness-to-pay your prof was gesturing at, without competing head-on with Bloomberg.

Strategy: launch on segment 1 to build audience and credibility cheaply, monetize segment 2 with the Pro tier and API, and grow into segment 3 once the product has a track record.

## 3. Product & Tier Structure

The free tier exists to win search traffic and trust; the paid tiers sell workflow tools, not raw data (raw data is commoditized and license-restricted; tools and interpretation are defensible).

| | **Free** | **Pro — $29/mo or $290/yr** | **Desk — $99/mo or $990/yr** |
|---|---|---|---|
| Yield curves (US, Canada) | Daily | Intraday updates | Intraday + historical curve animation |
| Bond screener | 10 results, basic filters | Full screener: rating, sector, duration, YTM, callable | Screener + saved screens + export |
| Fair-value estimator (vs TRACE prints) | — | ✓ | ✓ |
| Ladder & barbell builder | 1 saved portfolio | Unlimited, with reinvestment modeling | Unlimited + multi-account |
| Alerts (yield targets, new issues, downgrades) | — | 10 alerts | Unlimited |
| Weekly market letter | Public archive | Full letter + data appendix | Full letter + data appendix |
| Education library | ✓ | ✓ | ✓ |
| API access | — | — | ✓ (rate-limited) |
| Seats | 1 | 1 | 3 (team plan upsell later) |

Anchoring logic: Free converts readers, Pro is the volume product, Desk exists partly to make Pro look cheap and partly to catch prosumers/RIAs. Annual plans (2 months free) smooth revenue and cut churn.

## 4. Data Sourcing (the make-or-break detail)

This is where most fintech data startups die, so plan it first:

**Free / public sources for MVP (build on these):** FRED (Fed yield curves, spreads, macro series — generous API, redistribution-friendly), US Treasury Fiscal Data API and auction results, Bank of Canada Valet API (GoC yields — important for your Canadian audience), FINRA TRACE end-of-day corporate bond data, MSRB EMMA for munis, SEC EDGAR for issuer filings.

**Licensing caution:** FINRA, MSRB, and exchanges restrict *redistribution* of their data. Displaying derived analytics (fair-value estimates, aggregates, charts) is generally treated differently from rebroadcasting raw quotes, but the line matters legally — budget for a vendor/redistribution agreement review before charging for anything containing third-party data, and read each source's terms of use. Reference data (CUSIPs) is itself licensed by CUSIP Global Services and is notoriously expensive; lean on ISINs/FIGIs (OpenFIGI is free) where possible.

**Later (revenue-funded):** a commercial feed (e.g., ICE, Intercontinental's evaluated pricing, or a smaller vendor like Finnhub/Polygon for what they cover) once MRR justifies the $1–3K/month entry cost.

## 5. Regulatory Posture

You are based in Ontario. Publishing general market data, analytics, and education does **not** require registration, but giving *advice tailored to a person* does (advising registration under Ontario securities law; similar rules under the SEC/state RIA regimes for US users). The product must stay firmly on the publisher side of that line: no personalized recommendations, no "you should buy X," prominent disclaimers, and tools framed as calculators/information. Subscription publishers ("bona fide newsletters") have recognized exemptions in both countries, but get one consultation with a securities lawyer before charging money — it is a few thousand dollars that protects the whole business. Also factor in: terms of service, privacy policy (PIPEDA), and sales tax registration (HST applies to digital subscriptions sold to Canadians).

*(None of this section is legal advice — it is the map of questions to bring to a lawyer.)*

## 6. Go-to-Market

Content is the engine, because bond education has astonishingly weak competition compared to equities. The flywheel: free, genuinely good explainers and data pages ("What is the 2s10s spread and why is it inverted?", "Canada yield curve today", "How bond ladders beat GIC ladders") rank on search → readers join the free tier and weekly letter → a fraction convert to Pro when they hit tool limits. Supplement with: a public X/LinkedIn account posting one chart per day from your own pipeline, Reddit (r/bonds, r/fixedincome, r/PersonalFinanceCanada) where bond questions go chronically unanswered, and a referral month-free program. Your MEng/AI-in-finance angle is a credibility asset — write under your own name.

## 7. Financial Sketch (what the math has to look like)

Assumptions: $29 Pro / $99 Desk, blended ~$33 ARPU, 3–5% free→paid conversion (newsletter-led products commonly hit this), 5% monthly churn early, improving with annual plans.

| Milestone | Free list | Paying subs | MRR | Notes |
|---|---|---|---|---|
| Month 3 (launch) | 500 | 15 | ~$500 | Friends, Reddit, first SEO pages |
| Month 6 | 2,500 | 75 | ~$2,500 | Covers data + infra costs |
| Month 12 | 8,000 | 280 | ~$9,000 | Ramen profitability; consider first paid feed |
| Month 24 | 25,000 | 900 | ~$30,000 | Add team/RIA plan; possible first hire |

Costs are low until you buy data: hosting + DB + email ≈ $50–150/month early, Stripe takes ~3%, the real costs are your time and (later) data licensing and legal. Break-even is roughly 10–20 paying subscribers.

## 8. Competition & Moat

Direct-ish competitors: Finra's own free tools (clunky), BondSavvy (~$365/yr, picks-focused), YCharts/Koyfin (equity-first, fixed income shallow), MarketAxess/Tradeweb (institutional execution, not analytics for individuals). The gap Basispoint targets — retail-priced fixed income *analytics with Canadian + US coverage* — is genuinely thin. The moat is not the data (anyone can hit FRED); it is the accumulated content library, the trust of the audience, proprietary derived datasets (your fair-value model trained on TRACE history is a real asset and a real use of your AI background), and workflow lock-in from saved portfolios and alerts.

## 9. Build Roadmap

**Phase 0 (now, weeks 1–2):** This repo. Static landing page on GitHub Pages, email capture (Buttondown/ConvertKit), publish two cornerstone explainers. Goal: validate that people sign up before writing a backend.

**Phase 1 (weeks 3–8):** Data pipeline (Python: pull FRED + Bank of Canada + TRACE EOD into Postgres, nightly cron), public pages that render live charts (yield curve page, spreads page). Weekly letter starts. Still no auth, no payments.

**Phase 2 (weeks 9–16):** Accounts + Stripe subscriptions, gate the screener and ladder builder behind Pro. Stack suggestion: FastAPI or Next.js backend, Postgres, Stripe Billing, deployed on Railway/Render/Fly. Ship the fair-value estimator as the Pro headline feature.

**Phase 3 (months 5–8):** Alerts engine, API for Desk tier, historical curve explorer, Canadian provincial + corporate coverage. Begin RIA conversations.

**Kill/iterate criteria:** if 1,000 free signups convert at under 1% after a real Pro launch, the willingness-to-pay isn't there — pivot the paid layer (API-first for fintech devs, or B2B reports) before quitting the niche.

## 10. Risks (named, not hidden)

Data licensing challenge from FINRA/MSRB (mitigate: lawyer review, derived analytics only); rate cycle turns and retail interest in bonds fades (mitigate: the audience that arrived for 5% yields still owns the bonds); a big player (Morningstar, Koyfin) goes deep on retail fixed income (mitigate: speed, Canada coverage, community); regulatory drift if content ever sounds like advice (mitigate: editorial policy, disclaimers, legal review); and solo-founder burnout (mitigate: the Phase 0 validation gate exists so you don't build a year of product nobody wants).
