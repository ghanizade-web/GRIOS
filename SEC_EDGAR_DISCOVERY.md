# GRIOS v15 — SEC EDGAR 13F Discovery Client

## Scope

`sec_edgar_client.py` discovers recent 13F-HR and 13F-HR/A submissions from the SEC submissions JSON endpoint and inspects an accession's EDGAR filing index to identify its Information Table XML attachment.

## Required configuration

Supply a descriptive `User-Agent` string containing a monitored contact email. Do not hardcode personal credentials or secrets. The SEC asks automated clients to identify themselves and provides fair-access guidance in its developer resources.

## API

- `normalize_cik(...)` and `normalize_accession(...)` validate SEC identifiers.
- `SecEdgarClient.discover_13f_filings(...)` filters the submissions `recent` arrays to 13F-HR / 13F-HR/A and returns accession, filing date, report date and primary-document URL. Set `include_historical=True` to fetch SEC `filings.files` JSON archives, apply filing-date range filters and deduplicate accessions across recent and historical sets.
- `get_filing_index(...)` reads the SEC filing `index.json`.
- `find_information_table_document(...)` returns one uniquely identifiable XML attachment containing `infotable` or `informationtable` in its filename.

## Limitations

- Historical pagination is opt-in. It reads SEC `filings.files` references sequentially and has a configurable `max_historical_files` safety cap (default 1,000); a cap breach raises an error rather than silently truncating history.
- It does not download or parse the filing XML, parse cover-page amendment metadata, or automatically invoke the 13F parser/reconciler.
- It does not yet publish observations to the GRIOS Data Hub.
- Every SEC JSON/index lookup and XML download is paced by the client. The default minimum interval is 0.11 seconds between request starts (about 9 requests/second), below the SEC's 10 requests/second fair-access ceiling. Callers can tune `min_request_interval`; setting it to zero disables pacing and should be reserved for controlled tests.
- Pacing is per `SecEdgarClient` instance. Use one shared instance for a batch; creating multiple clients does not provide a process-wide or organization-wide rate limit. Cache responses at the workflow/application layer where appropriate.
- No live SEC requests are executed by unit tests.

## Official references

- SEC developer resources: https://www.sec.gov/about/developer-resources
- SEC Form 13F FAQs: https://www.sec.gov/rules-regulations/staff-guidance/frequently-asked-questions-about-form-13f
- SEC EDGAR submissions API pattern: https://data.sec.gov/submissions/CIK0000320193.json
