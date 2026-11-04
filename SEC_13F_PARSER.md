# GRIOS v15 — SEC Form 13F Parser

## Scope

This module parses a single SEC Form 13F-HR or 13F-HR/A XML Information Table document and compares two reported holdings snapshots. It deliberately does not treat a holdings delta as a confirmed transaction.

## Input contract

The caller supplies the XML attachment and filing metadata:
- accession number
- filer CIK and filer name
- form type (13F-HR or 13F-HR/A)
- filing timestamp and report-period end date
- SEC.gov source URL and retrieval timestamp

13F-NT notices are rejected because they are not holdings tables. The parser is for the Information Table XML attachment; it is not a complete filing assembler or an EDGAR crawler.

## Normalized fields

Each reported position includes issuer, title of class, CUSIP, reported value in USD thousands, share/principal amount and type, investment discretion, other manager, optional put/call designation, and voting authority.

## Snapshot comparison

`compare_13f_snapshots` compares positions by CUSIP, put/call and share/principal type. It reports changes in reported amounts and reported values. These are snapshot differences, not trade records.

A new or no-longer-reported position must not be labeled as a confirmed purchase or sale. Changes can reflect valuation, scope, manager discretion, amendments, options, or filing corrections.

## Mandatory interpretation limits

- A filing is a delayed report for a specified reporting period, not real-time flow.
- The filing does not establish the exact trade date.
- A manager's filing does not by itself establish that the manager invested proprietary balance-sheet capital.
- The parser does not resolve beneficial ownership or infer client-versus-proprietary capital.
- Amendments are preserved as separate filing identifiers; amendment/restatement precedence and corrected snapshot reconstruction require a dedicated filing-level reconciliation layer.
- The parser does not currently ingest the SEC bulk 13F dataset, submissions API, issuer master, or Data Hub.

## Official SEC references

- Form 13F FAQs: https://www.sec.gov/rules-regulations/staff-guidance/frequently-asked-questions-about-form-13f
- Form 13F XML technical specification: https://www.sec.gov/files/info/edgar/specifications/form13fxmltechspec.htm
- Form 13F data sets: https://www.sec.gov/files/form_13f.pdf
- EDGAR developer resources: https://www.sec.gov/about/developer-resources
