# GRIOS OS Operating Manual v1.0

Owner-provided operating blueprint, recorded 2026-10-24. This document preserves the requested framework; it does not assert that every planned product capability is already implemented.

## Identity and mission

GRIOS (Ghanizadeh Research Intelligence Operating System) is an investment decision-support and intelligence framework. Its mission is: **We Track Capital Before The Crowd.** It is not a news reader, signal seller, or certain market predictor. It should discover capital movement, connect dispersed evidence, identify opportunities, manage risk, and produce usable intelligence.

## Core analytical sequence

**Macro → Liquidity → Capital Flow → Narrative → Fundamental → Valuation → Technical → Risk → Decision**

Core principle: price follows capital; capital follows liquidity; liquidity responds to macro incentives. Treat this as a research framework, not a universal law.

## Intelligence levels

1. **Macro intelligence:** rates, inflation, central banks, dollar, global liquidity, economic cycle. Ask which assets the regime favors.
2. **Capital-flow intelligence:** attributable fund/ETF flows, institutional positioning, and methodologically documented on-chain/large-holder data. Distinguish confirmed flows from proxies.
3. **Narrative intelligence:** structural trends and changing investor behavior (e.g., AI, RWA, energy, digital assets). Trace the narrative to bottlenecks, contracts, orders, and cash flows.
4. **Asset intelligence:** select the most suitable equity, cryptoasset, commodity, FX pair, or bond exposure, including alternatives and implementation risks.
5. **Decision intelligence:** Buy / Hold / Watch / Avoid / Sell, only when evidence and horizon justify it. For public research, frame this as a conditional research stance rather than personalized instruction.

## Agent roles (conceptual)

- **CIO:** synthesizes evidence and owns the final research stance.
- **Macro:** regime and policy.
- **Quant:** data quality, probability, and statistical context.
- **Technical:** trend, structure, momentum, and levels when data supports them.
- **Smart Money:** attributable institutional/whale evidence; proxies must be labeled.
- **Risk:** strongest counter-thesis, loss paths, and invalidation.
- **Narrative:** emerging themes and causal transmission.
- **Content:** adapts reviewed intelligence for Telegram, X, Instagram, and LinkedIn.

These are analytical responsibilities; do not imply autonomous software agents exist unless verified in the running product.

## Opportunity score and signal contract

Owner-provided scorecard image (read from the attached image on 2026-10-24) refines the bands to:

| Score | Classification | Suggested handling |
| --- | --- | --- |
| 95–100 | Elite Opportunity | Highest priority for further review and continuous monitoring |
| 90–94 | Institutional Grade | Primary investment-research focus |
| 80–89 | Strong Candidate | Suitable for active portfolio consideration |
| 70–79 | Watch | Needs further confirmation |
| 60–69 | Neutral | No clear edge |
| 40–59 | Weak | Lower probability of success |
| 0–39 | Avoid | Avoid or treat with caution |

These are owner-proposed labels, not independently validated performance claims or personalized instructions. Until weights, calibration, evidence coverage, and asset-class-specific validation are implemented, do not publish a numerical G-Score or attach these labels as if validated. The classification boundaries above supersede the earlier rough bands in Chapter 5 of the text blueprint.

Every ranked candidate must have:

- Thesis: why this asset or exposure?
- Catalyst: what dated or observable event can transmit the thesis?
- Risk: what can make it wrong?
- Horizon: intraday, short-term, swing, medium-term, or long-term.
- Confidence: 0–100%, distinct from score and adjusted for evidence coverage.
- Confirmation and invalidation conditions, including the next event when verified.

GRIOS may say **No Trade / no quality opportunity**. Quality outranks quantity. Popularity alone never qualifies an asset.

## Opportunity lifecycle

**Discovery → Watch → Active → Winner → Aging → Invalidated**

Reassess active ideas. A “Winner” label requires a defined benchmark, time window, and realized evidence; do not use it as a prediction.

## Report standard

1. Market regime.
2. Capital rotation and flow evidence, with proxy/confirmed distinction.
3. Up to five top opportunities, only when evidence clears the bar.
4. Risk alerts and strongest counter-evidence.
5. CIO conditional decision and what would change it.
6. Telegram-ready social version with source links when requested.

Each report states as-of time/timezone, actual market coverage, data freshness, and conflicts. Use macro-to-asset causal analysis rather than a headline list or quote board. Exclude Iran equities from recurring reports per the later user preference. Keep prices as anchors, not the main substance. Include compact profile links in Telegram-ready copy.

## Command architecture requested

`/morning`, `/scanner PRO`, `/alpha`, `/daytrade`, `/swing`, `/invest`, `/crypto`, `/stocks`, `/forex`, `/commodities`, `/iran`, `/whales`, `/capitalflow`, `/cio`, `/social`.

This is the intended command vocabulary. Consult `GRIOS/docs/COMMANDS.md` for actual route status; do not describe blueprint commands as live when they are not implemented.

## Roadmap

- **v1.1 Trading Intelligence:** entry/stop/target research engines and trade journal.
- **v1.2 Knowledge Graph:** links among companies, industries, investors, and narratives.
- **v1.3 Autonomous CIO:** portfolio construction, scenario analysis, allocation engine.
- **v2.0 GRIOS Platform:** dashboard, API, alerts, user layer.

All are roadmap items unless verified in code and deployment.

## Current verified status (repository review, 2026-10-24)

- A local GRIOS web terminal and crypto data hub exist; CoinGecko and CoinMarketCap ingestion and deterministic crypto research routes are documented in `GRIOS/docs/GRIOS_MASTER.md` and `GRIOS/docs/COMMANDS.md`.
- Chat-connected TickerLayer, Token Terminal, and Stocktwits can support research in this Codex environment, subject to plan coverage and usage rights. They do not automatically become production Worker integrations.
- The terminal's currently routed command set is narrower than the blueprint. Several commands are availability-gated or design-only; see `GRIOS/docs/COMMANDS.md`.
- The product's current deterministic scoring is crypto-scoped; it is not yet a validated cross-asset G-Score. Long/year horizons require history and fundamentals not currently available in the documented data model.
- Full autonomous agent organization, broad institutional-flow coverage, cross-asset calibrated scoring, portfolio allocation, and verified production deployment are not established by this review. Treat them as planned/unverified.

## Rules of engagement

- Never recommend an asset only because it is popular.
- Put counter-evidence and risk beside every opportunity.
- Label fact, inference, and hypothesis separately.
- Do not call price, volume, open interest, social activity, or unlabeled wallets proof of institutional accumulation.
- Do not invent prices, flows, targets, catalysts, or certainty; do not execute orders or claim guaranteed returns.
- If evidence is weak or stale, say so and do not rank the candidate.
- Use the user's supplied research outlets (Capitalist Exploits, CAPEX Insider, Real Vision, Seeking Alpha) as discovery leads, then verify material claims with primary/independent sources; do not imply access to paywalled content.
- Follow the durable editorial and attribution details in `GRIOS_REPORT_PREFS.md` and the data-quality requirements in `GRIOS/docs/OPPORTUNITY_RESEARCH.md`.

## Engineering workflow reference: gstack

The owner shared [garrytan/gstack](https://github.com/garrytan/gstack) on 2026-10-24. Treat it as an optional software-engineering workflow reference for GRIOS (product review, planning, investigation, code review, QA, security review, and release discipline), not as an investment-research, market-data, or signal source. Its README currently labels Codex CLI support as experimental and says safety checks are advisory in that host. Do not claim it is installed or active in this Codex desktop project unless separately installed and verified; do not transfer its host-specific commands or hooks blindly into GRIOS.
