# GRIOS v15 — Daily Editorial Intelligence Standard

## Mission

Publish a concise Persian, decision-first intelligence briefing that identifies the most relevant daily market directions and explains the political, economic, monetary, corporate and geopolitical news affecting each asset class.

## Required daily structure

1. Market regime and one-sentence global capital-flow read.
2. **Daily symbol radar:** a compact list of symbols with directional bias only (bullish / bearish / neutral / wait). No per-symbol entry checklist, trigger, invalidation, stop, target, timeframe or trade-management card.
3. **Market-specific news intelligence**, grouped separately for:
   - FX: central banks, interest-rate expectations, inflation, employment, fiscal policy, elections, currency policy and geopolitical developments affecting currencies.
   - Commodities and energy: supply disruptions, sanctions, OPEC, inventories, production, shipping routes, industrial demand, China and critical-mineral policy.
   - US equities: earnings, guidance, AI/semiconductor capex and monetization, regulation, antitrust, fiscal/tax policy, trade restrictions and sector developments.
   - Crypto: regulation, ETF/market-structure developments, institutional adoption, exchange/custody risks, monetary/liquidity conditions and geopolitical risk.
   - Bonds and rates: central-bank decisions, inflation, labor data, Treasury issuance/auctions, fiscal policy and credit conditions.
4. Cross-market synthesis: explain how material headlines may transmit through rates, USD, liquidity, energy, earnings and risk appetite.
5. Institutional positioning and capital flows only where verified, with publication lag and data limitations disclosed.
6. Megatrends and strategic capital themes as a separate long-horizon watchlist.
7. Economic calendar and key upcoming political, monetary and corporate events.
8. Concise final assessment: where attention should focus and whether the evidence supports action or waiting.

## News selection and editorial discipline

- Prioritize news with a plausible, material transmission channel to a covered market; do not fill sections with generic headlines.
- Cover political, economic, monetary, geopolitical, regulatory and company-specific catalysts when relevant.
- Attribute each item to its publisher and link to the original source.
- Prefer official primary sources for policy, regulation, macro releases and supply data; use established financial journalism for reported developments.
- Distinguish confirmed facts, reported claims and GRIOS interpretation.
- For every selected story, print the actual RSS summary/excerpt as the news brief; never replace the story with a bare URL or generic placeholder.\n- Follow each story with a market-specific transmission analysis: what variable changes, which instruments/sectors are exposed, likely positive/negative/conditional pathways, and what market evidence would confirm the interpretation.\n- A URL is a verification link only; it is not the news content or the analysis.\n- Preserve numeric facts in headlines when they are material; do not suppress a headline merely because it contains prices, percentages or dates.\n- Do not classify generic political stories as relevant to every market. Require a direct transmission channel or explicit market relevance.
- Group the same story under more than one market only when its transmission is genuinely cross-asset.
- If a market has no sufficiently relevant verified news, say so instead of inventing coverage.
- News headlines and RSS excerpts are not represented as full-article research.

## Signal presentation

- Show the symbol and directional bias only, for example: EUR/USD — صعودی, XAU/USD — نزولی, BTC/USD — خنثی.
- Do not publish per-symbol entry conditions, breakout/retest instructions, invalidation levels, targets, stop-losses, risk/reward ratios or timeframe labels.
- Do not fabricate directional signals when market data is stale, incomplete or contradictory.
- A neutral / wait / no-trade outcome is valid and should be explicit.
- Avoid duplicated correlated exposures dominating the shortlist.
- Keep the daily shortlist selective and cross-asset; rank by evidence quality rather than by the magnitude of the latest price move.

## Data and source integrity

- Do not publish routine prices, percentages, raw scores, factor tables or raw observation counts in the Telegram body.
- Never infer institutional flows from price movement or weekly CFTC positioning.
- Never call an ETF proxy an underlying spot or futures contract.
- Do not fabricate consensus, earnings, valuation multiples, release times, ETF flows, order-book data or 13F holdings.
- If data is missing, stale, contradictory or unavailable, disclose the limitation and suppress the related conclusion.
- CFTC Futures Only is weekly positioning, not real-time flow.
- SEC 13F holdings are delayed and partial disclosures, not real-time institutional activity.
- The current synthesis is deterministic and rule-based; RSS summaries/excerpts are not represented as full-text article review. Each story must nevertheless include its available excerpt and an explicit market-specific impact analysis. If a source supplies no excerpt, label that limitation and do not fabricate article details. A future full-text research stage should retrieve permitted article text or official releases and preserve source-level evidence.

## Output limits

- Target 1,800–3,000 Persian characters where news volume permits; prioritize completeness of material market news over an artificial character cap.
- Keep each market's news section to the most material items, normally one or two headlines.
- Avoid market-by-market encyclopedic prose, repetitive explanations and generic bull/base/bear scenarios.
- Keep megatrends separate from today's directional symbol radar unless a current catalyst and market evidence support inclusion.
- If no market has a defensible directional bias, explicitly say that no high-conviction direction is identified and waiting is appropriate.

## Technical implementation

- market_news.py: curated RSS retrieval, topic classification, publisher attribution and evidence metadata.
- daily_narrative_report.py: Persian synthesis, market-specific news grouping and concise symbol radar.
- cftc_context.py: read-only, validated CFTC Futures Only positioning context.
- scanner.py: passes market observations, calendar, news and positioning to the renderer.
- market-pulse/.github/workflows/grios-data-hub-scan.yml: builds contexts and publishes the integrated report once.