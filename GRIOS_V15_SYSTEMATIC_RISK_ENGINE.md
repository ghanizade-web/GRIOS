# GRIOS v15 — SYSTEMATIC RISK ENGINE

## Institutional Framework for Portfolio Risk, Exposure Management, Drawdown Control & Systemic Risk Detection

**Project:** Ghanizadeh Research Intelligence Operating System  
**Version:** 15.0  
**Module:** Systematic Risk Engine  
**Status:** Core Module Specification  
**Mission:** We Track Capital Before The Crowd.

---

## 1. PURPOSE

The Systematic Risk Engine evaluates, quantifies, monitors, and controls financial risk across individual instruments, investment strategies, portfolios, sectors, and broader market exposures.

Its primary objectives are to:

- Measure portfolio and instrument-level risk.
- Identify concentration and correlated exposures.
- Monitor volatility and drawdown.
- Calculate Value at Risk (VaR) and Expected Shortfall (ES).
- Detect leverage and liquidity risks.
- Evaluate counterparty and funding risks.
- Monitor cross-asset contagion.
- Identify systemic vulnerabilities.
- Establish exposure limits and risk controls.
- Prevent unsupported investment signals from becoming actionable recommendations.

**Core principle:**

A high-conviction investment thesis is not sufficient if its risk cannot be measured, monitored, and controlled.

GRIOS must evaluate expected return and downside exposure together.

Risk management must operate independently of bullish or bearish analytical conviction.

## 2. RISK MANAGEMENT ARCHITECTURE

The engine shall operate across six levels.

### Level 1 — Instrument Risk

Evaluate:

- Price volatility
- Liquidity
- Spread
- Gap risk
- Leverage
- Market depth
- Execution risk

### Level 2 — Position Risk

Evaluate:

- Position size
- Entry exposure
- Stop-loss exposure
- Maximum loss
- Risk/reward
- Holding period
- Correlation with existing positions

### Level 3 — Portfolio Risk

Evaluate:

- Total exposure
- Net exposure
- Gross exposure
- Concentration
- Portfolio volatility
- Drawdown
- VaR
- Expected Shortfall

### Level 4 — Sector & Factor Risk

Evaluate:

- Sector concentration
- Geographic exposure
- Currency exposure
- Interest-rate sensitivity
- Commodity sensitivity
- Growth and value factors
- Momentum and volatility factors

### Level 5 — Counterparty & Funding Risk

Evaluate:

- Counterparty concentration
- Financing conditions
- Margin requirements
- Collateral quality
- Funding maturity
- Settlement risk

### Level 6 — Systemic Risk

Evaluate:

- Market-wide leverage
- Financial-system stress
- Liquidity deterioration
- Correlation breakdown
- Contagion channels
- Forced deleveraging risk

## 3. RISK TAXONOMY

Every risk record must be classified.

### 3.1 Market Risk

- Equity price risk
- Interest-rate risk
- Foreign-exchange risk
- Commodity price risk
- Credit spread risk
- Volatility risk

### 3.2 Liquidity Risk

- Market liquidity
- Funding liquidity
- Asset liquidation risk
- Bid-ask spread expansion
- Market depth deterioration

### 3.3 Credit & Counterparty Risk

- Default risk
- Counterparty exposure
- Settlement failure
- Credit deterioration
- Concentrated counterparty exposure

### 3.4 Leverage Risk

- Margin exposure
- Financing dependence
- Derivatives leverage
- Liquidation risk
- Refinancing risk

### 3.5 Concentration Risk

- Single-instrument concentration
- Sector concentration
- Geographic concentration
- Currency concentration
- Counterparty concentration
- Factor concentration

### 3.6 Operational & Model Risk

- Data-quality failures
- API interruptions
- Model error
- Calculation error
- Execution-system failure
- Incorrect assumptions

### 3.7 Geopolitical & Regulatory Risk

- Sanctions
- Export controls
- Political instability
- Regulatory changes
- Trade restrictions
- Strategic supply disruptions

## 4. PORTFOLIO EXPOSURE FRAMEWORK

The engine must calculate portfolio exposure using consistent definitions.

### Gross Exposure

The sum of absolute position exposures.

### Net Exposure

The signed sum of position exposures.

### Notional Exposure

The nominal market exposure of a position or instrument.

### Market Value Exposure

The current marked-to-market value of an investment.

### Leverage Ratio

Exposure must be compared with the relevant equity, capital, or collateral base.

The system must document the denominator used for every leverage calculation.

### Exposure Dimensions

Each position must be mapped across:

- Instrument
- Asset class
- Sector
- Industry
- Country
- Currency
- Issuer
- Counterparty
- Strategy
- Risk factor

Exposure aggregation must account for derivatives and nonlinear instruments rather than relying solely on market value.

## 5. POSITION SIZING & TRADE RISK

The engine must evaluate proposed position sizes before a trade is classified as actionable.

### Required Inputs

- Portfolio equity
- Instrument price
- Entry level
- Stop level, where technically supported
- Contract multiplier
- Currency conversion
- Estimated transaction costs
- Expected slippage
- Position direction

### Basic Position Sizing Formula

Risk Budget = Portfolio Equity × Risk Allocation Percentage

Position Quantity = Risk Budget / Estimated Loss Per Unit

Estimated loss per unit must include relevant multipliers, currency conversion, fees, and slippage assumptions.

For derivatives, options, leveraged products, and instruments with nonlinear payoffs, simple linear sizing must not be used without appropriate adjustment.

### Position Validation

Before approval, evaluate:

- Maximum loss
- Portfolio concentration
- Correlated exposure
- Liquidity
- Gap risk
- Stop execution uncertainty
- Funding requirements

A stop-loss does not guarantee the maximum loss during gaps or market dislocations.

## 6. VOLATILITY & DRAWDOWN ANALYSIS

The engine must monitor realized and implied volatility.

Required indicators:

- Daily realized volatility
- Weekly realized volatility
- Monthly realized volatility
- Annualized volatility
- Implied volatility
- Volatility percentile
- Volatility regime

### Drawdown

Drawdown measures the decline from a previous portfolio or asset peak.

Maximum Drawdown:

Maximum Drawdown = Maximum Peak-to-Trough Percentage Decline

Monitor:

- Current drawdown
- Maximum historical drawdown
- Drawdown duration
- Recovery period
- Peak-to-recovery duration
- Drawdown contribution by position

The system must distinguish realized drawdown from unrealized mark-to-market drawdown.

## 7. VALUE AT RISK (VaR)

The engine must support multiple VaR methodologies.

### 7.1 Historical VaR

Uses historical portfolio or instrument returns to estimate a loss threshold.

### 7.2 Parametric VaR

Uses statistical assumptions about return distributions and covariance.

### 7.3 Monte Carlo VaR

Uses simulated scenarios to estimate potential portfolio losses.

### Required Parameters

- Confidence level
- Holding period
- Historical observation window
- Return frequency
- Distribution assumptions
- Portfolio valuation timestamp
- Model version

Typical confidence levels may include:

- 95%
- 97.5%
- 99%

VaR must always specify the confidence level and holding period.

VaR is not a maximum-loss estimate. Losses may exceed the reported VaR threshold.

## 8. EXPECTED SHORTFALL (ES)

Expected Shortfall estimates the average loss conditional on losses exceeding the selected VaR threshold.

The engine must calculate ES using compatible methodology and assumptions.

Required outputs:

- VaR threshold
- Expected Shortfall
- Confidence level
- Holding period
- Historical window
- Methodology
- Data-quality status

Expected Shortfall must be reported alongside VaR where sufficient data exists.

## 9. CORRELATION & DIVERSIFICATION RISK

The engine must evaluate portfolio diversification dynamically.

Monitor:

- Pearson correlation
- Spearman correlation
- Rolling correlation
- Correlation matrix
- Tail dependence, where data permits
- Conditional correlation
- Correlation regime changes

### Key Analytical Requirements

- Identify hidden correlated exposures.
- Detect concentration across apparently different instruments.
- Measure correlation during stress periods.
- Evaluate diversification deterioration.
- Identify common macroeconomic risk factors.

Historical correlation must not be assumed to remain stable during market stress.

A portfolio containing multiple asset classes may still have concentrated exposure to the same underlying economic factor.

## 10. FACTOR & SENSITIVITY ANALYSIS

The engine must identify portfolio sensitivity to major risk factors.

Potential factors:

- Interest rates
- Real yields
- US dollar
- Inflation
- Oil prices
- Gold prices
- Credit spreads
- Equity market beta
- Volatility
- Liquidity
- Growth expectations

For relevant instruments, estimate:

- Beta
- Duration
- DV01
- Convexity
- Delta
- Gamma
- Vega
- Theta
- Rho

Only calculate metrics that are applicable to the instrument and supported by valid inputs.

Every sensitivity measure must identify its units and calculation assumptions.

## 11. LIQUIDITY & MARKET IMPACT RISK

The engine must evaluate the ability to enter or exit positions without excessive market impact.

Monitor:

- Average daily traded value
- Bid-ask spread
- Market depth
- Trading volume
- Turnover
- Order-book conditions, where available
- Historical slippage
- Estimated liquidation time

### Liquidity Risk Classification

**Low Risk**

Strong market depth and relatively stable execution conditions.

**Moderate Risk**

Some execution limitations or variable liquidity.

**High Risk**

Limited market depth, elevated spreads, or significant price impact.

**Critical Risk**

Severe liquidity impairment or unreliable execution conditions.

Liquidity classification must be instrument-specific and time-sensitive.

## 12. STRESS TESTING & SCENARIO ANALYSIS

The engine must run historical and hypothetical stress scenarios.

### Historical Scenarios

Where reliable historical data exists, test relevant events such as:

- Global financial crisis
- European sovereign debt stress
- COVID-19 market shock
- 2022 inflation and monetary tightening
- Major banking-sector stress episodes
- Significant commodity supply shocks

### Hypothetical Scenarios

Examples:

- Sudden Federal Reserve policy repricing
- Sharp US dollar appreciation
- Major Treasury yield spike
- Oil supply disruption
- Severe equity-market correction
- Credit-market freeze
- Banking liquidity crisis
- Geopolitical escalation
- Crypto-market deleveraging
- Cross-asset correlation shock

Each scenario must specify:

- Shock assumptions
- Affected risk factors
- Instrument-level impact
- Portfolio-level impact
- Liquidity implications
- Potential margin requirements
- Estimated drawdown
- Model limitations

Historical stress tests must not be treated as forecasts of future losses.

## 13. LEVERAGE, MARGIN & LIQUIDATION RISK

Monitor:

- Gross leverage
- Net leverage
- Derivatives notional
- Margin requirements
- Maintenance margin
- Collateral coverage
- Financing costs
- Margin utilization
- Liquidation thresholds

The engine must identify positions vulnerable to forced liquidation.

Where exact broker or counterparty margin requirements are unavailable, the system must not invent them.

Potential margin-call scenarios must be labeled as estimates.

## 14. CONCENTRATION RISK

The engine must identify exposures that exceed defined concentration limits.

Monitor:

- Single-stock exposure
- Single-sector exposure
- Single-country exposure
- Single-currency exposure
- Commodity concentration
- Counterparty concentration
- Strategy concentration
- Common-factor concentration

Concentration alerts must specify:

- Exposure amount
- Portfolio percentage
- Relevant limit
- Excess exposure
- Primary risk driver
- Recommended review action

Limits must be configurable by portfolio mandate and risk policy.

## 15. SYSTEMIC RISK & CONTAGION DETECTION

The engine must monitor risks that can propagate across financial institutions and asset markets.

Potential indicators:

- Credit spread widening
- Funding-market stress
- Banking-sector deterioration
- Sovereign risk repricing
- Elevated volatility
- Correlation convergence
- Market depth deterioration
- Derivatives leverage
- Cross-currency funding stress
- Forced deleveraging indicators

### Contagion Channels

- Banking system to credit markets
- Credit markets to equities
- Sovereign debt to bank balance sheets
- Dollar funding to emerging markets
- Commodity shocks to inflation and rates
- Derivatives exposure to underlying markets
- Crypto leverage to digital-asset liquidity

The engine must distinguish isolated market volatility from evidence of systemic stress.

## 16. RISK LIMITS & ALERT ENGINE

The system must support configurable limits.

Examples:

- Maximum single-position exposure
- Maximum sector exposure
- Maximum gross leverage
- Maximum net exposure
- Maximum portfolio volatility
- Maximum drawdown threshold
- Maximum VaR
- Maximum Expected Shortfall
- Maximum counterparty exposure
- Minimum liquidity requirements

### Alert Severity

**Information**

Relevant risk changes without an immediate threshold breach.

**Warning**

Risk approaching a defined limit.

**High**

Material limit breach or significant deterioration.

**Critical**

Severe risk exposure, liquidity impairment, or potential systemic instability.

Every alert must include:

- Trigger
- Observation timestamp
- Source
- Current value
- Threshold
- Severity
- Affected exposures
- Required review action

The system must not execute trades or liquidate positions automatically unless a separately authorized execution system explicitly permits it.

## 17. RISK SCORING MODEL

The engine shall calculate a Systematic Risk Condition Score.

| Component | Weight |
|---|---:|
| Market & Volatility Risk | 15% |
| Portfolio Concentration | 15% |
| Liquidity & Execution Risk | 15% |
| Leverage & Margin Risk | 15% |
| Correlation & Factor Risk | 15% |
| Credit & Counterparty Risk | 10% |
| Drawdown & Tail Risk | 10% |
| Data Quality & Model Reliability | 5% |
| **Total** | **100%** |

### Classification

- 85–100: Critical Risk Conditions
- 70–84: High Risk Conditions
- 55–69: Elevated Risk Conditions
- 40–54: Moderate Risk Conditions
- 0–39: Lower Measured Risk Conditions

The score represents risk severity, not investment attractiveness.

Higher scores indicate more severe measured risk.

### Scoring Rules

- Missing data must not be interpreted as low risk.
- Stale data must reduce confidence.
- Severe liquidity or counterparty stress may override an aggregate score.
- Concentration and leverage breaches must remain independently visible.
- Score and confidence must remain separate.
- Every score must include component-level explanations.

## 18. RISK-ADJUSTED OPPORTUNITY VALIDATION

Before an investment opportunity receives final approval, the engine must evaluate:

- Expected return assumptions
- Maximum estimated loss
- Risk/reward
- Volatility
- Liquidity
- Correlation with existing exposure
- Portfolio contribution to risk
- Stress-scenario performance
- Invalidation conditions

The engine must distinguish:

- Attractive opportunity
- Attractive opportunity with excessive portfolio risk
- Insufficient risk information
- Unacceptable risk exposure

A high Signal Scoring result must never override a critical risk-control alert.

## 19. INTEGRATION WITH GRIOS v15

### Data Intelligence & Validation Engine

Validates risk inputs, return series, timestamps, and calculation integrity.

### API Source Registry

Provides approved data sources, freshness information, and source health.

### Global Liquidity Engine

Provides funding and liquidity regime information.

### Cross-Asset Transmission Engine

Provides macroeconomic shock scenarios and cross-market transmission paths.

### Institutional Positioning Engine

Provides leverage, crowding, and positioning-risk evidence.

### Smart Money Tracking Engine

Provides verified capital-allocation and institutional exposure evidence.

### Megatrend Discovery Engine

Provides structural sector and industry exposure.

### Signal Scoring Engine

Provides ranked investment opportunities.

The Systematic Risk Engine evaluates whether those opportunities are acceptable under the relevant risk mandate.

## 20. STANDARD OUTPUT SCHEMA

Every risk record must contain:

- Risk Record ID
- Portfolio ID
- Instrument
- Asset class
- Position direction
- Position quantity
- Market value
- Notional exposure
- Currency
- Sector
- Country
- Risk factor exposure
- Volatility
- Beta
- Correlation
- Current drawdown
- Historical maximum drawdown
- VaR
- Expected Shortfall
- Leverage
- Liquidity classification
- Counterparty exposure
- Stress-test results
- Risk-limit status
- Systematic Risk Condition Score
- Confidence
- Source references
- Calculation timestamp
- Model version

Portfolio-level reports must additionally include:

- Gross exposure
- Net exposure
- Total leverage
- Portfolio volatility
- Portfolio VaR
- Portfolio Expected Shortfall
- Maximum drawdown
- Concentration analysis
- Correlation matrix
- Factor exposures
- Stress scenarios
- Risk-limit breaches
- Critical alerts

## 21. OPERATIONAL WORKFLOW

The standard workflow is:

1. Retrieve portfolio and instrument exposure data.
2. Validate prices and valuation timestamps.
3. Normalize currencies and instrument units.
4. Calculate position and notional exposures.
5. Calculate volatility and drawdown.
6. Estimate VaR and Expected Shortfall.
7. Evaluate correlation and factor exposures.
8. Measure leverage and margin utilization.
9. Assess market liquidity and execution risk.
10. Evaluate counterparty exposure.
11. Run stress tests.
12. Detect concentration and systemic vulnerabilities.
13. Compare exposure against risk limits.
14. Calculate the Systematic Risk Condition Score.
15. Review investment opportunities under risk constraints.
16. Generate alerts and risk reports.
17. Preserve calculation and decision history.

## 22. DATA GOVERNANCE & MODEL VALIDATION

The engine must preserve:

- Original data
- Historical return series
- Valuation timestamps
- Calculation methodology
- Model assumptions
- Risk-limit configuration
- Scenario definitions
- Historical score changes
- Backtesting results
- Model versions
- Validation records

### Model Validation Requirements

- VaR backtesting
- Expected Shortfall validation
- Stress-test review
- Sensitivity analysis
- Data-quality checks
- Parameter stability assessment
- Correlation-model review
- Model limitation documentation

The engine must identify situations where the model is unsuitable or where input data is insufficient.

## 23. FINAL OPERATING PRINCIPLE

GRIOS must not recommend an investment solely because its fundamentals, capital flows, or technical structure appear attractive.

Every opportunity must be evaluated against portfolio exposure, liquidity, leverage, correlation, downside risk, and stress conditions.

The engine must answer:

1. How much capital is exposed?
2. Where is the risk concentrated?
3. How much can the portfolio lose under defined scenarios?
4. What happens when correlations converge?
5. Can positions be liquidated under stress?
6. Is leverage creating forced-selling vulnerability?
7. Which limits are approaching or breached?
8. Does the expected return justify the measured risk?
9. What conditions invalidate the risk assessment?

**GRIOS v15 Objective:**

Protect capital, quantify uncertainty, identify hidden exposure, and ensure that investment opportunities remain compatible with institutional risk discipline.

**We Track Capital Before The Crowd.**
