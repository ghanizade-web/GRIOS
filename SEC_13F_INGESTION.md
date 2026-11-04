# GRIOS v15 — SEC 13F Single-Filing Ingestion

## Scope

`sec_13f_ingestion.py` connects the SEC EDGAR discovery client to the 13F parser:

1. Finds a requested 13F-HR / 13F-HR/A accession in the SEC submissions recent list.
2. Downloads the primary filing document and the uniquely identified Information Table XML.
3. Extracts report period, filing-manager name and amendment metadata from the cover page.
4. Cross-checks the cover-page report period against SEC submissions metadata.
5. Parses and normalizes positions using the existing 13F parser, preserving both SEC source URLs.

The SEC client now supports bounded document downloads. Each document is limited to 10 MB by default at the caller level; the method permits a stricter explicit maximum.

## Amendment metadata

The cover page supplies `isAmendment`, `amendmentNo` and `amendmentType`. For 13F-HR/A, the pipeline requires a positive amendment number and one of the SEC amendment types: `RESTATEMENT` or `NEW HOLDINGS`. The parsed filing can then be passed to `reconcile_13f_filing_chain` after the related original and all relevant amendments have been collected.

## API

`ingest_13f_filing(client, cik, accession_number, retrieved_at=...)` returns a normalized filing record with `ingestion_status=PARSED`, Information Table source URL and cover-page source URL.

## Limitations

- This is a single-filing operation. It does not yet paginate historical `filings.files` submissions, batch all amendments for a report period, schedule discovery, persist records, or publish to the Data Hub.
- SEC requests are mocked in tests; no live SEC download is performed in CI.
- The SEC filing's reported positions are not transaction records and do not prove beneficial ownership or proprietary manager capital.
- The caller must provide a descriptive SEC User-Agent containing a contact email and respect SEC fair-access guidance.

## Official references

- SEC developer resources: https://www.sec.gov/about/developer-resources
- SEC Form 13F FAQs: https://www.sec.gov/rules-regulations/staff-guidance/frequently-asked-questions-about-form-13f
