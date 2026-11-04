# Manual SEC 13F Ingestion Workflow

Workflow: .github/workflows/ingest-sec-13f.yml

## Required repository configuration

Set these in the GRIOS repository:

- Actions variable SEC_USER_AGENT: a descriptive SEC client identity with a monitored contact email (for example, "GRIOS Research contact@example.org").
- Actions variable GRIOS_DATA_HUB_URL: the deployed Cloudflare Worker HTTPS origin.
- Actions secret GRIOS_INGEST_TOKEN: the same bearer token configured as the Worker secret.

Do not paste secret values into chat, commits, workflow inputs or logs. The existing deploy workflow uses the same GRIOS_INGEST_TOKEN secret.

## Run

1. Open GitHub Actions → Ingest SEC 13F Report Period.
2. Select Run workflow.
3. Enter the 10-digit filer CIK and report period (YYYY-MM-DD).
4. Review the run result and download the SEC 13F audit artifact.

The workflow discovers recent and historical SEC filings for the selected filer/period, parses the original and amendments, reconstructs the public reported-holdings snapshot, stores a local SQLite copy in the artifact, and publishes the snapshot to the authenticated Data Hub endpoint.

## Safety and interpretation

- The workflow is manual only. It does not run on a schedule or scan an unreviewed CIK watchlist.
- SEC requests use the configured User-Agent and the client’s HTTPS/size controls.
- A 13F position is a reported holding, not proof of an actual purchase, trade date, beneficial owner or manager proprietary capital.
- If deployment variables/secrets are missing, the workflow fails before SEC ingestion.
- The report and SQLite database are retained as a 90-day workflow artifact; the Data Hub is the persistent shared store.
