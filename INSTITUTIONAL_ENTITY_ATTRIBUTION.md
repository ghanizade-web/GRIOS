# GRIOS v15 — Institutional Entity & Capital Attribution

**Status:** Initial source-backed entity registry. It does not independently establish beneficial ownership or investment activity.

## Data model

The registry stores canonical entities, source-backed aliases, and directed relationships. Entity types include asset managers, investment funds, sovereign wealth funds, pension funds, corporations, subsidiaries, governments, individuals and SPVs.

Identifiers such as SEC CIK and LEI are preferred over name-only identity. Name-only IDs are deterministic within jurisdiction but must not be treated as authoritative identifiers.

## Relationship taxonomy

- `MANAGES`: operational fund/asset management relationship.
- `ADVISES`: investment adviser relationship; does not establish beneficial ownership.
- `BENEFICIAL_OWNER_OF`: only when source evidence supports beneficial ownership.
- `SUBSIDIARY_OF`, `GENERAL_PARTNER_OF`, `ISSUER_OF`, `CONTROLS`.
- `UNKNOWN`: relationship cannot be safely classified.

Each relationship stores source URL, publication/retrieval timestamps, effective interval, verification status and caveat. Historical relationships must be represented with effective dates rather than overwriting the current relationship.

## Resolution policy

Entity resolution is exact-only against canonical legal names and source-backed aliases. Fuzzy matches are deliberately not auto-accepted. If an alias maps to more than one entity, the result is `AMBIGUOUS` and requires human review.

## Capital attribution guardrails

1. `ADVISES` or `MANAGES` never implies `BENEFICIAL_OWNER_OF`.
2. An asset manager's 13F filing may aggregate reportable holdings of managed accounts; it does not by itself prove proprietary investment by the manager.
3. A fund's holdings, fund flows, manager AUM and manager balance-sheet assets are distinct quantities.
4. Unknown beneficial ownership remains unknown.
5. Relationship evidence must be time-bounded and source-attributed.

## API

`institutional_entities.py` provides:
- `register_entity(...)`
- `add_entity_alias(...)`
- `add_entity_relationship(...)`
- `resolve_entity(...)` — exact match only, with explicit ambiguous result.
- `list_relationships(...)`

This is a local SQLite registry. No SEC crawler, 13F parser, LEI lookup service, automatic ownership inference, Data Hub publishing or smart-money score is included yet.
