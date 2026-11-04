# GRIOS v15 — SEC 13F Snapshot Registry

## Purpose

Persist reconstructed public 13F report-period snapshots in a dedicated SQLite registry. This is separate from the generic Smart Money Evidence Registry because a disclosed position is not a transaction and the holding's market value must not be stored as a transaction value.

## Stored data

- Snapshot identity: filer CIK, report period, latest filing timestamp and all applied accessions.
- Filing ledger: form type, amendment number/type, filing timestamp, Information Table URL, cover-page URL and reconciliation effect.
- Position records: issuer, class, CUSIP, optional FIGI, put/call, share/principal amount and type, investment discretion, other manager, reported amount, normalized USD value and voting authority.

The registry preserves the reported public holdings. It does not infer beneficial ownership, manager proprietary capital, trade dates or live flows.

## API

- initialize_13f_registry(path)
- persist_13f_snapshot(path, report) — accepts only RECONCILED_PUBLIC_SNAPSHOT output; deterministic IDs and append-only idempotent inserts.
- get_13f_snapshot(path, filer_cik=..., report_period=..., snapshot_id=...) — retrieve an exact snapshot or the latest known snapshot for the filer/period.

Every filing source must be HTTPS SEC.gov. A snapshot cannot be persisted unless the holding count matches the actual holdings array and the applied-filing ledger is present.

## Limitations

The SQLite registry is the local research store. A validated, versioned payload can also be sent through the authenticated Data Hub client to the separate Supabase 13F tables. The Data Hub keeps filing and position records append-only; it does not replace the local source artifact. Scheduling and smart-money scoring remain out of scope.

## Evidence classification

A 13F record is a HOLDING_DISCLOSURE, not an ACTUAL_PURCHASE. It must not be translated into manager proprietary capital unless a separate source establishes beneficial capital ownership.

## Official references

- SEC Form 13F FAQs: https://www.sec.gov/rules-regulations/staff-guidance/frequently-asked-questions-about-form-13f
- SEC Form 13F XML Technical Specifications: https://www.sec.gov/submit-filings/technical-specifications
