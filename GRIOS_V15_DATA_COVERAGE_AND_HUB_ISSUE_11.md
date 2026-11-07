# GRIOS v15 — Data Coverage & Supabase Data Hub

**Current status:** Supabase-only architecture, verified 2026-11-07. This document supersedes the earlier Cloudflare Worker deployment plan recorded below in historical commits.

## Active architecture

- Supabase project `ouzayspfyhkhktntonxd`, region `eu-west-1`, status `ACTIVE_HEALTHY`, PostgreSQL 17.6.
- Primary table: `public.grios_market_observations`; latest view: `public.grios_latest_market_observations`.
- Market scanner writes directly to Supabase PostgREST using `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`.
- CFTC context reads directly from the same table.
- SEC 13F ingestion writes directly to Supabase tables/RPCs.
- The private `market-pulse` Twelve Data adapter now writes directly to the same observation table.
- GitHub Actions remains the compute and scheduling layer. The daily schedule remains `0 12 * * *` UTC.
- Cloudflare Worker source, Wrangler configuration, deployment workflow and Worker fallback were removed from active repository code. No Worker URL/token is required.

## Live database verification

Read-only SQL verification on 2026-11-07 returned:
- 1,073 rows
- 40 distinct ingestion runs
- 7 provider labels
- Latest insertion: 2026-11-07 15:52:08 UTC

Provider labels observed: CoinGecko + CoinMarketCap (346 rows), OpenBB Cboe (376), OpenBB ECB (113), OpenBB FRED (100), CFTC (61), OpenBB EIA (50), and EIA (27).

These counts confirm persistence only. They do not imply that every feed is real-time, complete, or suitable for execution.

## Security model

- RLS is enabled on the market observation table.
- Public, anon and authenticated grants are revoked.
- Backend ingestion uses the service-role credential only.
- Never place the service-role key in client code, reports, artifacts or logs.
- The database advisor's informational no-policy findings are consistent with this restricted service-role-only access model; do not add public policies merely to silence those notices.

## Provider coverage and limitations

| Feed | Provider | Semantics / limitations |
|---|---|---|
| Crypto spot | CoinGecko + CoinMarketCap | Provider top-page coverage; identity and freshness validation required |
| US equities / ETFs | OpenBB Cboe | Daily history, not executable real-time quotes |
| Commodity proxies | OpenBB Cboe | ETF proxies, not underlying spot/futures |
| FX reference | OpenBB ECB | Reference rates, not bid/ask or market depth |
| Energy | EIA / OpenBB EIA | Published series, not intraday futures |
| Macro | OpenBB FRED | Published observations, not intraday feeds |
| Futures positioning | CFTC | Weekly aggregate positioning, not transaction-level institutional flow |
| Twelve Data | Private market-pulse adapter | Daily candle history; plan entitlement and session caveats retained |
| SEC 13F | SEC EDGAR + Supabase | Delayed reported holdings, not live positions or proof of manager proprietary capital |

The report separately flags as not implemented: underlying gold/silver and industrial-metal spot/futures coverage, order-book depth, verified institutional fund flows, and point-in-time walk-forward score calibration.

## Operational acceptance

For each production run:
1. Confirm GitHub Actions completed.
2. Confirm the publisher reports `DIRECT_SUPABASE` with a non-zero accepted count when valid data exists.
3. Verify latest rows by `inserted_at`, `run_id`, provider, asset class and source timestamp.
4. Confirm data freshness independently of insertion success.
5. Confirm Telegram publication only when logs explicitly contain `TELEGRAM_PUBLISH: SENT`.

## Cloudflare account boundary

Repository code and active workflows no longer use Cloudflare. Removing repository files does not delete a previously deployed Cloudflare account resource or disconnect an external Cloudflare GitHub App/Workers Builds integration. Those account-level actions require Cloudflare dashboard access and separate verification.
