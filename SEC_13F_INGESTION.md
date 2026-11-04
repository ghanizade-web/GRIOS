# GRIOS v15 — SEC 13F Single-Filing Ingestion

## Scope

`sec_13f_ingestion.py` connects the SEC EDGAR discovery client to the 13F parser:

1. Finds a requested 13F-HR / 13F-HR/A accession in the SEC submissions recent list or, when enabled, historical archives.
2. Downloads the primary filing document and the uniquely identified Information Table XML.
3. Extracts report period, filing-manager name and amendment metadata from the cover page.
4. Cross-checks the cover-page report period against SEC submissions metadata.
5. Parses and normalizes positions using the existing 13F parser, preserving both SEC source URLs.

The SEC client now supports bounded document downloads. Each document is limited to 10 MB by default; callers may set a stricter explicit maximum. The parser also preserves the optional FIGI identifier introduced in the SEC Form 13F XML specification.

## Amendment metadata

The cover page supplies `isAmendment`, `amendmentNo` and `amendmentType`. For 13F-HR/A, the pipeline requires a positive amendment number and one of the SEC amendment types: `RESTATEMENT` or `NEW HOLDINGS`. The parsed filing can then be passed to `reconcile_13f_filing_chain` after the related original and all relevant amendments have been collected.

## API

`ingest_13f_filing(client, cik, accession_number, retrieved_at=..., include_historical=False)` returns a normalized filing record with `ingestion_status=PARSED`, Information Table source URL and cover-page source URL.

`ingest_13f_report_period(client, cik, report_period, retrieved_at=..., include_historical=True)` discovers all public 13F-HR / 13F-HR/A filings for the selected quarter, downloads and parses each, then invokes `reconcile_13f_filing_chain` to produce one reconstructed public snapshot. The default enables historical submissions so that older original filings are not silently omitted. Missing originals, duplicate amendment numbers, inconsistent periods and invalid filing order raise errors.

## Limitations

- Report-period ingestion is an on-demand batch operation; it is not scheduled and does not persist records or publish to the Data Hub.
- Only public submissions returned by SEC EDGAR are considered. Confidential treatment and any unavailable filing documents are outside the discovered public snapshot.
- SEC requests are mocked in tests; no live SEC download is performed in CI.
- The SEC filing's reported positions are not transaction records and do not prove beneficial ownership or proprietary manager capital.
- The caller must provide a descriptive SEC User-Agent containing a contact email and respect SEC fair-access guidance.

## Official references

- SEC developer resources: https://www.sec.gov/about/developer-resources
- SEC Form 13F FAQs: https://www.sec.gov/rules-regulations/staff-guidance/frequently-asked-questions-about-form-13f
- SEC XML Technical Specifications (Form 13F, Version 2.0): https://www.sec.gov/submit-filings/technical-specifications
