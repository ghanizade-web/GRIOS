# GRIOS v15 — Supabase-Only Data Hub Architecture

**Decision date:** 2026-11-07  
**Status:** Migration in progress; database and direct-ingestion path verified.

## Architecture decision

Supabase is the only GRIOS Data Hub and persistent backend. Cloudflare Worker, Wrangler deployment, Worker bearer tokens, and Worker URLs are deprecated and must not be used by any active workflow.

GitHub Actions remains the scheduled compute/orchestration layer. It runs the Python collectors and report generation, then writes normalized observations directly to Supabase. The existing daily schedule remains unchanged (12:00 UTC / 15:30 Asia/Tehran).

## Verified Supabase project

- Project ref: `ouzayspfyhkhktntonxd`
- Region: `eu-west-1`
- Database: PostgreSQL 17.6
- Project status at verification: `ACTIVE_HEALTHY`
- Primary observation table: `public.grios_market_observations`
- Latest observation view: `public.grios_latest_market_observations`
- 13F persistence: `grios_13f_snapshots`, `grios_13f_snapshot_filings`, `grios_13f_snapshot_holdings` and service-role-only RPC functions
- Paper journal: Supabase-backed ideas/evaluations tables

### Live database evidence (2026-11-07)

A read-only query returned 953 market-observation rows, 38 distinct ingestion runs, and 7 provider labels. The newest row was inserted at 2026-11-07 15:05:53 UTC.

Provider coverage observed in the table:
- CoinGecko + CoinMarketCap: 318 rows
- OpenBB Cboe: 310 rows across equity ETF and commodity proxy classes
- OpenBB ECB: 99 rows
- OpenBB FRED: 92 rows
- CFTC: 61 rows
- OpenBB EIA: 46 rows
- EIA: 27 rows

These counts establish persisted observations, not that every provider is real-time or every market universe is complete. Each record retains provider, feed class, instrument, observation timestamp, source date, caveat, payload and source revision.

## Active ingestion path

1. GitHub Actions starts the scheduled or manually requested Python workflow.
2. Provider adapters collect and validate market data.
3. `data_coverage.py` serializes observations and posts batches directly to:
   `/rest/v1/grios_market_observations?on_conflict=run_id,asset_key,provider`.
4. The Supabase PostgREST API persists rows in PostgreSQL.
5. Reporting and CFTC context readers query Supabase directly.
6. Telegram publication remains a separate report-delivery step.

The Twelve Data adapter in the private `market-pulse` repository is being migrated to the same direct Supabase table; it must not call a Worker endpoint.

## Security model

- RLS is enabled on the market-observation table.
- Table and view access is revoked from `public`, `anon`, and `authenticated`.
- Server-side ingestion uses `SUPABASE_SERVICE_ROLE_KEY`; it must never be exposed in browser, desktop client, reports, artifacts, or logs.
- Required backend configuration is `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`.
- No Worker URL, Worker token, Cloudflare API token, or Cloudflare account ID is required by the active GRIOS pipeline.
- Security Advisor currently reports informational `RLS Enabled No Policy` notices for restricted tables. This is consistent with the intended service-role-only access model because public and authenticated grants are revoked; do not add permissive policies merely to silence the notice.

## Repository changes

The Supabase-only migration removes the Cloudflare Worker implementation and Wrangler deployment workflow, removes the Worker CI job and fallback publisher, updates documentation, and enforces direct Supabase ingestion in tests.

The private `market-pulse` migration updates its Twelve Data adapter and workflows to use the same Supabase credentials and table.

## Operational verification

For each production scan:
- Verify the workflow run completed.
- Verify the scanner reports `DIRECT_SUPABASE` and a non-zero accepted row count when valid observations exist.
- Query `grios_market_observations` for the latest `inserted_at`, `run_id`, provider, and asset classes.
- Verify source timestamps and freshness separately; successful insertion alone does not validate data freshness.
- Verify Telegram publication only when logs explicitly contain `TELEGRAM_PUBLISH: SENT`.

## Explicit boundary

Removing Worker code and workflow files from GitHub does not delete a previously deployed Cloudflare account resource or disconnect a Cloudflare GitHub App/Workers Builds integration. Those account-level actions require access to the Cloudflare dashboard and must be verified separately. Until that verification, describe Cloudflare as **unused by GRIOS code**, not as deleted from the Cloudflare account.
