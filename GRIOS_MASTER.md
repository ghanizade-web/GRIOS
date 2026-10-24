# GRIOS — Master Project Context

_Last reviewed: 2026-10-24_

## Mission

GRIOS is intended to be a Persian-first, command-driven market research terminal for crypto and, over time, forex, equities, commodities and macro markets. It should turn current, timestamped evidence into ranked research candidates for user-selected horizons. It must state source, freshness, coverage, uncertainty and counter-evidence, and must never invent data or claim certainty.

The user's recurring use cases include `/start`, `/menu`, `/trades`, `/alpha`, `/pumpfinder`, `/report`, market scans, a CIO-style summary, portfolio views, and smart-money/capital-flow research. The desired PumpFinder evolution is from momentum chasing toward early-move research: detect quiet changes in spot/perpetual volume, volume delta, open interest, funding, liquidations and spot/perp mix, then confirm them with flow, tokenomics and catalysts. A cross-market opportunity scan should distinguish an observed fact from an inference and a hypothesis.

## Current code state

- `services/data-hub-worker/` is the Cloudflare Worker data hub.
- CoinGecko and CoinMarketCap connectors ingest normalized crypto-market data into Supabase on the configured schedule.
- Codex hourly market briefs can query the connected TickerLayer MCP for covered cross-market prices/history, Token Terminal MCP for crypto protocol fundamentals, and Stocktwits MCP for retail sentiment. These MCP connections do not automatically become Cloudflare Worker integrations; the recurring Codex brief is the current way to use them without copying credentials or violating provider terms.
- The `latest_market_snapshots` view feeds `/v1/markets/latest` and the deterministic research council at `/v1/intelligence`.
- `/v1/status` reports provider health and marks observations stale after 15 minutes.
- `/v1/intelligence` and `/v1/opportunities` suppress candidate rankings when no latest asset observation is within the same 15-minute window; coverage includes stale-record count, threshold, and age of the freshest usable record.
- `/v1/opportunities?horizon=day|week|month|year|long` is being added. Current stored history supports 24h/7d/30d only. Year and long horizons must return `insufficient_history` until longer history and fundamental/catalyst evidence exist.
- `apps/opportunity_scanner/` is a local Python/OpenBB V5 research prototype: GRIOS crypto snapshots plus Cboe daily US equity history, ECB reference rates, EIA Brent/Henry Hub published series, FRED macro context, a Telegram-format text file, and a local SQLite idea/checkpoint journal. It is not a deployed multi-asset feed, has no live FX or underlying metal prices, and emits WATCH-only technical heuristics pending catalyst/fundamental/flow integrations and validation.
- `artifacts/grios-terminal/` is the React terminal. Cloudflare SPA build wiring exists locally but a full production build has not yet succeeded in this environment.
- `supabase/migrations/20260912000000_create_data_hub.sql` defines provider, asset, run, snapshot tables, the latest-snapshot view and restrictive client-role access.
- The deterministic “council” currently has momentum, liquidity, FDV dilution and market-regime factors. It is not a live multi-LLM council and does not make personalized buy/sell decisions.
- Prior design discussions selected Velo as a potential derivatives/microstructure source and Hyperliquid as another live market-data source. The architecture should normalize their observations into separately attributable source rows. Rising open interest or volume delta alone must never be called institutional accumulation or smart-money confirmation.
- The current Worker source list contains only CoinGecko and CoinMarketCap. There is no verified Velo or Hyperliquid connector in this codebase yet.
- On 2026-10-13, live Codex MCP checks succeeded for CoinGecko, CoinMarketCap, TickerLayer, Stocktwits, and Token Terminal. These are research-time connections; none becomes a Worker credential or runtime connector automatically. The tested TickerLayer account did not cover gold, US indices, or US Treasury yields.
- On 2026-10-24, OpenBB's public README, V5 documentation, release page and package metadata were reviewed. The local `apps/opportunity_scanner/` MVP uses OpenBB V5 provider packages only where documented; it does not imply that OpenBB itself supplies live data or a complete crypto/FX/metal feed. The scanner remains unconfigured and unrun until its data-hub URL and EIA/FRED keys are provided locally.
- GitHub continuity check on 2026-10-24: local `main` is eight commits ahead of `origin/main` and has additional staged/unstaged/untracked project files. The connected GitHub app returned no repositories for the expected owner and direct file reads returned 404. Do not push or replace remote content until the repository connection/branch is reconciled and the local changes are reviewed. The Worker build/deployment limitation is still unresolved: the prior build log records missing macOS ARM64 optional esbuild/Rollup packages; the lockfile contains platform entries, but installation/build/deployment has not been reverified. No Cloudflare dashboard tab or connector was available in the current session to confirm deployment or bindings.

## Storage decision and free-tier limits

- Keep the existing Supabase Postgres project for now. The organization and project were verified on the Free plan and `ACTIVE_HEALTHY`; the database measured about 11 MB on 2026-10-13, well below the documented 500 MB/project database quota. Its relational schema and migrations are in place, and a Supabase PostgREST adapter exists in Worker source. Replacing it now adds migration risk without removing all free-tier limits.
- Supabase Free is not unlimited: current published limits include 500 MB database size/project, 5 GB egress, two active projects, and automatic pausing after low activity for a week. Automatic database backups are not included. The configured 10-minute Worker ingestion should generate regular activity once deployed, but this must be verified in production. Keep versioned schema migrations and a separate tested database export; GitHub source archives do not back up live database rows.
- Cloudflare D1 is a plausible future fit because it runs next to the Worker and avoids Supabase's inactivity pause, but it is not unlimited either: the current Workers Free allowance is 5 GB total storage, 5 million rows read/day, and 100,000 rows written/day. At the configured 10-minute schedule and 250 assets from each of two sources, raw snapshot inserts alone could reach about 72,000 rows/day; indexes, audit rows, and journal writes add load. This is a theoretical maximum, not measured usage. D1 would still require PostgreSQL-to-SQLite migration and runtime changes before it could replace Supabase safely.
- The Worker poll schedule is set to every 10 minutes to leave free API quota headroom while staying inside the 15-minute freshness gate. At 250 returned assets per source each cycle, this is about 4,320 requests/month per provider; CoinMarketCap's additional row-based credit cost must still be watched in its account usage dashboard. A missed or failed poll remains visible as stale/degraded data, not silently substituted.
- Live connector responses are not automatically trustworthy just because calls succeed. The 2026-10-13 CoinGecko and CoinMarketCap global-market change figures differed materially, and the CoinMarketCap metrics response contained internally inconsistent volume fields. Preserve each provider's timestamp and mark cross-source conflicts; validate metric semantics before scoring or persisting.

## Data-source map

| Source                                           | Intended use                                                                                            | Free/connection notes                                                                                                    | Limits and handling                                                                                                                                                                                  |
| ------------------------------------------------ | ------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| CoinGecko API/MCP                                | Crypto market cap, volume, returns, rankings, trend/news context                                        | Demo API is free with a key; connected MCP is available in Codex                                                         | Per current official pricing, Demo allows 100 calls/min and 10,000/month. Attribute and label freshness.                                                                                             |
| CoinMarketCap API/MCP                            | Independent crypto cross-check, global metrics, news/narratives                                         | Basic API is free with an account; connected MCP available                                                               | Current official FAQ lists 15,000 monthly credits; credit use depends on rows returned. Keep the key secret.                                                                                         |
| TickerLayer MCP/API                              | Quotes, history, market hours for covered equities, FX and crypto; commodities coverage depends on plan | User has enabled the connector. Current free plan: 3,000 REST calls per 30 days; internal research and MCP use permitted | Free plan excludes commercial display and redistribution. Use for private research in Codex, not as a public Worker data feed. Data is derived, may be delayed/inaccurate, and is not exchange data. |
| Stocktwits                                       | Social activity/sentiment context for named candidates                                                  | Connector available in Codex                                                                                             | Treat social signals as noisy and never as proof of institutional buying.                                                                                                                            |
| DefiLlama public API                             | Crypto protocol/chain TVL context                                                                       | Public free endpoints, no key for basic TVL endpoints                                                                    | Use only for supported DeFi fundamentals; confirm terms and timestamp; do not infer token price targets from TVL alone.                                                                              |
| SEC EDGAR APIs                                   | US issuer submissions and company facts                                                                 | Public REST APIs do not require API keys                                                                                 | Fundamentals/filings, not live quotes. Cite filing date and reporting period; obey SEC fair-access/User-Agent requirements.                                                                          |
| CFTC Commitments of Traders                      | Weekly futures positioning, including relevant commodity and financial contracts                        | Public reporting API/data                                                                                                | Report date differs from release date; positions are aggregate and delayed, not proof of a specific institution's activity.                                                                          |
| FRED/ALFRED                                      | Macroeconomic series and historical vintages                                                            | Free account/key required                                                                                                | Not an intraday feed. Preserve observation date and release/vintage to avoid look-ahead bias.                                                                                                        |
| Token Terminal MCP                            | Protocol-level fees/revenue, usage, TVL, supply and valuation context                                   | Connected in Codex; coverage and per-query limits apply                                                                  | Use for crypto protocol fundamentals; keep daily observation dates and distinguish fees from protocol revenue. MCP connection is not a Worker API credential.                                      |
| Stocktwits MCP                                | Equities/crypto retail attention and sentiment context                                                   | Connected in Codex                                                                                                       | Noisy retail sentiment only; never treat as institutional flow or standalone trade confirmation.                                           |
| Velo (planned)                                    | Perpetual microstructure: volume delta, open interest, funding, liquidations, spot/perp ratios          | Mentioned in prior design discussions; current API/MCP entitlement and accessible fields must be verified                 | Treat these as derivatives-market proxies. OI does not identify who opened positions; confirm with independent flows and primary disclosures.                                                        |
| Hyperliquid (planned)                             | Venue-specific live prices, liquidity and derivatives activity                                           | User supplied access context in an earlier project chat; current connector and credential status are not verified here    | No credential is stored in this project. Use public endpoints where sufficient or a server-side secret; do not claim global whale/institutional flow from one venue.                                   |

The MCP connectors available to Codex are not automatically callable from Cloudflare Workers. A Worker integration requires a separately supported API, server-side secret, documented license, and quota budget. Do not copy connector secrets into Git or frontend code.

Provider references (check current plans/terms before deployment): [CoinGecko pricing](https://www.coingecko.com/en/api/pricing), [CoinMarketCap API FAQ](https://coinmarketcap.com/api/faq/), [TickerLayer pricing and usage rights](https://tickerlayer.com/pricing), [TickerLayer API docs](https://tickerlayer.com/docs), [DefiLlama API docs](https://api-docs.defillama.com/), [SEC EDGAR APIs](https://www.sec.gov/search-filings/edgar-application-programming-interfaces), [CFTC COT API help](https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm), and [FRED API terms](https://fred.stlouisfed.org/docs/api/terms_of_use.html).

## Opportunity horizons and evidence requirements

- **Today / day-trade research:** current quote and timestamp, session state, spread/liquidity, 24h move, volatility and nearby event risk. A static quote alone is not enough to propose an entry or target.
- **This week:** 7d price history, volume/liquidity, market regime, positioning where available, event calendar and a falsifiable thesis.
- **This month / short-to-medium term:** 30d or longer history, volatility/drawdown, relative strength, catalyst schedule, valuation/fundamental context where available.
- **This year / long term:** at least 90d/365d history, drawdowns and volatility, inflation-adjusted or peer-relative valuation as appropriate, audited/primary-source fundamentals, documented catalysts and risks. Until those fields exist, return `insufficient_history` rather than a ranked opportunity.

“Institutions are quietly accumulating” requires named, dated and attributable evidence (for example a filing, fund flow series, public on-chain labels with methodology, or exchange/issuer report). Price/volume spikes, social posts or an unlabeled wallet do not establish institutional accumulation. Use language such as “consistent with” only when supported and list alternative explanations.

“Near a low” requires a stated reference window and metric (e.g., 1y percentile or drawdown from high), not a low nominal unit price. Recommendations should present a watchlist and scenarios with invalidation conditions, not guarantees or personalized allocations.

## Operating principles

1. Every data point carries provider, instrument, currency, market session, observed timestamp and freshness class.
2. Cross-check important signals with a genuinely independent source; identify conflicts rather than averaging away discrepancies.
3. Keep missing fields missing. A zero or unavailable value must not be treated as a low-risk value.
4. Use source-specific rate-limit budgets, caching, backoff on 429/5xx, and graceful provider degradation.
5. Do not scrape websites where an API/MCP exists or bypass a provider's plan/license.
6. Never commit API keys, access tokens, account credentials, raw connector responses that may contain credentials, or personal data.
7. Daily reports cover a watchlist of evidence-backed candidates, not every tradable instrument worldwide; coverage gaps and delayed markets must be explicit.

## Command menu and token budget

Keep user-facing commands short and Persian-first. In the current web terminal, only overview (`/`), crypto alpha (`/alpha`) and CIO brief (`/ai`) are implemented. `/start`, `/menu`, `/trades`, `/pumpfinder`, `/report`, portfolio, and multi-market scans are retained as product design commands only until actual routes/actions exist. Do not advertise a planned command as live.

Low-token operating defaults for Chat and Work:

- Load this master context plus only the relevant module note; do not paste the whole history into every turn.
- For follow-up requests, return changes/new facts first and link to prior context rather than restating it.
- Daily reports should be a compact delta: regime, up to five candidates, the strongest counter-evidence, stale/missing feeds, and source timestamps. Expand only when asked.
- Batch provider requests, request only fields/horizons needed, cache within provider terms, and avoid polling unchanged data.
- Use concise machine-readable summaries between modules; keep raw payloads and long market-history arrays out of LLM prompts.
- Ask for deeper research only when a candidate clears the first-stage quality/liquidity filter; otherwise state that nothing meets the evidence threshold.
- After code or product changes, append a dated, concise entry to `CHANGELOG_CONTEXT.md` and update the relevant source-of-truth section here. Never dump whole chat transcripts or key values into the history.

Scheduling boundary: the Codex heartbeat can wake this thread for a daily research pass, but it cannot post a new message into the same ChatGPT conversation autonomously. Do not describe the daily report as auto-published to Chat unless a supported same-thread publishing mechanism is added and verified. The user's requested report time is 09:00 Asia/Tehran.

## What is not yet complete

- A licensed, server-side multi-asset API for GRIOS itself (the Codex MCP connection does not flow into the deployed Worker); Velo and Hyperliquid remain planned/unverified.
- Production use of the OpenBB scanner: provider credentials, working data entitlements, metal/futures feeds, catalyst/fundamental joins, and scoring backtest/validation have not been configured or verified.
- Cross-asset instrument registry and normalized price/history schema.
- 90d/365d history, audited fundamentals, event/catalyst feeds, and backtesting without look-ahead bias.
- A reproducible evaluation of ranking quality and false-positive rates.
- A real LLM provider configuration if natural-language interpretation is desired; current council is deterministic.
- Authenticated production deployment, connected Worker secrets, and successful live Worker/frontend deployment have not been verified. Supabase migrations are applied and verified on the currently active Free project.

## Backup scope

`PROJECT_HISTORY.md` is a curated, sanitized project decision log reconstructed from the GRIOS-related Codex thread summaries and repository history accessible on 2026-10-13. It is not a verbatim export of all ChatGPT/Work conversations, uploaded files, provider data or hidden memory. Raw conversations are intentionally excluded because they may contain API credentials, personal data and attachments; secrets must be rotated if exposed previously and must never be copied into this repository.
