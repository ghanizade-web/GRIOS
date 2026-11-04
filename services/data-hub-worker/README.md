# GRIOS Data Hub Worker

Cloudflare Worker API for normalized, authenticated market observations. The Worker is server-to-server; it does not expose Supabase credentials or accept browser-origin requests.

## Routes

All routes require Authorization: Bearer <GRIOS_INGEST_TOKEN>.

- GET /v1/status — checks the Supabase REST connection.
- POST /v1/ingest — accepts a versioned batch of 1–500 normalized observations.
- GET /v1/markets/latest?asset_class=crypto&symbol=BTC&limit=100 — reads latest provider-attributed observations.
- POST /v1/13f/snapshots — accepts a validated, reconciled public SEC 13F report-period snapshot and atomically stores the snapshot, applied-filing ledger and positions through a Supabase RPC.
- GET /v1/13f/latest?cik=0000123456&report_period=2026-09-30 — returns the latest stored public snapshot for a filer and report period.

Market-observation envelope fields: schema_version=1.0, generated_at, source_revision, observations[]. Each observation requires asset_key, symbol, name, asset_class, instrument, provider, feed_class, currency, observed_at and data_as_of; observations and extra carry history and source-specific metrics.

SEC 13F envelope fields: schema_version=1.0 and snapshot. The snapshot requires a deterministic snapshot_id, zero-padded filer CIK, report period, latest filing timestamp, applied_filings[] and holdings[]. Filing provenance URLs must be HTTPS SEC.gov. The Worker validates amendment order, original filing presence, CUSIP/FIGI, quantity, USD value and voting authority before calling the atomic database function.

## Deployment

1. Supabase migrations `grios_market_observations_hub`, `grios_sec_13f_snapshots` and `grios_13f_append_only_security_fix` have been applied. The three 13F tables exist with RLS enabled; anon/authenticated have no table grants; service_role has only SELECT and INSERT. The two RPC functions are executable by service_role only.
2. Add these GitHub Actions repository secrets to `ghanizade-web/GRIOS`: `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`, `GRIOS_INGEST_TOKEN`, `SUPABASE_URL`, and `SUPABASE_SERVICE_ROLE_KEY`. Use the existing Supabase project URL for SUPABASE_URL. Generate a strong random ingest token. Never put any secret value in Git, issue comments, logs, or chat.
3. Run the manual workflow [Deploy GRIOS Data Hub Worker](../../.github/workflows/deploy-data-hub.yml). It deploys the Worker and binds the three runtime secrets.
4. Add `GRIOS_DATA_HUB_URL` (the deployed Worker origin) and `GRIOS_DATA_HUB_TOKEN` (same value as `GRIOS_INGEST_TOKEN`) as GitHub Actions secrets in `ghanizade-web/market-pulse`.
5. Run [GRIOS Scanner to Data Hub](https://github.com/ghanizade-web/market-pulse/actions/workflows/grios-data-hub-scan.yml). Verify authenticated `/v1/status`, accepted record count, and `/v1/markets/latest`.

The Supabase project is currently ACTIVE_HEALTHY and the schema migration is applied. Worker deployment still requires the Cloudflare and server-side secret configuration above. No secrets are stored in this repository.

## Security and data semantics

- RLS is enabled; public and authenticated roles have no table/view grants. The Worker uses its server-side key.
- Market-observation ingestion is append-only and idempotent within a run (run_id, asset_key, provider).
- 13F snapshot ingestion is atomic and idempotent by content-derived snapshot_id; filing and position rows are append-only.
- 13F holdings are disclosed positions, not transaction records. Reported USD market value is never treated as transaction value or proof of manager proprietary capital.
- Provider, instrument, currency, observation timestamp, source date, and source revision are retained.
- Invalid or stale observations are not silently repaired or replaced.
- Upstream errors are reduced to status codes; response bodies and credentials are never logged or returned.
- The API stores research observations only. It does not execute trades or publish recommendations.
