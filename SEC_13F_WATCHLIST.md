# GRIOS v15 — SEC 13F Institutional Watchlist

## Purpose

The watchlist workflow runs the existing SEC EDGAR discovery, XML parsing, amendment reconciliation, SQLite persistence and Data Hub publication pipeline for multiple 13F filers in one manually initiated batch.

The workflow is intentionally manual. The persistent Data Hub is Supabase; ingestion writes directly to the secured Supabase database.

## Current watchlist

Configuration: `config/sec_13f_watchlist.json`

| Filer | CIK | SEC filing-detail evidence |
|---|---:|---|
| BlackRock, Inc. | 0001364742 | https://www.sec.gov/Archives/edgar/data/1364742/000108636424008417/0001086364-24-008417-index.htm |
| Berkshire Hathaway Inc. | 0001067983 | https://www.sec.gov/Archives/edgar/data/1067983/000119312526352200/0001193125-26-352200-index.htm |
| FMR LLC | 0000315066 | https://www.sec.gov/Archives/edgar/data/315066/000031506626002260/0000315066-26-002260-index.htm |
| State Street Corporation | 0000093751 | https://www.sec.gov/Archives/edgar/data/93751/000009375126000507/0000093751-26-000507-index.html |

Each CIK above is shown as the filer on an SEC Form 13F-HR filing detail page. The list is a starter set of four direct filers, not a complete map of their subsidiaries, affiliates, funds or delegated managers. Do not interpret the listed manager's consolidated name as proof that it beneficially owns every reported position.

Add managers only after verifying the filer CIK against an official SEC filing detail page. A manager name or ticker is not a substitute for a CIK. Entries may be disabled with `"enabled": false`.

## Run

1. Configure repository variable `SEC_USER_AGENT` with a descriptive application name and monitored contact email.
2. Configure repository secret `SUPABASE_URL` with the existing Supabase project URL.
3. Configure repository secret `SUPABASE_SERVICE_ROLE_KEY` with the server-side service key.
4. Ensure the 13F Supabase schema migrations are applied.
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
