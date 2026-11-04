# GRIOS v15 — Smart Money Evidence Registry

**Status:** Initial local evidence ledger implementation. It is not a live institutional-flow feed and does not imply that any named institution has traded an asset.

## Purpose

Preserve source-backed records of capital-related events without conflating different kinds of evidence. The registry is an evidence ledger, not a signal generator or an institutional portfolio tracker.

## Evidence taxonomy

- `ACTUAL_PURCHASE`: a completed purchase supported by evidence that establishes execution.
- `PURCHASE_ORDER`: an order or purchase commitment; not proof of delivery or completed settlement.
- `SUPPLY_CONTRACT`: signed commercial supply agreement; not proof that the full contracted volume has been delivered.
- `CORPORATE_CAPEX`: issuer investment/capex announcement or filing; not automatically an external asset purchase.
- `M_AND_A_ANNOUNCEMENT`: announced transaction; distinguish signing, closing and termination.
- `HOLDING_DISCLOSURE`: disclosed holdings; does not prove a manager invested its own balance-sheet capital.
- `FUND_FLOW`: subscription/redemption or fund-flow evidence; do not infer underlying security purchases without evidence.
- `STATED_INTEREST`: non-binding expression of interest; never upgrade to an order or contract.

## Capital ownership

`capital_origin` is one of `CLIENT_ASSETS`, `PROPRIETARY`, `SOVEREIGN`, `CORPORATE_BALANCE_SHEET`, or `UNKNOWN`. For asset managers, a fund holding or 13F filing must not be labeled proprietary unless the source establishes that the manager itself is the beneficial capital owner. If ownership is unclear, use `UNKNOWN`.

## Verification and execution are separate axes

Verification: `VERIFIED`, `CORROBORATED`, `PARTIALLY_VERIFIED`, `UNVERIFIED`, `DISPUTED`, `REJECTED`.

Execution: `RUMORED`, `ANNOUNCED`, `SIGNED`, `PARTIALLY_EXECUTED`, `COMPLETED`, `CANCELLED`, `UNKNOWN`.

A verified announcement is still an announcement, not a completed purchase. Evidence tier (1–4) records source quality and must not be treated as a probability or investment score.

## Required provenance

Every record requires entity, target, evidence type, capital origin, execution status, verification status, evidence tier, absolute HTTPS source URL, publication timestamp with timezone, retrieval timestamp with timezone, and a concise factual summary. Event time, amount, currency, instrument and caveats remain nullable where the source does not support them. Never invent amounts, ownership, execution or event dates.

## Local API

`smart_money_registry.py` provides:
- `initialize_registry(path)`
- `add_evidence(path, record)` — deterministic evidence ID and idempotent insert.
- `list_evidence(path, entity_name=..., target_name=..., verification_status=..., limit=...)`

SQLite is append-only by evidence ID: repeated identical records are ignored; corrections should be added as new source-backed records with an explicit caveat, not silently overwrite the original. This initial module is local-only. It does not crawl SEC, exchange, company, ETF or sovereign wealth sources, and it does not yet publish registry records to Supabase/Data Hub.

## Operational guardrails

1. Do not infer that BlackRock or another asset manager used proprietary capital from holdings disclosed for client funds.
2. Keep AUM, net fund flows, holdings, purchase orders, contracts and completed transactions as separate evidence classes.
3. Treat social posts and unattributed claims as unverified until corroborated by primary sources.
4. Preserve source publication and retrieval timestamps to prevent look-ahead bias.
5. Do not calculate a “smart money score” until entity resolution, source coverage, deduplication and point-in-time validation are implemented.
6. No automatic trading, allocation or recommendation is authorized by this registry.
