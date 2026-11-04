# GRIOS Data Hub Worker

Cloudflare Worker API for normalized, authenticated market observations. The Worker is server-to-server; it does not expose Supabase credentials or accept browser-origin requests.

## Routes

All routes require Authorization: Bearer <GRIOS_INGEST_TOKEN>.

- GET /v1/status — checks the Supabase REST connection.
- POST /v1/ingest — accepts a versioned batch of 1–500 normalized observations.
- GET /v1/markets/latest?asset_class=crypto&symbol=BTC&limit=100 — reads latest provider-attributed observations.

Envelope fields: schema_version=1.0, generated_at, source_revision, observations[]. Each observation requires asset_key, symbol, name, asset_class, instrument, provider, feed_class, currency, observed_at and data_as_of; observations and extra carry history and source-specific metrics.

## Deployment

1. The migration `grios_market_observations_hub` has been applied to the connected Supabase project and verified: table and latest view exist; RLS is enabled; anon/authenticated have no SELECT grants; service_role has INSERT and view SELECT.
2. Add these GitHub Actions repository secrets to `ghanizade-web/GRIOS`: `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`, `GRIOS_INGEST_TOKEN`, `SUPABASE_URL`, and `SUPABASE_SERVICE_ROLE_KEY`. Use the existing Supabase project URL for SUPABASE_URL. Generate a strong random ingest token. Never put any secret value in Git, issue comments, logs, or chat.
3. Run the manual workflow [Deploy GRIOS Data Hub Worker](../../.github/workflows/deploy-data-hub.yml). It deploys the Worker and binds the three runtime secrets.
4. Add `GRIOS_DATA_HUB_URL` (the deployed Worker origin) and `GRIOS_DATA_HUB_TOKEN` (same value as `GRIOS_INGEST_TOKEN`) as GitHub Actions secrets in `ghanizade-web/market-pulse`.
5. Run [GRIOS Scanner to Data Hub](https://github.com/ghanizade-web/market-pulse/actions/workflows/grios-data-hub-scan.yml). Verify authenticated `/v1/status`, accepted record count, and `/v1/markets/latest`.

The Supabase project is currently ACTIVE_HEALTHY and the schema migration is applied. Worker deployment still requires the Cloudflare and server-side secret configuration above. No secrets are stored in this repository.

## Security and data semantics

- RLS is enabled; public and authenticated roles have no table/view grants. The Worker uses its server-side key.
- Ingestion is append-only and idempotent within a run (run_id, asset_key, provider).
- Provider, instrument, currency, observation timestamp, source date, and source revision are retained.
- Invalid or stale observations are not silently repaired or replaced.
- Upstream errors are reduced to status codes; response bodies and credentials are never logged or returned.
- The API stores research observations only. It does not execute trades or publish recommendations.
