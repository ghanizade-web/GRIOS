# GRIOS v15 — INSTITUTIONAL POSITIONING ENGINE

## Institutional Framework for Futures Positioning, Options Exposure, Dealer Gamma & Market Crowding

**Project:** Ghanizadeh Research Intelligence Operating System  
**Version:** 15.0  
**Module:** Institutional Positioning Engine  
**Status:** Core Module Specification  
**Mission:** We Track Capital Before The Crowd.

---

## 1. PURPOSE

The Institutional Positioning Engine identifies, measures, and monitors the positioning, exposure, concentration, and potential behavioral constraints of major market participants.

Its primary objectives are to:

- Monitor institutional futures positioning.
- Analyze speculative and commercial positioning.
- Track asset-manager and leveraged-fund exposure.
- Evaluate options-market positioning.
- Analyze dealer gamma exposure.
- Detect crowded trades and positioning extremes.
- Identify potential short squeezes and long liquidations.
- Monitor changes in institutional ownership.
- Compare positioning with price action and market structure.
- Identify divergences between positioning, fundamentals, and liquidity.

The engine must distinguish reported positions, inferred exposures, estimated dealer positioning, and actual capital flows.

**Core principle:**

Positioning data describes exposure, not necessarily investment conviction. A large position does not independently establish directional intent, and a positioning extreme does not guarantee an imminent reversal.

## 2. PARTICIPANT CLASSIFICATION

The system must classify market participants according to the source methodology.

### 2.1 Futures Market Participants

Where available, monitor:

- Asset Managers
- Leveraged Funds
- Dealers
- Swap Dealers
- Producers and Merchants
- Commercial Hedgers
- Other Reportable Traders
- Nonreportable Traders

The classification must follow the relevant exchange or regulatory reporting methodology.

### 2.2 Options Market Participants

Analyze:

- Market makers
- Dealers
- Institutional options traders
- Asset managers
- Volatility-focused funds
- Retail options activity, where reliable data exists

Participant classifications must not be inferred when the underlying source does not provide them.

### 2.3 Equity Ownership Participants

Monitor:

- Mutual funds
- ETFs
- Pension funds
- Sovereign wealth funds
- Hedge funds
- Insurance companies
- Activist investors
- Corporate insiders

Distinguish beneficial ownership, reported holdings, voting rights, and economic exposure.

## 3. COMMITMENT OF TRADERS (COT) ANALYSIS

The engine must incorporate relevant CFTC Commitment of Traders reports.

Supported report types may include:

- Legacy Reports
- Disaggregated Reports
- Traders in Financial Futures Reports
- Futures Only
- Futures and Options Combined

The system must identify which report is appropriate for each market.

### Required Fields

- Market name
- Contract market
- Report date
- Publication date
- Report type
- Participant category
- Long positions
- Short positions
- Spreading positions, where applicable
- Open interest
- Number of traders, where available
- Changes from previous reporting period

### Positioning Calculations

**Net Position:**

Net Position = Long Positions − Short Positions

**Weekly Net Change:**

Weekly Net Change = Current Net Position − Previous Net Position

**Positioning as Percentage of Open Interest:**

Positioning Ratio = Net Position / Open Interest × 100

The system must preserve the original source units and report methodology.

### Analytical Questions

- Which participant categories are accumulating net long exposure?
- Which categories are increasing short exposure?
- Are commercial hedgers and leveraged funds positioned in opposite directions?
- Is positioning approaching historical extremes?
- Is open interest expanding alongside the position?
- Are price movements confirming or contradicting positioning changes?

## 4. POSITIONING EXTREMES & HISTORICAL PERCENTILES

The engine must evaluate current positioning relative to historical observations.

Required measures:

- Historical percentile
- Rolling 1-year percentile
- Rolling 3-year percentile
- Rolling 5-year percentile, where data permits
- Historical maximum
- Historical minimum
- Positioning z-score
- Position concentration relative to open interest

### Z-Score

The positioning z-score may be calculated as:

Z = (Current Position − Historical Mean) / Historical Standard Deviation

The lookback window and methodology must be recorded.

### Interpretation

- Extreme net long positioning may indicate crowded bullish exposure.
- Extreme net short positioning may indicate crowded bearish exposure.
- Rapid positioning changes may indicate a transition in market participation.
- Divergence between positioning and price may indicate weakening confirmation.

An extreme percentile is a descriptive statistical observation, not an automatic trading signal.

## 5. OPEN INTEREST & MARKET PARTICIPATION

Open interest must be analyzed together with price and volume.

Monitor:

- Total open interest
- Daily changes
- Weekly changes
- Contract-level open interest
- Futures volume
- Options open interest
- Contract maturity distribution

### Price and Open Interest Framework

| Price | Open Interest | Possible Interpretation |
|---|---|---|
| Rising | Rising | New exposure accompanying price appreciation |
| Rising | Falling | Position reduction or short covering may contribute |
| Falling | Rising | New exposure accompanying price decline |
| Falling | Falling | Position reduction or long liquidation may contribute |

These are interpretive frameworks, not definitive identification of buyer or seller intent.

Open interest represents outstanding contracts. Every open contract has both a long and a short side.

## 6. OPTIONS MARKET POSITIONING

The engine must monitor options-market activity and exposure.

Required indicators:

- Call open interest
- Put open interest
- Put/call open-interest ratio
- Put/call volume ratio
- Implied volatility
- Realized volatility
- Options volume
- Strike distribution
- Expiration distribution
- Skew
- Term structure
- Implied volatility surface

### Put/Call Analysis

The system must specify whether each ratio is based on:

- Volume
- Open interest
- Equity options
- Index options
- Futures options
- A defined market universe

Different put/call ratios must never be combined without methodological justification.

### Options Skew

Monitor:

- 25-delta risk reversal
- Put skew
- Call skew
- Volatility smile
- Changes in downside protection demand

The engine must distinguish demand for protection from outright directional speculation.

## 7. DEALER GAMMA & GAMMA EXPOSURE

The engine must evaluate dealer gamma exposure when sufficient options-chain data and a defensible positioning model are available.

Required inputs may include:

- Options open interest
- Contract multiplier
- Strike
- Expiration
- Underlying price
- Implied volatility
- Option type
- Delta
- Gamma
- Relevant participant-position assumptions

### Gamma Exposure Framework

A simplified estimated gamma exposure calculation may use:

GEX = Gamma × Open Interest × Contract Multiplier × Spot Price² × Sign Assumption

The exact calculation convention, scaling, and sign assumptions must be documented.

### Important Limitations

Public options open interest does not independently reveal whether dealers are net long or net short each option.

Therefore:

- Dealer gamma must be labeled estimated unless directly supported by reliable positioning data.
- The sign-assignment methodology must be disclosed.
- Assumptions must not be presented as observed dealer positions.
- Results must include sensitivity analysis.
- Data quality and model confidence must be visible.

### Gamma Regime Classification

**Positive Gamma Estimate**

Under the assumed dealer-positioning model, dealer hedging may dampen price movements.

**Negative Gamma Estimate**

Under the assumed model, dealer hedging may reinforce price movements.

**Neutral or Uncertain Gamma**

Available evidence is insufficient to establish a reliable directional gamma regime.

The system must not treat these classifications as guaranteed market behavior.

## 8. GAMMA FLIP & KEY OPTIONS LEVELS

Where data quality permits, identify:

- Estimated gamma flip level
- Major call open-interest concentrations
- Major put open-interest concentrations
- High-gamma strikes
- Expiration-related exposure concentrations
- Potential hedging-sensitive price regions

Every calculated level must include:

- Calculation timestamp
- Underlying price timestamp
- Options-chain timestamp
- Expiration universe
- Methodology
- Model assumptions
- Confidence classification

These levels are model estimates, not guaranteed support or resistance.

## 9. VOLATILITY POSITIONING

The engine must monitor volatility-related exposure.

Relevant instruments and indicators may include:

- VIX futures
- VIX options
- Equity index options
- Volatility ETFs
- Implied volatility term structure
- Realized volatility
- Volatility risk premium

Evaluate:

- Volatility futures curve
- Contango and backwardation
- Short-volatility exposure
- Long-volatility demand
- Changes in hedging costs
- Volatility compression and expansion

The system must distinguish volatility exposure from directional equity exposure.

## 10. INSTITUTIONAL EQUITY OWNERSHIP

The engine must integrate institutional ownership disclosures where available.

Potential sources include:

- SEC Form 13F
- Schedule 13D
- Schedule 13G
- Form 4
- Official fund holdings
- ETF holdings disclosures
- Relevant regulatory filings outside the US

### Required Fields

- Issuer
- Ticker
- Reporting institution
- Filing type
- Reporting period
- Filing date
- Reported shares
- Reported market value
- Ownership percentage, where available
- Change in reported holdings
- Source reference
- Verification status

### Interpretation Rules

- 13F filings are periodic and delayed.
- Reported holdings do not necessarily reveal current positions.
- Options-related disclosures may be incomplete.
- Short positions may not be visible.
- Derivatives exposure may be absent or difficult to infer.
- A reported ownership increase does not automatically establish a new purchase during the current market period.

Institutional ownership must not be confused with recent capital inflows.

## 11. ETF HOLDINGS & POSITIONING

Monitor:

- ETF holdings
- Shares outstanding
- Net asset value
- Premium or discount
- Creation and redemption activity
- Reported fund flows
- Concentration
- Changes in underlying exposure

Distinguish:

- ETF market-price movement
- Changes in AUM
- Net creations and redemptions
- Underlying asset-price appreciation
- Changes in portfolio composition

An increase in ETF AUM does not automatically indicate an equivalent amount of new capital entering the underlying market.

## 12. CROWDING & POSITION CONCENTRATION

The engine must identify crowded market exposures.

Potential indicators:

- Extreme COT percentiles
- High open-interest concentration
- Concentrated options exposure
- Elevated leverage
- Unusually high funding rates
- Extreme futures basis
- One-sided institutional positioning
- Concentrated ownership
- Positioning-price divergence

### Crowding Classification

**Low Crowding**

No material evidence of concentrated positioning.

**Moderate Crowding**

Positioning is becoming concentrated, but no major stress condition is established.

**High Crowding**

Multiple indicators suggest significant exposure concentration.

**Extreme Crowding**

Historical extremes and additional market-stress indicators suggest elevated liquidation or squeeze vulnerability.

Crowding is a risk condition, not a directional forecast.

## 13. SHORT SQUEEZE & LONG LIQUIDATION DETECTION

The engine must identify conditions that may increase the risk of forced position adjustment.

### Short Squeeze Indicators

- High short interest, where reliable
- Elevated short positioning
- Rising prices
- Increasing volume
- Deteriorating borrow availability
- Rising borrow costs
- Positive catalysts
- Potentially destabilizing negative gamma conditions

### Long Liquidation Indicators

- High leveraged long exposure
- Rapid price deterioration
- Falling open interest
- Rising liquidations
- Elevated funding rates before reversal
- Weakening market liquidity
- Potentially destabilizing negative gamma conditions

### Confirmation Requirements

A squeeze or liquidation alert must identify which indicators are observed and which remain inferred.

The engine must not label ordinary price appreciation as a short squeeze without supporting positioning evidence.

## 14. POSITIONING DIVERGENCE ANALYSIS

The engine must compare positioning with:

- Price action
- Open interest
- Volume
- Fundamentals
- Macro conditions
- Liquidity conditions
- Capital flows
- Market structure

Examples:

- Price rising while leveraged funds reduce net longs.
- Price declining while commercial hedgers increase net longs.
- Open interest rising during a persistent directional trend.
- Options demand increasing without corresponding spot-market confirmation.
- Institutional ownership increasing while reported earnings expectations deteriorate.

Each divergence must include alternative explanations and a confidence assessment.

## 15. INSTITUTIONAL POSITIONING SCORE

The engine shall calculate an Institutional Positioning Condition Score for each asset or market.

| Component | Weight |
|---|---:|
| Futures Positioning & COT | 20% |
| Options Positioning & Skew | 15% |
| Open Interest & Participation | 15% |
| Dealer Gamma Model | 15% |
| Institutional Ownership & ETF Exposure | 15% |
| Crowding & Leverage Indicators | 10% |
| Positioning Divergence & Confirmation | 10% |
| **Total** | **100%** |

### Classification

- 85–100: Strong Positioning Evidence
- 70–84: Elevated Positioning Signal
- 55–69: Mixed Positioning Conditions
- 40–54: Weak Positioning Evidence
- 0–39: Insufficient or Adverse Evidence

### Scoring Rules

- Missing data must not receive an assumed positive score.
- Delayed disclosures must carry a freshness penalty.
- Model-estimated gamma must be labeled and confidence-adjusted.
- Conflicting indicators must reduce confidence.
- Positioning extremes must not automatically generate LONG or SHORT signals.
- Score and confidence must remain separate.
- The score is not a probability of profitable trading.

## 16. POSITIONING-BASED SCENARIO ENGINE

Every significant positioning condition must include three scenarios.

### Bullish Scenario

Evaluate:

- Short-covering potential
- Underpositioned market participants
- Improving catalysts
- Positive price confirmation
- Potentially supportive dealer hedging conditions

### Neutral Scenario

Evaluate:

- Balanced exposure
- Stable open interest
- Limited positioning changes
- Lack of decisive price confirmation

### Bearish Scenario

Evaluate:

- Crowded long exposure
- Increasing downside protection demand
- Negative price confirmation
- Rising liquidation vulnerability
- Potentially destabilizing dealer hedging conditions

Each scenario must include:

- Trigger conditions
- Supporting evidence
- Contradictory evidence
- Expected market mechanism
- Time horizon
- Invalidation conditions

## 17. DATA SOURCES & REGISTRY REQUIREMENTS

The API Source Registry must support documented access to relevant sources.

Potential sources include:

### Futures & COT

- US Commodity Futures Trading Commission
- Relevant futures exchanges
- Exchange-published open-interest data

### Options & Volatility

- Cboe
- CME Group
- Relevant options exchanges
- Approved market-data providers

### Institutional Holdings

- US Securities and Exchange Commission
- Official fund disclosures
- ETF issuer holdings
- Relevant international regulatory filings

### Market Data

- Approved price-data providers
- Options-chain providers
- Futures-market data providers
- Verified short-interest and securities-lending data sources

For every source, maintain:

- Provider
- Official endpoint or retrieval method
- Access requirements
- Update frequency
- Publication delay
- Historical coverage
- Data definition
- License restrictions
- Validation status
- Health status

The presence of an API key does not establish source connectivity or data validity.

## 18. INTEGRATION WITH GRIOS v15

### API Source Registry

Provides source metadata, retrieval status, freshness, and health monitoring.

### Data Intelligence & Validation Engine

Validates positioning records, timestamps, units, participant classifications, and historical consistency.

### Global Liquidity Engine

Provides liquidity conditions that may influence leverage, risk capacity, and positioning adjustments.

### Cross-Asset Transmission Engine

Maps positioning changes into potential cross-market transmission and contagion effects.

### Smart Money Tracking Engine

Provides verified institutional transactions and strategic capital-allocation evidence.

### Megatrend Discovery Engine

Provides structural fundamental context for evaluating whether institutional positioning aligns with long-term demand and capital expenditure trends.

### Signal Scoring Engine

Receives validated positioning evidence as a market-structure input.

The existing Signal Scoring Engine remains responsible for final opportunity ranking.

The Institutional Positioning Score must not replace it.

### Daily Market & Investment Intelligence

Publishes:

- COT positioning developments
- Futures positioning extremes
- Options-market conditions
- Estimated dealer gamma regimes
- Institutional ownership changes
- ETF positioning
- Crowding alerts
- Short squeeze and liquidation risks
- Positioning-based scenarios

## 19. STANDARD OUTPUT SCHEMA

Every positioning record must contain:

- Positioning Record ID
- Asset or market
- Instrument
- Exchange
- Participant category
- Report type
- Reporting date
- Publication date
- Retrieval timestamp
- Long exposure
- Short exposure
- Net exposure
- Open interest
- Volume
- Historical percentile
- Z-score
- Positioning change
- Options exposure
- Gamma estimate, where available
- Institutional ownership data, where available
- ETF exposure, where available
- Crowding classification
- Divergence classification
- Source references
- Verification status
- Data freshness
- Confidence

Every positioning assessment must additionally contain:

- Institutional Positioning Condition Score
- Component scores
- Market regime
- Dominant participant categories
- Positioning extremes
- Options exposure assessment
- Estimated gamma methodology
- Crowding risk
- Squeeze or liquidation vulnerability
- Bull, neutral, and bear scenarios
- Invalidation conditions
- Last updated timestamp

## 20. OPERATIONAL WORKFLOW

The standard workflow is:

1. Identify the asset or market to monitor.
2. Retrieve relevant COT and futures data.
3. Retrieve open interest and volume.
4. Retrieve options-chain and volatility data.
5. Calculate positioning and exposure metrics.
6. Evaluate historical positioning percentiles.
7. Analyze estimated dealer gamma, if supported.
8. Retrieve institutional ownership disclosures.
9. Retrieve ETF holdings and flow data.
10. Assess crowding and leverage.
11. Detect positioning-price divergences.
12. Identify squeeze and liquidation vulnerabilities.
13. Validate all source timestamps and definitions.
14. Calculate the Institutional Positioning Condition Score.
15. Build conditional scenarios.
16. Integrate findings with the Signal Scoring Engine.
17. Publish relevant alerts and intelligence.

## 21. DATA GOVERNANCE & MODEL INTEGRITY

The engine must preserve:

- Original source records
- Historical reporting dates
- Publication dates
- Retrieval timestamps
- Positioning calculation methodology
- Options-model assumptions
- Gamma sign conventions
- Historical score changes
- Confidence changes
- Data revisions
- Model versions

The system must distinguish:

- Reported positioning
- Calculated positioning metrics
- Estimated dealer exposure
- Reported institutional ownership
- Verified capital flows
- Model-generated interpretations
- Speculative hypotheses

No unobservable institutional position may be represented as confirmed fact.

## 22. FINAL OPERATING PRINCIPLE

GRIOS must understand not only where markets are trading, but also how market participants are positioned.

The engine must answer:

1. Who is positioned long and short?
2. Which participant categories are changing exposure?
3. Are positions approaching historical extremes?
4. Is open interest confirming price action?
5. What does the options market indicate?
6. What is the estimated dealer gamma environment?
7. Where is positioning becoming crowded?
8. Is the market vulnerable to short squeezes or long liquidations?
9. Are institutional positioning and fundamental conditions aligned?
10. What evidence would invalidate the current positioning thesis?

**GRIOS v15 Objective:**

Track institutional exposure, identify positioning imbalances, detect crowded trades, and understand potential market pressure before it becomes fully visible in price action.

**We Track Capital Before The Crowd.**
