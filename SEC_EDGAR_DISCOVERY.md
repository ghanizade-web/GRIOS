# GRIOS v15 — SEC EDGAR 13F Discovery Client

## Scope

`sec_edgar_client.py` discovers recent 13F-HR and 13F-HR/A submissions from the SEC submissions JSON endpoint and inspects an accession's EDGAR filing index to identify its Information Table XML attachment.

## Required configuration

Supply a descriptive `User-Agent` string containing a monitored contact email. Do not hardcode personal credentials or secrets. The SEC asks automated clients to identify themselves and provides fair-access guidance in its developer resources.

## API

- `normalize_cik(...)` and `normalize_accession(...)` validate SEC identifiers.
- `SecEdgarClient.discover_13f_filings(...)` filters the submissions `recent` arrays to 13F-HR / 13F-HR/A and returns accession, filing date, report date and primary-document URL.
- `get_filing_index(...)` reads the SEC filing `index.json`.
- `find_information_table_document(...)` returns one uniquely identifiable XML attachment containing `infotable` or `informationtable` in its filename.

## Limitations

- The current client reads only the `filings.recent` arrays. Older filing history referenced by `filings.files` is not yet paginated.
- It does not download or parse the filing XML, parse cover-page amendment metadata, or automatically invoke the 13F parser/reconciler.
- It does not yet publish observations to the GRIOS Data Hub.
- The caller must apply SEC fair-access limits and should cache responses. No live SEC requests are executed by unit tests.

## Official references

- SEC developer resources: https://www.sec.gov/about/developer-resources
- SEC Form 13F FAQs: https://www.sec.gov/rules-regulations/staff-guidance/frequently-asked-questions-about-form-13f
- SEC EDGAR submissions API pattern: https://data.sec.gov/submissions/CIK0000320193.json
