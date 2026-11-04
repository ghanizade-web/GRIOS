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
- `python -m pytest -q`: **24 passed** in the final suite
- PR #5 merged to `main` as commit `25e23f6c6d50861e19e3adf5984cf97bcb2a9926`

This correction repairs audit metadata argument wiring. It does not alter `market_score()`, provider retrieval, reconciliation thresholds, or universe eligibility rules.


## 10. Final repository integration and main-branch CI

- PR [#7](https://github.com/ghanizade-web/GRIOS/pull/7) merged the end-to-end `main()` regression test. It verifies that `GRIOS_SOURCE_COMMIT_SHA` is written into `source_revision.git_commit_sha`, that the audit JSON is generated, and that the report output is written.
- PR [#8](https://github.com/ghanizade-web/GRIOS/pull/8) corrected the README to match the actual implementation: direct CoinGecko/CoinMarketCap crypto adapters, rather than claiming the scanner already uses the Cloudflare Data Hub. It also enabled the crypto audit CI workflow on pushes to `main`.
- PR #7 CI: [41900256396](https://github.com/ghanizade-web/GRIOS/actions/runs/41900256396) — PASS, 24 tests.
- PR #8 CI: [41900475554](https://github.com/ghanizade-web/GRIOS/actions/runs/41900475554) — PASS, 24 tests.
- Post-merge `main` CI: [41900573045](https://github.com/ghanizade-web/GRIOS/actions/runs/41900573045) — PASS, 24 tests.
- PR #7 merge commit: `5eb33a599854fab2d01d382ebf2f34f3e922a53c`.
- PR #8 merge commit: `53763c52f65d265447a483065618aefffffc6da1`.

The current test suite contains 24 tests and the main-branch push validation is green. A fresh manual live scanner dispatch on the final GRIOS commit has not yet been performed; prior live provider evidence remains tied to the earlier runtime revision recorded in Section 1.


## 11. Final live acceptance — 2026-11-04

A fresh end-to-end run was completed against the final GRIOS `main` revision.

- Workflow run: [market-pulse run #41903098841](https://github.com/ghanizade-web/market-pulse/actions/runs/41903098841)
- Trigger: `push` on the narrowly scoped workflow-file validation trigger; attempt 1.
- GRIOS source commit captured by the runner: `eb62cc96b42629046bdadf402ea16355a6f0eb0f`.
- Overall workflow and scanner job: **success**.
- Python dependency installation: success.
- CoinGecko, CoinMarketCap, FRED, and EIA credentials: configured (values were not logged).
- Scanner report and crypto audit JSON: generated and uploaded as artifact `grios-daily-report-7` (artifact ID `13358143465`).
- Telegram delivery step: **skipped**, as intended for this validation run.

### Live crypto audit results

- CoinGecko: 13 of 14 requested symbols returned valid records.
- CoinMarketCap: 13 of 14 requested symbols returned valid records.
- TON: `NOT_RETURNED` by both providers in their requested top-market pages.
- Reconciliation: 13 accepted cross-source assets, zero rejected symbols, zero price conflicts.
- Maximum observed cross-source price deviation: 0.1766%, below the 2% data-quality threshold.
- Identity remains `UNCONFIRMED_NAME_MATCH`; matching ticker/name labels are not equivalent to cryptographic asset-contract verification.
- Universe filter: 13 eligible, 0 excluded.

### Live non-crypto data limitation

The EIA API key was configured, but the Henry Hub spot series returned `OpenBBError` in this run. The report correctly marks this series unavailable rather than substituting an unverified value. This is a provider/adapter investigation item, not a successful EIA validation.

### Acceptance decision

**Crypto audit live acceptance: PASS for the 13 returned watchlist assets.**

**Whole-market data acceptance: CONDITIONAL.** TON fallback is not implemented, Henry Hub EIA remains unavailable, and the existing scanner still lacks crypto OHLCV history, order-book spread, verified institutional flow, catalyst integration, and calibrated backtesting. The current score remains a preliminary screening heuristic, not a probability of profit or trade recommendation.

The artifact is available from the workflow run page above. No secrets or credentials are included in the artifact by design.

## 12. Post-run correction — TON native-asset rebrand

A source-identity review on 2026-11-05 established that the native cryptocurrency of The Open Network was renamed from Toncoin (TON) to Gram (GRAM), effective 2026-06-15. The blockchain remains The Open Network (TON); the native asset's ticker and display name changed without a token migration.

The prior scanner run's provider IDs — CoinGecko `the-open-network` and CoinMarketCap `11419` — resolve to Gram (prev. Toncoin), not to an unrelated token. The previous `IDENTITY_MISMATCH` result was therefore caused by stale scanner expectations for the old ticker/name, not by provider substitution. The earlier decision to keep rejecting the record was conservative, but its interpretation of the provider evidence was incorrect.

The scanner correction now:
- Uses `GRAM` as the canonical watchlist symbol.
- Converts legacy `TON` watchlist entries to `GRAM` at load time and de-duplicates aliases.
- Validates provider asset ID, symbol, and name/slug for GRAM in both ranked listings and pinned-ID fallback requests.
- Continues rejecting mismatched IDs, names, symbols, duplicate rows, stale quotes, and invalid prices.

**Runtime status:** this correction is in PR #40 and has not yet been validated by a post-merge live scan. The prior live artifact must not be retroactively described as a successful GRAM ingestion. A new scanner run is required to verify current provider coverage and Supabase publication.
