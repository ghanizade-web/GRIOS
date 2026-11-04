# GRIOS v15 — SEC Form 13F Parser

## Scope

This module parses a single SEC Form 13F-HR or 13F-HR/A XML Information Table document and compares two reported holdings snapshots. It deliberately does not treat a holdings delta as a confirmed transaction.

## Input contract

The caller supplies the XML attachment and filing metadata:
- accession number
- filer CIK and filer name
- form type (13F-HR or 13F-HR/A)
- for 13F-HR/A: amendment number (1–99) and amendment type (`RESTATEMENT` or `NEW HOLDINGS`)
- filing timestamp and report-period end date
- SEC.gov source URL and retrieval timestamp

13F-NT notices are rejected because they are not holdings tables. The parser is for the Information Table XML attachment; it is not a complete filing assembler or an EDGAR crawler.

## Normalized fields

Each reported position includes issuer, title of class, CUSIP, raw reported value and its filing-date-dependent unit, normalized `value_usd`, share/principal amount and type, investment discretion, other manager, optional put/call designation, and voting authority.

### Reported-value normalization

The parser uses the filing date (not the report-period date) to interpret the XML `value` field:

- Filings submitted before 2023-01-03: reported values are interpreted as USD thousands and multiplied by 1,000.
- Filings submitted on or after 2023-01-03: reported values are interpreted as USD.

All outputs expose `value_usd` in dollars, alongside `reported_value` and `reported_value_unit` so the original scale remains auditable. This follows the SEC's updated Form 13F rounding convention effective January 3, 2023 (SEC Form 13F FAQs, update note and FAQs 61–62): https://www.sec.gov/rules-regulations/staff-guidance/frequently-asked-questions-about-form-13f

## Amendment reconciliation

`reconcile_13f_filing_chain` requires exactly one original 13F-HR and validates that all amendments share the same filer CIK and report period. Amendments are applied in amendment-number order, with filing timestamps required to be strictly increasing.

- `RESTATEMENT`: replaces the previously reconstructed public snapshot with the complete corrected holdings table.
- `NEW HOLDINGS`: supplements the currently reconstructed public snapshot with additional reported entries.

The SEC explains that a restatement resubmits the entire corrected filing and supersedes the original, while a new-holdings amendment adds only omitted/new entries and supplements the public filing. Multiple amendments may be filed. See SEC Form 13F FAQs 58b–58e: https://www.sec.gov/rules-regulations/staff-guidance/frequently-asked-questions-about-form-13f

The reconciler preserves source filing metadata in its applied-filings ledger. It does not infer trades or beneficial ownership.

## Snapshot comparison

`compare_13f_snapshots` compares positions by CUSIP, put/call and share/principal type. It reports changes in reported amounts and reported values. These are snapshot differences, not trade records.

A new or no-longer-reported position must not be labeled as a confirmed purchase or sale. Changes can reflect valuation, scope, manager discretion, amendments, options, or filing corrections.

## Mandatory interpretation limits

- A filing is a delayed report for a specified reporting period, not real-time flow.
- The filing does not establish the exact trade date.
- A manager's filing does not by itself establish that the manager invested proprietary balance-sheet capital.
- The parser does not resolve beneficial ownership or infer client-versus-proprietary capital.
- Amendment metadata is required for 13F-HR/A. The filing-chain reconciler applies RESTATEMENT as replacement and NEW HOLDINGS as supplementation, based on the SEC's stated filing semantics.
- The parser does not currently ingest the SEC bulk 13F dataset, submissions API, issuer master, or Data Hub.

## Official SEC references

- Form 13F FAQs: https://www.sec.gov/rules-regulations/staff-guidance/frequently-asked-questions-about-form-13f
- Form 13F XML technical specification: https://www.sec.gov/files/info/edgar/specifications/form13fxmltechspec.htm
- Form 13F data sets: https://www.sec.gov/files/form_13f.pdf
- EDGAR developer resources: https://www.sec.gov/about/developer-resources
