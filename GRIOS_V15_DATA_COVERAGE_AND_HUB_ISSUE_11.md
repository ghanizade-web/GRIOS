# GRIOS v15 — Data Coverage & Data Hub Implementation

Date: 2026-11-04
Scope: GitHub Issue #11, Data Coverage and Cloudflare Data Hub.

## Verified starting state

- The GRIOS main branch contains a direct-provider Python scanner, but no executable Cloudflare Worker source or Wrangler configuration.
- The scanner reads crypto from CoinGecko and CoinMarketCap; equities and ETF proxies from OpenBB/Cboe; FX reference history from ECB; energy series from EIA; and macro context from FRED.
- The live acceptance record documents TON as missing from both crypto provider pages and Henry Hub as unavailable from the EIA/OpenBB path.
- The private market-pulse repository currently contains a Twelve Data daily time-series client for FX, XAU/XAG, WTI, crypto and selected equity indices. It does not currently contain a FRED or EIA adapter in the inspected source file. Its API key is a server-side environment variable.
- The connected Supabase project currently reports INACTIVE. Database inspection failed because the database was not accessible. The schema must not be described as applied until the project is active and verified.
- No Cloudflare account/deployment connector is available in this session. Worker deployment and secret binding cannot be claimed complete.

## Implemented in this branch

1. Added an authenticated Cloudflare Worker with:
   - GET /v1/status
   - POST /v1/ingest
   - GET /v1/markets/latest
   - bearer-token authentication, payload size/row limits, schema validation, and sanitized upstream errors.
2. Added a Supabase migration for provider-attributed append-only observations, RLS, restricted grants, indexes, and a latest-observation view.
3. Added a Python Data Hub client using standard-library HTTPS requests; no new Python runtime dependency.
4. Connected scanner output to optional Data Hub ingestion. If URL/token are absent, the scanner reports NOT_CONFIGURED and continues operating against direct providers.
5. Added a JSON coverage report that records requested/received/missing symbols, freshness, feed errors, and unsupported capabilities.
6. Added Worker contract tests and Python coverage/client tests.

## Data coverage model

| Feed | Expected universe | Source | Current limitation |
|---|---|---|---|
| Crypto spot | Configured watchlist | CoinGecko + CoinMarketCap | Provider top-page limits; native asset is now GRAM (formerly TON), with pinned-ID fallback |
| US shares/ETFs | User watchlist | OpenBB/Cboe daily history | Not executable real-time quotes |
| Commodity proxies | User watchlist | OpenBB/Cboe ETF proxies | Proxy exposure, not underlying spot/futures |
| FX reference | User watchlist | ECB | Reference rates, not bid/ask or market depth |
| Energy spot | Brent and Henry Hub | EIA via OpenBB | Henry Hub path has a live OpenBBError |
| Macro | DGS10, DGS2, DTWEXBGS, VIXCLS | FRED via OpenBB | Published observations, not intraday feeds |

The report separately flags as NOT IMPLEMENTED: underlying gold/silver and industrial-metal prices, crypto OHLCV beyond provider snapshots, order-book spread/depth, verified institutional fund flows, dated catalyst feeds, and point-in-time walk-forward calibration.

## Required production activation

1. Restore/activate the existing Supabase project and verify the database is reachable.
2. Apply the migration in this branch and verify the table/view and RLS grants.
3. Deploy the Worker from services/data-hub-worker using Wrangler.
4. Set Worker secrets: GRIOS_INGEST_TOKEN, SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY.
5. Set scanner-side secrets: GRIOS_DATA_HUB_URL and GRIOS_DATA_HUB_TOKEN.
6. Run a live scan with Telegram disabled; verify Worker status, accepted row count, provider provenance, freshness and latest endpoint output.
7. Only then classify the Data Hub as INTEGRATION_VERIFIED or PRODUCTION_VALIDATED.

No secret values belong in GitHub, audit JSON, reports or logs.
