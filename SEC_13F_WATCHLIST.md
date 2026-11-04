# GRIOS v15 — SEC 13F Institutional Watchlist

## Purpose

The watchlist workflow runs the existing SEC EDGAR discovery, XML parsing, amendment reconciliation, SQLite persistence and Data Hub publication pipeline for multiple 13F filers in one manually initiated batch.

The workflow is intentionally manual. Do not enable a recurring schedule until the Cloudflare Worker deployment, authenticated Data Hub readback, and at least one real SEC filing ingestion have been accepted operationally.

## Current watchlist

Configuration: `config/sec_13f_watchlist.json`

| Filer | CIK | Scope |
|---|---:|---|
| BlackRock, Inc. | 0001364742 | SEC 13F-HR public holdings filings |

The BlackRock CIK is grounded in its SEC filing detail page:
https://www.sec.gov/Archives/edgar/data/1364742/000108636424008417/0001086364-24-008417-index.htm

Add managers only after verifying the filer CIK against an official SEC filing detail page. A manager name or ticker is not a substitute for a CIK. Entries may be disabled with `"enabled": false`.

## Run

1. Configure repository variable `SEC_USER_AGENT` with a descriptive application name and monitored contact email.
2. Configure repository variable `GRIOS_DATA_HUB_URL` with the deployed HTTPS Worker origin.
3. Configure repository secret `GRIOS_INGEST_TOKEN` with the Worker bearer token.
4. Ensure the GRIOS Data Hub Worker is deployed and the 13F Supabase schema is available.
5. Open Actions → Ingest SEC 13F Institutional Watchlist → Run workflow.
6. Enter the report period as `YYYY-MM-DD` (normally a quarter-end date).

The workflow uploads per-filer report JSON, a shared SQLite snapshot registry and a batch summary as a 90-day artifact. The batch continues after an individual filer failure and exits unsuccessfully if any enabled filer fails.

## Rate limiting and provenance

One shared `SecEdgarClient` instance is used for the whole batch, preserving its default 0.11-second request pacing across all filers. The SEC requests include the configured descriptive User-Agent. No secrets are written to artifacts.

## Interpretation boundaries

- 13F is a delayed, periodic disclosure of reportable holdings, not a live portfolio feed.
- A reported position or quarter-over-quarter change does not establish a purchase, sale, trade date, beneficial owner or manager proprietary capital.
- The watchlist CIK identifies the filing manager. It does not by itself establish who economically owns the reported assets.
- Reported holdings should remain classified as public holdings evidence; capital origin stays unknown unless separately established by reliable evidence.
- A missing or failed filing is surfaced as an error; the pipeline does not synthesize a zero-holdings snapshot.

## Official references

- SEC Form 13F FAQs: https://www.sec.gov/rules-regulations/staff-guidance/frequently-asked-questions-about-form-13f
- SEC developer resources and fair-access guidance: https://www.sec.gov/about/developer-resources
