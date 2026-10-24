# GRIOS Opportunity Research Method

## Output contract

Each report should state its as-of time and timezone, data providers, coverage, session/market state, freshness, and any conflicts. Rank research candidates only within an explicit universe and horizon. Include the evidence behind each score, counter-evidence, missing fields, catalysts with source/date, and conditions that would invalidate the thesis. Do not fabricate entry prices, price targets, whale activity, or live status.

## Horizons

| Horizon     | Minimum evidence before ranking                                                                                           | Current GRIOS support                                                        |
| ----------- | ------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| Today / 24h | Fresh quote, 24h move, liquidity/spread, realized volatility/session, near-term calendar                                  | Crypto market snapshot has 24h fields; no complete spread/calendar risk data |
| Week        | 7d history, 24h/7d volume, trend/drawdown, event calendar, market regime                                                  | 7d return available for provider rows when present                           |
| Month       | 30d history, volatility/drawdown, liquidity, valuation/fundamental context, upcoming catalysts                            | 30d return and market-cap/FDV/volume only                                    |
| Year        | 90d/365d total return, drawdown, volatility, relative/inflation-adjusted valuation, audited fundamentals, dated catalysts | Unsupported; return `insufficient_history`                                   |
| Long term   | Multi-year history, audited business/protocol fundamentals, sustainability, regulatory and dilution risks, scenarios      | Unsupported; return `insufficient_history`                                   |

## Score design

- Score components on a 0–100 scale with transparent weights and calculate coverage/confidence separately from the score.
- For short horizons, use horizon-specific momentum, liquidity and market regime plus a dilution-risk penalty when FDV and market capitalization are valid.
- Never treat missing/zero market cap, FDV, volume or history as evidence of low risk. Mark that factor unavailable and lower coverage/confidence.
- A high return by itself is not a high-quality opportunity; examine liquidity, volatility, spread, dilution, drawdown and counter-signals.
- Avoid comparing raw scores across asset classes until each asset class has an explicitly calibrated universe and history. Current scoring only covers crypto.
- Annual and long-term requests must be suppressed until the inputs above exist. The API must return the missing-data explanation rather than a ranked list.

## Derivatives and accumulation claims

- If Velo or Hyperliquid data is later connected, keep venue and instrument type explicit (spot, perpetual, dated future); include observed time, quote currency, and any sampling delay.
- A quiet-accumulation candidate may be flagged for review when price stays near a defined range low while independently sourced spot buy pressure or volume delta rises, open interest grows gradually, funding remains moderate, and liquidation/flow context is consistent.
- Open interest is the sum of both sides' contracts and does not reveal the identity or direction of a buyer on its own. Volume delta, funding and social activity are also proxies, not institutional-flow proof.
- Reserve `SMART MONEY CONFIRMED` for attributable evidence with an identified entity/source and methodology. Otherwise label the finding `EARLY FLOW PROXY` or `WATCH`, include alternative explanations, and state the confirming or invalidating observation.

## “Smart money” evidence ladder

1. **Attributable primary evidence:** filings, issuer/fund disclosures, exchange/ETF flow reports, named institutional holdings, or documented market-position reports.
2. **Methodologically documented on-chain evidence:** entity labels, transfer/flow definitions, confidence and observation window.
3. **Weak proxies:** volume, price impact, open interest, funding, social mentions, or unlabeled large wallets. These may suggest activity but cannot establish who traded or why.

Reports must label level 3 as a proxy, state alternative explanations, and never say “institutions are accumulating” from price/volume alone.

## Free-data operations

- CoinGecko Demo: batch market endpoints and stay within the current 10,000 calls/month allowance; retain attribution and call timestamps. At one poll every 10 minutes, the Worker uses about 4,320 calls/month before retries.
- CoinMarketCap Basic: inspect current quota/credit use because large result sets consume more credits; use as an independent cross-check rather than duplicating every CoinGecko poll. The Worker requests 250 listings; at one poll every 10 minutes, this is about 4,320 successful requests/month before endpoint-specific extra credits and retries.
- TickerLayer Free: reserve within the 3,000 calls/30 days budget and use its MCP only for internal research. Do not publish or re-serve its quotes from a free-plan public API. It is derived/indicative and may differ from exchange prices.
- SEC and CFTC data are for filings and weekly positioning, not intraday quotes. FRED needs a free registered key and must retain observation/vintage dates. DefiLlama public TVL endpoints are useful for supported protocols but not a substitute for token-market liquidity.
- MCP credentials/connectors in Codex do not become Worker bindings. Runtime integrations must be separately provisioned and licensed.

## Report template

1. **As of / sources:** one line with timestamp, timezone, coverage and freshness.
2. **Regime:** 2–3 compact facts.
3. **Candidates:** up to five; horizon, evidence, one counter-signal, confidence/coverage, catalyst and invalidation.
4. **Flows / conflicts:** only material corroboration, data gaps, or changed facts.
5. **Research notice:** no individualized allocation or guaranteed outcomes.

Default to a short daily delta; include only candidates that changed or still meet the evidence bar. Link back to the full method instead of repeating it.
