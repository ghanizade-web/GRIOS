# Manual SEC 13F Ingestion Workflow

Workflow: .github/workflows/ingest-sec-13f.yml

## Required repository configuration

Set these in the GRIOS repository:

- Actions variable SEC_USER_AGENT: a descriptive SEC client identity with a monitored contact email (for example, "GRIOS Research contact@example.org").
- Actions secret SUPABASE_URL: the existing Supabase project URL.
- Actions secret SUPABASE_SERVICE_ROLE_KEY: the server-side Supabase secret used by the ingestion script.

Do not paste secret values into chat, commits, workflow inputs or logs. Never expose the service-role key to a browser or client application.

## Run

1. Open GitHub Actions → Ingest SEC 13F Report Period.
2. Select Run workflow.
3. Enter the 10-digit filer CIK and report period (YYYY-MM-DD).
4. Review the run result and download the SEC 13F audit artifact.

The workflow discovers recent and historical SEC filings for the selected filer/period, parses the original and amendments, reconstructs the public reported-holdings snapshot, stores a local SQLite copy in the artifact, and publishes the reconciled snapshot directly to the Supabase Data Hub.

## Safety and interpretation

- The workflow is manual only. It does not run on a schedule or scan an unreviewed CIK watchlist.
- SEC requests use the configured User-Agent and the client’s HTTPS/size controls.
- A 13F position is a reported holding, not proof of an actual purchase, trade date, beneficial owner or manager proprietary capital.
- If Supabase credentials are missing, the workflow fails before SEC ingestion.
- The report and SQLite database are retained as a 90-day workflow artifact; the Data Hub is the persistent shared store.
