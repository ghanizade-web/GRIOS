# GRIOS_V15_PERFORMANCE_ATTRIBUTION_AND_PORTFOLIO_MONITORING_ENGINE.md

# GRIOS v15 — Performance Attribution & Portfolio Monitoring Engine

## 1. Mission

Build an institutional-grade performance measurement, attribution, and portfolio monitoring system that evaluates the actual outcomes of GRIOS investment decisions.

The engine must measure not only whether a portfolio generated positive or negative returns, but also:

- Why the return occurred.
- Which allocation decisions created or destroyed value.
- Which securities and strategies contributed to performance.
- Whether risk-adjusted performance justified the capital allocated.
- Whether actual portfolio exposures remained aligned with target allocations.
- Whether GRIOS signals produced measurable investment value over time.

**Core principle: Every investment decision must generate measurable evidence that can improve future decisions.**

## 2. Strategic Objectives

1. Measure portfolio performance across multiple time horizons.
2. Separate asset allocation effects from security selection and timing effects.
3. Compare realized performance against appropriate benchmarks.
4. Track realized and unrealized profit and loss.
5. Monitor portfolio drift, concentration, and risk-limit violations.
6. Evaluate the historical effectiveness of GRIOS signals.
7. Measure strategy-level and asset-class-level performance.
8. Feed validated performance evidence back into GRIOS intelligence engines.
9. Maintain an auditable history of investment decisions and outcomes.
10. Distinguish actual portfolio performance from simulated and backtested results.

## 3. Input Architecture

The engine must consume data from:

- Portfolio Intelligence & Allocation Engine
- Systematic Risk Engine
- Signal Scoring Engine
- Institutional Positioning Engine
- Smart Money Tracking Engine
- Cross-Asset Transmission Engine
- Global Liquidity Engine
- Event Catalyst Engine
- API Source Registry
- Data Intelligence & Validation Engine

Additional required inputs:

- Portfolio holdings and position quantities
- Entry prices and transaction timestamps
- Current and historical market prices
- Cash balances and cash movements
- Dividends, coupons, distributions, and corporate actions
- Deposits and withdrawals
- Trading commissions and execution costs
- Currency conversion rates
- Benchmark returns and constituent weights
- Portfolio target allocations
- Historical risk measurements

All performance calculations must retain source, timestamp, currency, and data-quality metadata.

Missing transaction history must not be silently replaced with estimated performance.

## 4. Performance Measurement Framework

Support the following performance metrics:

### Return Metrics
- Daily Return
- Weekly Return
- Monthly Return
- Quarterly Return
- Annual Return
- Year-to-Date Return
- Cumulative Return
- Annualized Return

### Risk-Adjusted Metrics
- Sharpe Ratio
- Sortino Ratio
- Calmar Ratio
- Information Ratio
- Treynor Ratio
- Jensen's Alpha

### Risk Metrics
- Annualized Volatility
- Maximum Drawdown
- Current Drawdown
- Drawdown Duration
- Recovery Time
- Beta
- Tracking Error
- Value at Risk
- Expected Shortfall

### Trading and Portfolio Metrics
- Win Rate
- Average Win
- Average Loss
- Profit Factor
- Turnover
- Average Holding Period
- Transaction Costs
- Exposure Utilization
- Cash Allocation
- Hit Rate by Signal Category

Metric definitions, annualization conventions, observation windows, and benchmark assumptions must be documented.

## 5. Performance Attribution Engine

Identify the sources of portfolio returns.

### A. Asset Allocation Attribution

Measure the contribution of allocation decisions across:

- Asset classes
- Geographic markets
- Sectors
- Industries
- Thematic exposures
- Investment strategies

Determine whether overweighting or underweighting specific portfolio segments added or reduced value relative to the benchmark.

### B. Security Selection Attribution

Measure the impact of selecting individual securities, ETFs, commodities, and other instruments within their respective allocation groups.

### C. Interaction Effect

Measure the combined impact of allocation and selection decisions where the selected attribution methodology requires it.

### D. Currency Attribution

Separate the impact of local asset performance from foreign-exchange movements.

### E. Timing Attribution

Evaluate the contribution of entry timing, exit timing, and rebalancing decisions.

### F. Cost Attribution

Identify the impact of:

- Commissions
- Bid-ask spreads
- Slippage
- Financing costs
- Borrowing costs
- Management fees, where available
- Other applicable transaction expenses

Attribution methodologies must be explicitly identified. Brinson-style attribution may be used for suitable benchmark-relative portfolios, while absolute-return strategies may require transaction-based or position-level attribution.

Attribution components must reconcile to total portfolio performance within documented calculation tolerances.

## 6. Benchmark Intelligence

Support appropriate benchmark selection for each portfolio mandate.

Examples include:

- Broad equity indices
- Regional equity indices
- Sector indices
- Government bond indices
- Commodity benchmarks
- Cryptocurrency benchmarks
- Cash or risk-free reference rates
- Custom blended benchmarks

For every portfolio, define:

- Benchmark identity
- Benchmark currency
- Benchmark weighting methodology
- Rebalancing methodology
- Measurement period
- Data source
- Benchmark suitability

The engine must prevent misleading comparisons between portfolios and inappropriate benchmarks.

## 7. Realized and Unrealized P&L

Track performance at both portfolio and position level.

### Realized P&L
Measure gains and losses from closed positions, accounting for transaction costs and applicable cash flows.

### Unrealized P&L
Measure changes in the market value of open positions relative to their documented cost basis.

### Additional Accounting Considerations

Support:

- Dividends and distributions
- Coupon payments
- Interest income
- Funding costs
- Corporate actions
- Split and reverse-split adjustments
- Deposits and withdrawals
- Multi-currency accounting

Use a clearly documented cost-basis methodology, such as FIFO, weighted average cost, or another mandate-defined method.

Do not confuse deposits and withdrawals with investment returns.

## 8. Portfolio Drift Monitoring

Continuously compare actual holdings and weights against target allocations.

Monitor:

- Asset-class drift
- Sector drift
- Geographic drift
- Individual position drift
- Currency exposure drift
- Thematic concentration
- Cash allocation deviations
- Risk-budget deviations

Generate monitoring events when predefined thresholds are breached.

Each alert must include:

- Current allocation
- Target allocation
- Absolute deviation
- Relative deviation, where meaningful
- Risk implications
- Suggested review action
- Alert timestamp

The engine must distinguish between ordinary market-driven drift and changes caused by portfolio transactions.

## 9. Signal Performance Tracking

Evaluate the historical effectiveness of GRIOS investment signals.

Track:

- LONG signal outcomes
- SHORT signal outcomes
- WATCH signal conversion
- Signal invalidation frequency
- Average return after activation
- Maximum favorable excursion
- Maximum adverse excursion
- Time to target, where defined
- Time to invalidation
- Performance by signal score tier
- Performance by confidence level
- Performance by asset class
- Performance by market regime
- Performance by investment horizon

Every signal must retain:

- Original timestamp
- Instrument and direction
- Entry or activation conditions
- Stop and target assumptions, if defined
- Signal score
- Confidence level
- Data quality at issuance
- Invalidation conditions
- Outcome evaluation methodology

Avoid look-ahead bias. A signal must be evaluated using only information available at the time it was generated.

WATCH signals must not be treated as executed trades unless an explicit activation and execution record exists.

## 10. Strategy and Model Performance

Measure the performance of different GRIOS strategies and analytical engines.

Examples:

- Macro strategies
- Momentum strategies
- Mean-reversion strategies
- Trend-following strategies
- Event-driven strategies
- Thematic strategies
- Cross-asset strategies
- Defensive and hedging strategies
- Long-term strategic allocation
- Tactical asset allocation

Track:

- Strategy returns
- Risk-adjusted returns
- Drawdown
- Turnover
- Capacity and liquidity constraints
- Benchmark-relative performance
- Performance consistency
- Market-regime sensitivity

Separate strategy performance from the performance of the overall portfolio.

Do not attribute a portfolio outcome to a particular engine unless a traceable decision or exposure link exists.

## 11. Drawdown and Recovery Intelligence

Monitor portfolio losses and recovery dynamics.

Calculate:

- Maximum Drawdown
- Current Drawdown
- Drawdown Duration
- Peak-to-Trough Loss
- Recovery Duration
- Recovery Return Required
- Historical Drawdown Distribution

Generate alerts when drawdown thresholds are approached or breached.

Analyze whether drawdowns originated from:

- Market-wide exposure
- Sector concentration
- Security selection
- Leverage
- Currency movements
- Correlation breakdown
- Liquidity stress
- Execution costs
- Unexpected event catalysts

Recovery analysis must not imply that historical recovery patterns guarantee future recovery.

## 12. Risk-Adjusted Performance Evaluation

Evaluate whether portfolio returns adequately compensate for the risk assumed.

Assess:

- Sharpe Ratio
- Sortino Ratio
- Calmar Ratio
- Information Ratio
- Beta-adjusted performance
- Downside volatility
- Expected Shortfall
- Maximum Drawdown
- Risk contribution by position and strategy

Compare portfolios using consistent measurement windows and assumptions.

A portfolio with higher nominal returns must not automatically be classified as superior if its risk exposure is materially higher.

## 13. Performance Alerts and Monitoring

Create configurable alert categories.

### Performance Alerts
- Benchmark underperformance
- Negative rolling returns
- Declining risk-adjusted performance
- Strategy deterioration
- Excessive turnover

### Risk Alerts
- Drawdown threshold breach
- Volatility expansion
- Concentration limit breach
- Unexpected correlation increase
- Liquidity deterioration
- Risk-budget violation

### Allocation Alerts
- Target allocation deviation
- Position size deviation
- Cash allocation deviation
- Sector concentration increase
- Rebalancing threshold breach

### Data Alerts
- Missing transaction records
- Stale market prices
- Corporate-action mismatch
- Inconsistent benchmark data
- Currency conversion errors
- Unreconciled portfolio valuation

Alerts must be prioritized according to severity and potential portfolio impact.

## 14. Performance Attribution Score

Create a Performance Attribution Quality Score from 0 to 100 to evaluate the reliability and completeness of the measurement process.

Proposed weighting:

| Component | Weight |
|---|---:|
| Transaction and Position Data Quality | 20% |
| Return Calculation Integrity | 20% |
| Benchmark Suitability | 15% |
| Attribution Reconciliation | 15% |
| Corporate Action and Cash Flow Accuracy | 10% |
| Cost and Execution Coverage | 10% |
| Timestamp and Data Freshness | 10% |

Interpretation:

- 85–100: High measurement reliability
- 70–84: Good measurement reliability
- 55–69: Partial reliability; review required
- 40–54: Weak measurement reliability
- 0–39: Insufficient evidence for reliable attribution

This score evaluates measurement quality, not investment performance.

Investment performance and measurement confidence must be reported separately.

## 15. Feedback and Continuous Improvement

Create a controlled feedback loop.

Performance outcomes should inform:

- Signal Scoring Engine calibration
- Portfolio Intelligence & Allocation Engine
- Systematic Risk Engine
- Strategy evaluation
- Market-regime classification
- Asset-class allocation research
- Investment horizon assessment

The engine must identify:

- Repeatedly successful signal conditions
- Persistent sources of underperformance
- Strategies sensitive to specific market regimes
- Unreliable data sources
- Excessive portfolio concentration
- Allocation decisions with poor risk-adjusted outcomes

Historical results may support model improvement but must not automatically modify model weights or investment rules without validation, versioning, and governance approval.

## 16. Reporting and Dashboards

Generate institutional reporting views.

### Executive Portfolio Dashboard
- Portfolio value
- Daily and cumulative return
- Benchmark-relative return
- Current drawdown
- Risk-adjusted performance
- Asset allocation
- Cash and liquidity
- Top contributors
- Top detractors
- Active alerts

### Attribution Dashboard
- Allocation effect
- Selection effect
- Currency effect
- Timing effect
- Cost effect
- Strategy contribution

### Monitoring Dashboard
- Target versus actual allocation
- Position-level P&L
- Sector and geographic exposure
- Risk-budget utilization
- Rebalancing alerts

### Strategy Intelligence Dashboard
- Strategy performance
- Signal effectiveness
- Market-regime performance
- Drawdown history
- Benchmark comparison

### Reporting Frequency
- Daily monitoring
- Weekly performance review
- Monthly attribution report
- Quarterly strategic review
- Annual performance assessment

Reports must distinguish live, delayed, manually supplied, simulated, and historical data.

## 17. Data Model

Core entities:

- Portfolio Performance Snapshot
- Portfolio Valuation
- Position Performance
- Realized P&L Record
- Unrealized P&L Record
- Cash Flow Record
- Transaction Cost Record
- Benchmark Performance
- Attribution Record
- Allocation Drift Record
- Signal Outcome
- Strategy Performance
- Drawdown Event
- Performance Alert
- Corporate Action Record
- Performance Audit Log

Every record must include:

- Unique identifier
- Portfolio or strategy reference
- Instrument reference, where applicable
- Measurement timestamp
- Reporting currency
- Data source
- Calculation methodology
- Model version
- Validation status

## 18. Integration Architecture

Portfolio Intelligence & Allocation Engine
→ Target Allocations and Portfolio Decisions

Systematic Risk Engine
→ Risk Budgets and Exposure Constraints

Market Data and API Source Registry
→ Prices, Benchmarks, FX, and Corporate Actions

Data Intelligence & Validation Engine
→ Data Integrity and Quality Controls

Performance Attribution Engine
→ Actual Return and Decision Attribution

Signal Scoring Engine
→ Historical Signal Effectiveness

Smart Money Tracking Engine
→ Capital Flow and Institutional Context

GRIOS Daily Market & Investment Intelligence
→ Executive Performance Reporting

Validated performance observations
→ Controlled feedback to relevant GRIOS engines

## 19. Governance and Model Controls

- Actual, simulated, and backtested performance must remain separate.
- Performance calculations must be reproducible.
- Benchmark methodology must be documented.
- External cash flows must be separated from investment returns.
- All corporate actions must be accounted for.
- Missing or unreliable records must reduce measurement confidence.
- Attribution must reconcile to total returns within defined tolerances.
- Backtests must account for survivorship bias, look-ahead bias, and transaction costs.
- Strategy comparisons must use consistent measurement periods.
- Model recalibration must require validation and version control.
- Historical performance must never be presented as a guarantee of future results.

## 20. Final Operating Principle

GRIOS must measure the consequences of its investment decisions with the same discipline used to generate those decisions.

The engine must establish a traceable relationship between:

**Evidence → Signal → Portfolio Decision → Capital Allocation → Realized Outcome → Performance Attribution → Model Improvement**

The ultimate objective is to create a continuously improving institutional intelligence system in which every investment decision can be evaluated, explained, and used to strengthen future capital allocation.

**GRIOS does not merely track market performance. It measures the quality of its own investment decisions.**
