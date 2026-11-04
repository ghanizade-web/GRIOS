# GRIOS Data Hub Worker

Cloudflare Worker API for normalized, authenticated market observations. The Worker is server-to-server; it does not expose Supabase credentials or accept browser-origin requests.

## Routes

All routes require Authorization: Bearer <GRIOS_INGEST_TOKEN>.

- GET /v1/status — checks the Supabase REST connection.
- POST /v1/ingest — accepts a versioned batch of 1–500 normalized observations.
- GET /v1/markets/latest?asset_class=crypto&symbol=BTC&limit=100 — reads latest provider-attributed observations.

Envelope fields: schema_version=1.0, generated_at, source_revision, observations[]. Each observation requires asset_key, symbol, name, asset_class, instrument, provider, feed_class, currency, observed_at and data_as_of; observations and extra carry history and source-specific metrics.

## Deployment

1. Apply supabase/migrations/20261104200000_grios_data_hub.sql to the existing Supabase project.
2. In Cloudflare Worker settings, add secrets GRIOS_INGEST_TOKEN, SUPABASE_URL, and SUPABASE_SERVICE_ROLE_KEY. Generate a long random ingest token; never commit it. Use the Supabase server-side service-role key only as a Worker secret.
3. From this directory run npm test, then npx wrangler deploy.
4. Configure the scanner with GRIOS_DATA_HUB_URL and GRIOS_DATA_HUB_TOKEN in its server-side environment.
5. Verify authenticated /v1/status, ingest a test observation, then query /v1/markets/latest.

The Supabase project must be active before the migration or live API test can succeed. No secrets are stored in this repository.

## Security and data semantics

- RLS is enabled; public and authenticated roles have no table/view grants. The Worker uses its server-side key.
- Ingestion is append-only and idempotent within a run (run_id, asset_key, provider).
- Provider, instrument, currency, observation timestamp, source date, and source revision are retained.
- Invalid or stale observations are not silently repaired or replaced.
- Upstream errors are reduced to status codes; response bodies and credentials are never logged or returned.
- The API stores research observations only. It does not execute trades or publish recommendations.
