# GRIOS v15 — Point-in-Time Evidence & Walk-Forward Validation Protocol

**Project:** Ghanizadeh Research Intelligence Operating System  
**Version:** 15.0 Institutional Edition  
**Module:** Signal and Megatrend Score Validation  
**Status:** Research protocol — not evidence of calibrated live performance  
**Mission:** We Track Capital Before The Crowd.

---

## 1. Purpose and operating boundary

This protocol defines the minimum evidence, temporal controls, validation design, and publication gates required before any GRIOS score may be described as statistically calibrated or any historical result may be presented as out-of-sample performance.

A score can be useful for research prioritization without being a calibrated probability. GRIOS must preserve that distinction.

Until the acceptance gates in this document have been met:
- Scores are **research heuristics**, not probabilities of profit.
- Historical scenario examples are not backtests.
- A successful software test is not evidence of predictive validity.
- No strategy performance, Sharpe ratio, hit rate, or expected return may be claimed without reproducible point-in-time tests and cost assumptions.

This protocol does not authorize automated trading or portfolio allocation.

## 2. Evidence contract for every signal

Every signal candidate must retain, where applicable:

| Field | Requirement |
|---|---|
| signal_id | Stable unique identifier |
| instrument_id | Canonical instrument/security identifier; ticker alone is insufficient |
| direction | LONG / SHORT / WATCH |
| thesis | Explicit causal mechanism |
| event_time | When the underlying event occurred |
| published_at | When the source made it public |
| retrieved_at | When GRIOS first obtained it |
| effective_at | Earliest time the information could legitimately influence a decision |
| source_url | Durable source reference |
| source_type | Filing, official release, exchange, provider, media, alternative |
| evidence_tier | Tier 1–4, using the Data Intelligence protocol |
| verification_status | VERIFIED / CORROBORATED / PARTIALLY_VERIFIED / UNVERIFIED / DISPUTED / REJECTED |
| execution_status | RUMORED through COMPLETED/CANCELLED as supported |
| freshness_status | LIVE / CURRENT / DELAYED / STALE / UNAVAILABLE / UNVERIFIED |
| feature_snapshot_id | Immutable identifier for exact model inputs |
| model_version | Code and configuration version |
| score_components | Component values, weights, missingness and explanations |
| generated_at | Signal generation timestamp |
| activation_rule | Conditions required before a trade thesis is active |
| invalidation_rule | Conditions that disprove the thesis |
| horizon | Predefined evaluation horizon |
| benchmark | Relevant asset-class and/or sector benchmark |
| caveats | Known limitations and conflicts |

Unknown values remain null or explicitly unknown. Never infer a missing transaction amount, publication time, entity identity, or execution status.

## 3. Point-in-time data and leakage prevention

The backtest must reconstruct what was knowable at each historical decision timestamp.

1. Use `published_at` or the earliest verified public availability time, not the event date alone.
2. If publication time is unavailable, apply a conservative delay (at least the next eligible session) and mark the record as time-imprecise.
3. Never use a later filing revision, corrected macro observation, restated earnings figure, or updated index constituent list as if it had been known earlier.
4. Preserve original and revised values separately, with vintage metadata.
5. Use point-in-time constituents and delisted securities; avoid survivorship bias.
6. Use only features available before the decision timestamp.
7. Normalize time zones and trading calendars explicitly.
8. Do not forward-fill unavailable observations across an event boundary unless the rule is documented and economically justified.
9. Do not use future corporate actions, future index membership, or future source verification in historical features.
10. Freeze feature snapshots and source references so each historical signal can be reproduced.

If reliable point-in-time data does not exist for a feature, exclude it from historical performance claims. It may remain a clearly labeled live research field.

## 4. Label and outcome definitions

Labels must be defined before inspecting test results.

For market signals, define:
- Decision timestamp and executable reference price.
- Entry convention (next tradable bar/open or another predeclared executable rule).
- Fixed evaluation horizons by asset class (for example, 5, 20, and 60 trading sessions); do not select the best horizon after seeing results.
- Total-return treatment, including dividends, splits, contract rolls, funding and borrow costs where relevant.
- Benchmark-relative outcome and absolute outcome separately.
- Barrier/stop/target handling where intraperiod price paths are available.
- No-trade and unavailable-price handling.
- Delisting, suspension and stale-price handling.

For event and megatrend scores, use separate outcomes rather than forcing all outputs into a trading label. Candidate labels include subsequent verified capacity commissioning, contract execution, realized revenue contribution, production growth, supply disruption, and benchmark-relative beneficiary performance. The observation window and verification rules must be specified for each label.

A label is not valid merely because an asset price rose after an event. The causal mechanism and relevant confounders must be assessed.

## 5. Walk-forward evaluation design

Use chronological, rolling-origin evaluation. Random train/test splits are prohibited for time-dependent market data.

Recommended initial design, subject to available history:
- **Development window:** earliest 60% of eligible history.
- **Validation window:** next 20%, used only for model/threshold selection.
- **Locked test window:** final 20%, untouched until design and parameters are frozen.
- **Rolling-origin checks:** repeat with expanding or fixed-length training windows and sequential future test windows.
- **Purge/embargo:** remove overlapping label windows around split boundaries; embargo at least the maximum label horizon plus any relevant publication/settlement delay.
- **Regime slices:** report performance separately across predeclared volatility, liquidity, rate, inflation, and geopolitical regimes when sample sizes permit.

The percentages are an initial design template, not a guarantee of statistical power. If the data history or event count is too small, report the test as underpowered and do not relax controls to manufacture significance.

All hyperparameter selection, feature selection, threshold tuning, and score-weight changes must occur inside development/validation data. The locked test set may be evaluated only after the model specification is frozen. Any subsequent change creates a new model version and requires a new untouched test period.

## 6. Baselines and comparison

Compare each model against simple, relevant baselines:
- No-skill / base-rate benchmark.
- Buy-and-hold or passive asset benchmark where appropriate.
- Sector or asset-class benchmark.
- Simple momentum/trend baseline where relevant.
- Existing GRIOS heuristic version, if reproducibly versioned.

A more complex model must demonstrate incremental value over these baselines, not merely positive absolute returns in a favorable market.

## 7. Metrics

Select metrics before evaluation and match them to the output type.

### Classification / event detection
- Precision, recall, F1 and balanced accuracy.
- Precision-recall AUC for rare events.
- False-positive rate and missed-event rate.
- Lead time between first valid signal and confirmed event.

### Probability calibration
Only if the model emits probabilities:
- Brier score and log loss.
- Reliability diagrams and calibration slope/intercept.
- Expected calibration error, with binning and sample count disclosed.
- Calibration stability across time and regimes.

### Portfolio or trading outcomes
Only where an executable strategy is explicitly defined:
- Net return after transaction costs.
- Volatility and maximum drawdown.
- Sharpe/Sortino with stated annualization.
- Turnover, exposure, capacity and liquidity.
- Hit rate and payoff ratio, reported alongside the full return distribution.
- Benchmark-relative return and tracking error.

Always report confidence intervals or uncertainty estimates appropriate to the sample and dependence structure. Do not use a single point estimate as proof.

## 8. Costs, liquidity and execution assumptions

Backtests must include realistic, asset-specific:
- Bid/ask spread.
- Commissions and exchange fees.
- Slippage and market impact assumptions.
- Borrow availability and borrow fees for shorts.
- Funding, financing and roll costs where applicable.
- Trading hours, holidays, halts, price limits and minimum lot sizes.
- Liquidity and participation constraints.

If reliable historical spread/depth data is unavailable, do not claim executable net performance. Report gross research outcomes separately and label them non-executable.

## 9. Multiple testing and model selection

GRIOS may test many assets, themes, features, horizons and parameter sets. This creates selection bias.

- Maintain a registry of all tested model variants and hypotheses.
- Record every attempted configuration, including failed experiments.
- Predeclare primary outcomes and horizons.
- Control false discoveries where multiple hypotheses are tested.
- Use nested chronological validation for tuning.
- Do not select a model solely by the best backtest statistic.
- Treat repeated reuse of the locked test set as test contamination.

Any score-weight optimization requires a documented rationale, stability analysis, and a fresh out-of-sample evaluation.

## 10. Minimum publication gates

A model or score may be promoted from research heuristic only after all applicable gates pass:

1. **Data gate:** source provenance, point-in-time availability, freshness and missingness are measured.
2. **Identity gate:** instrument/entity resolution and corporate-action handling are validated.
3. **Leakage gate:** feature and label timestamps pass automated leakage tests.
4. **Reproducibility gate:** a fixed model version reproduces the same historical signal set and metrics.
5. **Baseline gate:** results are compared with relevant simple baselines.
6. **Out-of-sample gate:** at least one locked chronological test period and multiple rolling-origin folds are completed.
7. **Robustness gate:** results are not driven by one asset, one event, one regime or one parameter choice.
8. **Cost gate:** executable costs are included or results are explicitly labeled gross/non-executable.
9. **Calibration gate:** probability claims pass calibration diagnostics and are supported by adequate sample size.
10. **Governance gate:** limitations, contradictions, failure cases and invalidation conditions are documented and reviewed.

No universal minimum event count can guarantee validity. Each report must show the number of independent events, instruments, periods and effective observations. Sparse samples remain exploratory.

## 11. Monitoring after release

After any promotion:
- Monitor feature drift, data-source drift and outcome drift.
- Compare live feature distributions with the training reference.
- Track missingness, staleness, source outages and schema changes.
- Measure realized outcomes only after each label horizon matures.
- Reassess calibration on a rolling basis.
- Suspend probability language when calibration degrades or the data pipeline is compromised.
- Version every model, threshold and score-weight change.
- Keep a complete audit trail of model outputs and subsequent corrections.

A source outage or material schema change must downgrade affected signals to unavailable/unverified rather than silently reusing stale inputs.

## 12. Required validation report

Every validation release must publish:
1. Model and data version.
2. Assets, dates and sample counts.
3. Feature and label definitions.
4. Point-in-time and leakage controls.
5. Chronological split dates and embargo.
6. Baseline comparison.
7. Primary metrics and uncertainty intervals.
8. Transaction-cost and liquidity assumptions.
9. Regime and robustness analysis.
10. Failed tests and contradictory evidence.
11. Known limitations and intended use.
12. Approval status and next review date.

## 13. Status vocabulary

Use these terms consistently:
- **RESEARCH_HEURISTIC:** rule-based or weighted score not statistically calibrated.
- **BACKTESTED_EXPLORATORY:** chronological historical evaluation exists but publication gates are incomplete.
- **OUT_OF_SAMPLE_VALIDATED:** locked test and rolling-origin gates passed for the specified scope.
- **CALIBRATED:** probability outputs passed calibration gates on sufficient independent data.
- **SUSPENDED:** data, drift, leakage, or governance issue invalidates current use.

A status applies only to the named model version, asset universe, horizon and evaluation period. It must not be generalized to other instruments or market regimes.

---

**Core rule:** GRIOS must never convert a research score into a probability of profit without point-in-time evidence, chronological out-of-sample validation, calibration analysis, and explicit governance approval.
