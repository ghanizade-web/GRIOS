# GRIOS v15 — Institutional Signal Scoring Engine

**Project:** Ghanizadeh Research Intelligence Operating System  
**Version:** 15.0 Institutional Edition  
**Module:** Signal Scoring & Opportunity Ranking  
**Status:** Core Analytical Specification  
**Mission:** We Track Capital Before The Crowd.

---

## 1. Purpose

The GRIOS Signal Scoring Engine transforms validated market, macroeconomic, geopolitical, corporate, and institutional capital-flow data into ranked investment opportunities.

Its purpose is to identify opportunities with favorable evidence, catalysts, market structure, and risk characteristics.

The engine must distinguish between:

- Market observations
- Developing investment themes
- Confirmed catalysts
- Actionable trading setups
- Long-term investment opportunities
- Unverified market narratives

A high score does not guarantee a profitable investment.

The scoring engine is a decision-support mechanism, not an autonomous trading system.

## 2. Core Design Principles

1. Evidence must precede conviction.
2. Capital allocation must be distinguished from market speculation.
3. A catalyst must have a plausible transmission mechanism.
4. Risk must directly affect opportunity ranking.
5. Data freshness and source reliability must influence confidence.
6. Contradictory evidence must reduce the score.
7. No opportunity may receive a high-confidence classification solely because of price momentum.
8. Every actionable thesis must have an invalidation condition.
9. Missing data must never be interpreted as positive evidence.
10. Scores must be reproducible and explainable.

## 3. Signal Categories

Every signal must belong to one of the following categories:

### A. LONG
Evidence supports a potential upward opportunity.

### B. SHORT
Evidence supports a potential downward opportunity.

### C. WATCH
A relevant opportunity exists, but activation conditions are incomplete.

### D. AVOID
Risk, valuation, deteriorating fundamentals, or contradictory evidence makes the opportunity unattractive.

### E. UNCONFIRMED
The underlying information has not passed minimum verification requirements.

### F. LONG-TERM STRUCTURAL OPPORTUNITY
A strategic investment theme supported by durable demand, capital expenditure, supply constraints, or technological adoption.

These categories must not be treated as interchangeable.

## 4. Scoring Architecture

The default opportunity score is calculated using seven components.

| Component | Weight |
|---|---:|
| Evidence & Source Quality | 20 |
| Smart Money & Capital Flows | 20 |
| Fundamental & Megatrend Strength | 15 |
| Catalyst Strength | 15 |
| Market Structure & Technical Confirmation | 15 |
| Risk/Reward & Invalidation Quality | 10 |
| Data Freshness & Cross-Source Confirmation | 5 |
| **Total** | **100** |

Each component receives a score from 0 to 100.

The weighted score is:

Weighted Score = Σ(Component Score × Component Weight) / 100

The result ranges from 0 to 100.

### Important

A component with insufficient evidence must be marked as MISSING or UNAVAILABLE.

Missing information must not automatically receive a score of zero or be treated as neutral evidence without an explicit missing-data policy.

The system must report both the calculated score and the percentage of scoring weight supported by valid evidence.

## 5. Component Definitions

### 5.1 Evidence & Source Quality — 20%

Evaluate:

- Official regulatory disclosures
- Company financial statements
- Government publications
- Verified institutional reports
- Independent corroboration
- Evidence consistency
- Source credibility

Official filings and confirmed contracts carry more evidential weight than anonymous claims or social media speculation.

### 5.2 Smart Money & Capital Flows — 20%

Evaluate:

- Institutional fund flows
- Verified ownership changes
- Insider transactions
- Sovereign wealth fund activity
- Corporate investment
- Strategic acquisitions
- Capital expenditure
- Procurement agreements
- Long-term supply contracts

Different transaction types must remain separately classified.

Fund ownership does not automatically represent proprietary investment by the asset manager.

### 5.3 Fundamental & Megatrend Strength — 15%

Evaluate:

- Structural demand growth
- Supply constraints
- Pricing power
- Industry margins
- Competitive advantages
- Technological necessity
- Regulatory support
- Long-term capital requirements
- Substitution risk

Priority monitoring themes include:

- AI infrastructure
- Semiconductors and HBM
- Data centers
- Electricity and grid infrastructure
- Nuclear energy and uranium
- Copper and strategic minerals
- Energy storage
- Robotics and autonomous systems
- Aerospace and defense
- Industrial automation

### 5.4 Catalyst Strength — 15%

Evaluate the existence, timing, and expected impact of:

- Earnings announcements
- Regulatory decisions
- Central-bank decisions
- Government contracts
- M&A transactions
- Supply disruptions
- New production capacity
- Product launches
- Strategic investments
- Geopolitical developments

A catalyst must have an identifiable mechanism linking it to the relevant asset.

### 5.5 Market Structure & Technical Confirmation — 15%

Evaluate only when reliable market data is available:

- Trend structure
- Break of structure
- Higher highs and lower lows
- Support and resistance
- Volume confirmation
- Liquidity zones
- Volatility regime
- Order-flow evidence
- Relative strength
- Momentum divergence

Technical data must be instrument-specific and timestamped.

Never invent order-flow, volume, support, resistance, or liquidity levels.

If technical data is unavailable, mark the component as unavailable and reduce coverage accordingly.

### 5.6 Risk/Reward & Invalidation Quality — 10%

Evaluate:

- Potential upside versus downside
- Liquidity risk
- Valuation risk
- Leverage
- Geopolitical exposure
- Regulatory exposure
- Execution risk
- Thesis invalidation clarity

An opportunity with an attractive narrative but undefined downside must not receive a top-tier actionable classification.

### 5.7 Data Freshness & Cross-Source Confirmation — 5%

Evaluate:

- Timestamp validity
- Data update frequency
- API status
- Independent source confirmation
- Conflicting observations
- Data completeness

Freshness requirements must be appropriate to the instrument and data type.

Intraday prices and quarterly financial disclosures require different freshness rules.

## 6. Score Interpretation

| Score | Classification | Meaning |
|---|---|---|
| 85–100 | Tier 1 | Highest-priority research candidate |
| 70–84 | Tier 2 | Strong opportunity requiring review |
| 55–69 | Tier 3 | Developing opportunity |
| 40–54 | Tier 4 | Weak or incomplete opportunity |
| 0–39 | Tier 5 | Low-priority opportunity |

These ranges rank research priority. They do not represent probabilities of profit.

### Mandatory Qualification Gates

A high numerical score cannot override the following restrictions:

- Unverified material claims cannot qualify as confirmed catalysts.
- Stale critical data prevents an actionable signal.
- Missing invalidation conditions prevent an actionable trade classification.
- Insufficient technical evidence prevents technical-entry recommendations.
- Material contradictory evidence must be disclosed.
- A serious liquidity or execution constraint must be highlighted.

A signal may have a high research score while remaining WATCH rather than LONG or SHORT.

## 7. Confidence Classification

Confidence is separate from the opportunity score.

### HIGH
Multiple reliable and independent sources support the thesis, with no unresolved critical contradiction.

### MEDIUM
Credible evidence exists, but important uncertainties remain.

### LOW
Evidence is limited, incomplete, or materially conflicting.

### UNCONFIRMED
The thesis depends on information that has not been adequately verified.

The system must never equate a score of 90 with a 90% probability of success.

## 8. Opportunity Horizon

Each signal must specify its intended horizon:

- Intraday: Within the trading session.
- Short-term: Several sessions to several weeks.
- Medium-term: Several weeks to several months.
- Long-term: Several months to multiple years.
- Structural: A multiyear industrial or technological transformation.

Signals with different horizons must not be ranked as if their objectives and risk profiles were identical.

## 9. Signal Activation Requirements

A WATCH signal can become actionable only after its required activation conditions are satisfied.

Examples:

- Confirmed technical breakout
- Volume confirmation
- Official contract disclosure
- Verified institutional flow
- Earnings confirmation
- Macro regime confirmation
- Successful support retest
- Defined risk/reward structure

The activation requirements must be defined before the signal is promoted.

## 10. Invalidation Engine

Every signal must identify what would make its thesis incorrect.

Examples:

- Demand forecasts deteriorate.
- Supply capacity expands faster than expected.
- A strategic contract is cancelled.
- Institutional flows reverse.
- A technical structure breaks.
- Regulatory approval is rejected.
- Valuation exceeds defensible assumptions.
- The expected catalyst fails to materialize.

Invalidation conditions must be measurable whenever possible.

## 11. Signal Record Schema

Every signal should be stored in a structured format.

```json
{
  "signal_id": "GRIOS-YYYYMMDD-001",
  "asset": "TICKER_OR_ASSET",
  "asset_class": "equity",
  "sector": "sector_name",
  "direction": "WATCH",
  "horizon": "medium_term",
  "weighted_score": null,
  "coverage_percentage": null,
  "confidence": "MEDIUM",
  "evidence_score": null,
  "smart_money_score": null,
  "fundamental_score": null,
  "catalyst_score": null,
  "technical_score": null,
  "risk_reward_score": null,
  "freshness_score": null,
  "catalyst": [],
  "activation_conditions": [],
  "invalidation_conditions": [],
  "sources": [],
  "created_at": null,
  "updated_at": null,
  "status": "PENDING_VALIDATION"
}
```

Null values must remain null until supported by data.

## 12. Ranking and Prioritization

The engine should rank opportunities using:

1. Evidence quality
2. Structural importance
3. Capital-flow confirmation
4. Catalyst proximity
5. Market confirmation
6. Risk-adjusted attractiveness
7. Data reliability

The ranking process must be reproducible.

A score change must be traceable to a changed input, new evidence, revised weighting, or updated methodology.

## 13. Anti-Bias and Contradiction Controls

The engine must actively search for:

- Confirmation bias
- Recency bias
- Survivorship bias
- Narrative bias
- Correlation mistaken for causation
- Double counting of the same evidence
- Conflicts of interest
- Outdated institutional disclosures

The same transaction reported by multiple media outlets must not be counted as multiple independent capital-flow events.

## 14. Daily Output

The daily opportunity table should include:

| Asset | Direction | Score | Confidence | Horizon | Status |
|---|---|---:|---|---|---|
| Asset A | WATCH | Pending | MEDIUM | Medium | Awaiting trigger |
| Asset B | LONG | Pending | HIGH | Long | Conditional |
| Asset C | SHORT | Pending | LOW | Short | High risk |

Illustrative rows only. Actual scores must be calculated from validated data.

Each published opportunity must include a short explanation of the evidence, catalyst, activation, risk, and invalidation.

## 15. Governance and Versioning

The scoring engine must maintain:

- Methodology version
- Weight configuration
- Input data timestamps
- Source references
- Calculation history
- Manual overrides
- Override justification
- Historical signal outcomes

Changes to scoring weights must be documented and version-controlled.

Backtesting must avoid look-ahead bias and survivorship bias.

Performance evaluation should include transaction costs, slippage, drawdowns, and benchmark comparisons where applicable.

## 16. Core Rule

GRIOS does not rank opportunities by how exciting their narratives sound.

It ranks opportunities by the quality of evidence, strength of capital allocation, durability of the underlying thesis, identifiable catalysts, market confirmation, and risk discipline.

**GRIOS v15 — We Track Capital Before The Crowd.**
