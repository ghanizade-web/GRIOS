# GRIOS v15 — Live Crypto Audit Acceptance Report

**Execution date:** 2026-11-04  
**Environment:** GitHub Actions / Ubuntu / Python 3.12  
**Result:** PASS — live provider retrieval, reconciliation, universe filtering, report generation, and artifact upload completed successfully.

## 1. Execution evidence

| Field | Value |
|---|---|
| Repository running the workflow | `ghanizade-web/market-pulse` |
| Workflow | `GRIOS Scanner` |
| Workflow run | [41884296819, attempt 2](https://github.com/ghanizade-web/market-pulse/actions/runs/41884296819) |
| Workflow conclusion | `success` |
| GRIOS runtime checkout | `df4335cdde22b6a46a6a292f76e6ee192aea52cd` |
| Audit generation timestamp | `2026-11-04T19:32:57Z` |
| Audit JSON | `crypto-audit-20261104T193257Z.json` |
| Report | `grios-20261104T193257Z.txt` |
| Uploaded artifact | `grios-daily-report-6` (artifact ID `13357456020`) |

The run checked out the merged GRIOS v15 crypto-audit integration commit, not the pre-integration scanner revision.

## 2. Provider connectivity and data quality

| Metric | CoinGecko | CoinMarketCap |
|---|---:|---:|
| API credential binding | CONFIGURED | CONFIGURED |
| Requested symbols | 14 | 14 |
| Returned provider rows | 250 | 500 |
| Valid and fresh requested assets | 13 | 13 |
| Provider-level errors | 0 | 0 |
| Duplicate-symbol ambiguity | 0 | 0 |

The provider adapters returned valid, timezone-aware observations within the configured 30-minute freshness threshold.

## 3. Reconciliation

| Metric | Result |
|---|---:|
| Combined provider rows | 26 |
| Accepted cross-source assets | 13 |
| Identity mismatches | 0 |
| Duplicate-symbol rejections | 0 |
| Price conflicts above 2% | 0 |
| Maximum observed cross-source price deviation | 0.3292% (XRP) |

All 13 reconciled assets were labelled `ACCEPTED_CROSS_SOURCE`.

**Identity limitation:** the current reconciliation rule establishes normalized-name agreement and price consistency. It does not independently prove token contract, chain, issuer, or legal-entity identity. Audit status therefore remains `UNCONFIRMED_NAME_MATCH`.

## 4. Universe filter

| Metric | Result |
|---|---:|
| Reconciled input | 13 |
| Eligible | 13 |
| Excluded | 0 |

### Missing requested symbol

`TON` was requested but was not returned by either provider in this execution. Both provider audits recorded `NOT_RETURNED`. TON was not silently substituted or included in the accepted universe.

This is an outstanding watchlist coverage item. The current evidence does not establish whether the cause was provider coverage, ranking/endpoint behavior, or symbol mapping.

## 5. Report and artifact delivery

- The daily GRIOS report was generated.
- The crypto audit JSON was generated and parsed successfully after artifact download.
- The report and audit were uploaded in the GitHub Actions artifact.
- The run completed with a successful conclusion.

### Telegram side effect

The rerun inherited the original workflow-dispatch input. The action log explicitly recorded `Telegram delivery: SUCCESS`. The report was therefore sent to the configured Telegram destination during this rerun.

This was not required for the data-validation test. The market-pulse workflow should prevent Telegram delivery on reruns to avoid accidental duplicate notifications.

## 6. Non-crypto observation

The broader daily scanner completed successfully, but the report recorded `EURGBP: ECB unavailable (OpenBBError)`. This does not invalidate the crypto provider audit; it remains an independent ECB feed issue for follow-up.

## 7. Acceptance decision

**Accepted for live crypto data retrieval and audit generation, with one coverage exception (TON).**

Verified:
- Live credentials were bound to the workflow environment.
- Both providers returned current requested-symbol data.
- 13 assets reconciled across both providers.
- No duplicate-symbol, identity-name, or price-deviation rejection occurred.
- The 13 reconciled assets passed the configured universe filter.
- The JSON audit and daily report were generated and archived.

Not established by this test:
- Historical signal calibration or predictive performance.
- Independent token-contract identity verification.
- Order-book depth, bid/ask spread, or executable liquidity.
- Verified institutional flows or catalyst coverage.
- Durable SQLite persistence across separate GitHub Actions runners.
- Production readiness of every GRIOS v15 engine.
- Resolution of TON provider coverage or the ECB EURGBP feed.

## 8. Follow-up actions

1. Investigate why TON was absent from both provider responses and decide whether explicit per-symbol lookup is required.
2. Prevent Telegram re-delivery on workflow reruns — implemented in `market-pulse` and merged to `main`; the guard applies to new runs and skips Telegram on rerun attempts.
3. Validate database persistence outside ephemeral GitHub-hosted runner storage.
4. Continue source-specific acceptance tests for ECB, EIA, FRED, and equity feeds.

**Verification principle:** a successful live scan verifies this execution path only; it does not establish full production validation of the entire GRIOS platform.


## 9. Post-acceptance regression correction

A follow-up source review found that `main()` still referenced the removed argparse attribute `crypto_audit_baseline_sha` after the parser option had been renamed to `crypto_audit_source_commit_sha`.

The reference was corrected and an AST regression test was added. The first CI attempt correctly caught an issue in the new test itself (it searched `ast.Name` nodes instead of `ast.Attribute` nodes); the test was corrected and rerun.

Final verification for the correction:
- Pull Request: [#5](https://github.com/ghanizade-web/GRIOS/pull/5)
- CI run: [41899474446](https://github.com/ghanizade-web/GRIOS/actions/runs/41899474446)
- `python -m py_compile scanner.py`: PASS
- `python -m pytest -q`: **23 passed**
- PR merged to `main` as commit `25e23f6c6d50861e19e3adf5984cf97bcb2a9926`

This correction repairs audit metadata argument wiring. It does not alter `market_score()`, provider retrieval, reconciliation thresholds, or universe eligibility rules.
