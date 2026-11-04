# GRIOS v15 — GLOBAL LIQUIDITY ENGINE

## Institutional Framework for Global Liquidity, Dollar Funding, Central Bank Balance Sheets & Financial Conditions

**Project:** Ghanizadeh Research Intelligence Operating System  
**Version:** 15.0  
**Module:** Global Liquidity Engine  
**Status:** Core Module Specification  
**Mission:** We Track Capital Before The Crowd.

---

## 1. PURPOSE

The Global Liquidity Engine measures, monitors, and interprets global financial liquidity conditions and their potential impact on asset prices, capital allocation, funding markets, and risk appetite.

Its primary objectives are to:

- Track changes in central-bank balance sheets.
- Monitor banking-system reserves and funding conditions.
- Analyze Treasury cash-management operations.
- Monitor money-market liquidity.
- Evaluate global dollar funding conditions.
- Track international monetary and liquidity developments.
- Identify liquidity expansion and contraction regimes.
- Connect liquidity conditions to cross-asset market behavior.
- Detect potential liquidity-driven investment opportunities and systemic risks.

**Core principle:**

Liquidity is multidimensional. Central-bank assets, bank reserves, monetary aggregates, funding availability, credit creation, and investable capital flows must be measured separately.

A single liquidity indicator must never be treated as a complete representation of global financial liquidity.

## 2. GLOBAL LIQUIDITY ARCHITECTURE

The engine shall organize liquidity analysis into seven interconnected layers.

### Layer 1 — Central Bank Balance Sheets

Monitor the size, composition, and direction of major central-bank balance sheets.

### Layer 2 — Banking-System Liquidity

Monitor reserves, deposits, funding availability, and banking-system conditions.

### Layer 3 — Government Cash Management

Monitor Treasury cash balances, government issuance, and fiscal cash flows.

### Layer 4 — Money Markets & Funding

Monitor repo, reverse repo, secured funding, unsecured funding, and short-term interest rates.

### Layer 5 — Global Dollar Liquidity

Monitor international dollar funding, cross-currency basis, offshore dollar conditions, and foreign-exchange swap markets.

### Layer 6 — Credit & Financial Conditions

Monitor credit creation, lending conditions, leverage, spreads, and financial-system risk capacity.

### Layer 7 — Asset-Market Transmission

Evaluate how liquidity conditions interact with bonds, currencies, equities, commodities, and digital assets.

## 3. CENTRAL BANK BALANCE SHEET MONITORING

The engine must monitor major central banks, including:

- Federal Reserve
- European Central Bank
- Bank of Japan
- People's Bank of China
- Bank of England
- Swiss National Bank
- Other systemically relevant central banks

For each institution, monitor:

- Total assets
- Total liabilities, where available
- Government securities holdings
- Lending facilities
- Reserve-related liabilities
- Foreign-exchange assets
- Asset purchase programs
- Quantitative easing
- Quantitative tightening
- Emergency liquidity operations

### Federal Reserve Priority Indicators

- Total Federal Reserve assets
- Treasury securities holdings
- Mortgage-backed securities holdings
- Reserve balances
- Overnight reverse repurchase agreements
- Currency in circulation
- Treasury General Account
- Relevant liquidity facilities

### Analytical Requirements

The engine must distinguish:

- Balance-sheet expansion from reserve creation.
- Balance-sheet contraction from actual funding stress.
- Asset composition changes from changes in total assets.
- Temporary liquidity facilities from persistent monetary expansion.
- Valuation effects from transaction-driven balance-sheet changes.

## 4. BANKING-SYSTEM LIQUIDITY

Monitor the availability and distribution of liquidity within the banking system.

Required indicators:

- Bank reserve balances
- Commercial bank deposits
- Bank credit
- Loan growth
- Deposit growth
- Reserve concentration, where available
- Bank funding costs
- Relevant regulatory liquidity indicators
- Interbank funding conditions

### Key Analytical Questions

- Are aggregate reserves increasing or decreasing?
- Are reserves broadly distributed or concentrated?
- Are banks expanding or restricting credit?
- Are deposit conditions improving or deteriorating?
- Is the banking system experiencing funding pressure?
- Are changes in reserves accompanied by changes in credit availability?

Aggregate reserve growth must not automatically be interpreted as improved liquidity for every financial institution.

## 5. TREASURY GENERAL ACCOUNT & FISCAL LIQUIDITY

The engine must closely monitor the US Treasury General Account (TGA).

Required indicators:

- TGA balance
- Daily and weekly changes
- Treasury cash-management operations
- Net Treasury issuance
- Treasury bill issuance
- Coupon issuance
- Government spending
- Tax receipts
- Treasury auction results

### Transmission Analysis

Changes in the TGA can influence banking-system reserves through government cash flows.

The engine must analyze:

- Treasury cash accumulation
- Treasury cash deployment
- Tax-payment periods
- Government spending cycles
- Debt issuance
- Settlement timing
- Interactions with Federal Reserve operations

The engine must not assume that every increase in Treasury issuance produces an identical reserve drain.

The effect depends on the buyer base, settlement flows, cash management, and other balance-sheet operations.

## 6. REPO & REVERSE REPO MARKET

Monitor short-term secured funding conditions.

Required indicators:

- Overnight Treasury repo rates
- SOFR
- Secured funding spreads
- Standing Repo Facility utilization
- Overnight reverse repo balances
- Relevant repo-market volumes
- Collateral availability
- Treasury collateral conditions

### Key Analytical Questions

- Is secured funding becoming more expensive?
- Are repo rates deviating from expected policy-rate conditions?
- Is there evidence of collateral scarcity?
- Is reverse repo usage increasing or declining?
- Are funding markets showing signs of stress?
- Is there a meaningful change in the composition of money-market liquidity?

A decline in reverse repo balances must not automatically be classified as an equivalent increase in risk-asset liquidity.

The engine must evaluate the actual destination and counterparties of the relevant flows.

## 7. GLOBAL DOLLAR LIQUIDITY

The engine must monitor the availability and cost of US dollar funding internationally.

Required indicators:

- DXY
- Cross-currency basis swaps
- FX swap market conditions
- Offshore dollar funding indicators
- Foreign central-bank dollar liquidity facilities
- Federal Reserve swap lines
- International banking claims, where available
- Relevant short-term dollar funding spreads

### Analytical Framework

Evaluate:

- Dollar funding demand
- Offshore dollar funding stress
- International bank balance-sheet constraints
- Currency hedging costs
- Foreign-exchange intervention
- Dollar liquidity provision

### Transmission Mechanism

Dollar funding stress may transmit through:

1. Higher dollar funding costs.
2. More expensive currency hedging.
3. Reduced access to dollar financing.
4. Pressure on foreign borrowers.
5. Potential deleveraging.
6. Changes in global risk appetite.

The direction and magnitude of the impact must be confirmed with observable market data.

## 8. MONETARY AGGREGATES & CREDIT CREATION

Monitor relevant monetary and credit indicators.

Examples:

- M2
- M1, where methodologically relevant
- Bank credit
- Private-sector lending
- Broad money growth
- Credit-to-GDP indicators
- Household credit
- Corporate credit
- International credit aggregates

### Analytical Requirements

The engine must distinguish:

- Monetary base
- Broad money
- Bank deposits
- Bank lending
- Central-bank reserves
- Credit creation
- Financial asset valuations

Changes in broad money must not automatically be interpreted as immediate buying power entering financial markets.

The engine must account for differences in definitions, frequency, coverage, and statistical methodology across jurisdictions.

## 9. FINANCIAL CONDITIONS MONITORING

Monitor financial conditions through a combination of market-based and institutional indicators.

Required categories:

- Interest rates
- Real yields
- Credit spreads
- Equity volatility
- Funding spreads
- Currency strength
- Lending standards
- Bank financing conditions
- Market liquidity
- Leverage indicators

Where available, incorporate established financial conditions indices.

Do not combine incompatible indices without normalization and methodology documentation.

## 10. LIQUIDITY IMPULSE & MOMENTUM

The engine must evaluate not only the level of liquidity but also its rate of change.

Required analytical measures:

- Weekly change
- Monthly change
- Quarterly change
- Year-over-year change
- Rate of acceleration or deceleration
- Rolling trend
- Historical percentile
- Volatility-adjusted change

### Liquidity Impulse

The liquidity impulse represents the change in the pace of liquidity expansion or contraction.

It must be calculated from explicitly defined underlying indicators.

The system must specify:

- Included variables
- Data frequency
- Normalization method
- Weighting methodology
- Treatment of missing observations
- Revision policy
- Calculation timestamp

No undocumented proprietary liquidity measure may be presented as an official economic statistic.

## 11. GLOBAL LIQUIDITY AGGREGATION

The engine may construct a Global Liquidity Dashboard from relevant monetary and funding indicators.

However, aggregation must follow strict methodology.

For every jurisdiction, document:

- Currency
- Reporting institution
- Indicator definition
- Reporting frequency
- Publication delay
- Seasonal adjustment status
- Data revision policy
- Conversion methodology
- Weighting methodology

Currency conversion must be explicit.

The system must not add nominal monetary values across currencies without a documented conversion process.

A global aggregate must distinguish between:

- Local-currency monetary growth
- US-dollar-equivalent changes
- Exchange-rate valuation effects
- Underlying domestic monetary changes

## 12. LIQUIDITY REGIME CLASSIFICATION

The engine must classify current liquidity conditions.

### Regime A — Strong Expansion

Characteristics:

- Broad-based liquidity improvement
- Improving funding conditions
- Increasing credit availability
- Supportive financial conditions

### Regime B — Moderate Expansion

Characteristics:

- Positive liquidity momentum
- Stable funding markets
- Gradual improvement in credit conditions

### Regime C — Neutral or Mixed

Characteristics:

- Conflicting monetary indicators
- Stable or mixed funding conditions
- No clear directional liquidity impulse

### Regime D — Moderate Contraction

Characteristics:

- Deteriorating liquidity momentum
- Tighter funding conditions
- Slower credit creation

### Regime E — Strong Contraction

Characteristics:

- Significant liquidity deterioration
- Funding-market stress
- Credit tightening
- Reduced financial-system risk capacity

### Regime F — Acute Funding Stress

Characteristics:

- Severe funding dislocations
- Counterparty concerns
- Material funding-market disruption
- Emergency liquidity measures

The regime classification must be supported by multiple indicators.

A single central-bank balance-sheet movement is insufficient to establish a global liquidity regime.

## 13. LIQUIDITY TRANSMISSION TO ASSET CLASSES

### 13.1 Government Bonds

Evaluate:

- Treasury yields
- Real yields
- Yield curve
- Auction demand
- Funding conditions
- Sovereign issuance

### 13.2 Foreign Exchange

Evaluate:

- DXY
- Dollar funding conditions
- Currency differentials
- Cross-currency basis
- Central-bank intervention

### 13.3 Equities

Evaluate:

- Equity valuations
- Market breadth
- Sector sensitivity
- Financial conditions
- Leverage
- Corporate financing conditions

### 13.4 Commodities

Evaluate:

- Commodity demand
- Financing conditions
- Inventory financing
- Currency effects
- Physical supply-demand conditions

### 13.5 Precious Metals

Evaluate:

- Real yields
- Dollar conditions
- Official-sector activity
- ETF flows
- Physical demand
- Safe-haven demand

### 13.6 Cryptocurrencies

Evaluate:

- Dollar funding conditions
- Stablecoin supply
- ETF flows
- Exchange liquidity
- Leverage
- Funding rates
- Open interest
- Liquidation activity

The engine must not assume that all risk assets respond uniformly to liquidity changes.

## 14. LIQUIDITY SCORING MODEL

The engine shall calculate a Global Liquidity Condition Score.

| Component | Weight |
|---|---:|
| Central Bank Balance Sheet Conditions | 20% |
| Banking-System Reserves & Credit | 15% |
| Treasury & Fiscal Liquidity | 15% |
| Repo & Money-Market Conditions | 15% |
| Global Dollar Funding | 15% |
| Broad Money & Credit Momentum | 10% |
| Financial Conditions & Market Confirmation | 10% |
| **Total** | **100%** |

### Score Classification

- 85–100: Strong Liquidity Expansion
- 70–84: Moderate Liquidity Expansion
- 55–69: Neutral or Mixed Conditions
- 40–54: Moderate Liquidity Contraction
- 0–39: Strong Liquidity Contraction or Stress

### Scoring Rules

- Missing data must not be interpreted as neutral or positive.
- Stale data must be penalized.
- Contradictory indicators must reduce confidence.
- Funding stress may override an otherwise positive aggregate score.
- Component scores must remain visible.
- The score must include a methodology version.
- Score and confidence must remain separate.

The Global Liquidity Condition Score is a model-derived analytical measure, not an official central-bank statistic.

## 15. LIQUIDITY STRESS DETECTION

The engine must identify early signs of funding deterioration.

Potential warning signals:

- Abnormal repo-rate movements
- Widening funding spreads
- Unusual cross-currency basis movements
- Rapid reserve deterioration
- Unusual bank funding activity
- Deteriorating credit conditions
- Increased emergency liquidity utilization
- Significant collateral dislocations

Every alert must specify:

- Indicator
- Threshold
- Observation timestamp
- Historical comparison
- Severity
- Data source
- Confirmation status
- Potential transmission channels

Thresholds must be calibrated using historical data and reviewed periodically.

## 16. SCENARIO ANALYSIS

Every major liquidity development must include three scenarios.

### Bull Scenario — Liquidity Improvement

- Improved funding conditions
- Stable or increasing reserves
- Reduced financial stress
- Improving credit availability
- Supportive market liquidity

### Base Scenario — Gradual or Mixed Conditions

- Mixed central-bank operations
- Stable funding markets
- Moderate changes in credit
- Limited broad-based liquidity impact

### Bear Scenario — Liquidity Deterioration

- Tightening funding conditions
- Weakening credit availability
- Rising dollar funding costs
- Deteriorating financial conditions
- Potential forced deleveraging

Each scenario must specify:

- Trigger conditions
- Leading indicators
- Affected markets
- Expected transmission
- Confirmation requirements
- Invalidation conditions

## 17. OPERATIONAL DATA REQUIREMENTS

The API Source Registry must maintain approved sources for:

### US Sources

- Federal Reserve H.4.1
- Federal Reserve FRED
- Federal Reserve Bank of New York
- US Treasury fiscal data
- Treasury auction data
- Relevant money-market statistics

### International Sources

- European Central Bank
- Bank of Japan
- Bank of England
- People's Bank of China
- Bank for International Settlements
- International Monetary Fund
- Other official monetary and financial institutions

### Market Data

- SOFR
- Treasury yields
- Repo indicators
- Cross-currency basis data
- FX market indicators
- Credit spreads
- Relevant market liquidity indicators

Each source must be registered with its official endpoint or documented retrieval method, update frequency, data definition, and validation status.

The presence of an API key does not establish that a source is operational or that retrieved data is valid.

## 18. INTEGRATION WITH GRIOS v15

### API Source Registry

Provides source registration, access status, freshness, and monitoring metadata.

### Data Intelligence & Validation Engine

Validates incoming monetary, banking, and market data.

### Cross-Asset Transmission Engine

Receives liquidity signals and maps their potential impact across financial markets.

### Smart Money Tracking Engine

Provides evidence of actual capital allocation and institutional positioning.

### Megatrend Discovery Engine

Connects structural investment themes to monetary and financial conditions.

### Signal Scoring Engine

Receives validated liquidity context as an input into individual opportunity assessments.

The Global Liquidity Condition Score must not replace the existing Signal Scoring methodology.

### Daily Market & Investment Intelligence

Publishes:

- Global liquidity conditions
- US dollar funding assessment
- Central-bank balance-sheet developments
- Treasury and repo dynamics
- Liquidity regime changes
- Cross-asset implications
- Liquidity stress alerts
- Conditional investment scenarios

## 19. STANDARD OUTPUT SCHEMA

Every liquidity observation must contain:

- Observation ID
- Institution
- Jurisdiction
- Indicator name
- Indicator definition
- Currency
- Reported value
- Previous value
- Absolute change
- Percentage change, where meaningful
- Reporting period
- Publication timestamp
- Retrieval timestamp
- Data frequency
- Source
- Source tier
- Validation status
- Freshness status
- Trend classification
- Regime contribution
- Confidence
- Methodology version

Every liquidity assessment must additionally contain:

- Global Liquidity Condition Score
- Component scores
- Liquidity regime
- Primary drivers
- Contradictory indicators
- Funding stress assessment
- Cross-asset implications
- Bull, base, and bear scenarios
- Evidence references
- Last updated timestamp

## 20. OPERATIONAL WORKFLOW

The standard workflow is:

1. Retrieve registered central-bank data.
2. Retrieve banking-system indicators.
3. Retrieve Treasury and fiscal data.
4. Retrieve repo and money-market indicators.
5. Retrieve global dollar funding indicators.
6. Retrieve monetary aggregates and credit data.
7. Validate observations and timestamps.
8. Normalize units and reporting frequencies.
9. Calculate changes and momentum.
10. Identify liquidity stress indicators.
11. Classify the liquidity regime.
12. Calculate the Global Liquidity Condition Score.
13. Compare liquidity signals with asset-market behavior.
14. Integrate verified capital-flow evidence.
15. Generate scenario analysis.
16. Identify relevant cross-asset implications.
17. Publish the liquidity dashboard and alerts.

## 21. DATA GOVERNANCE & MODEL INTEGRITY

The engine must preserve:

- Original source observations
- Historical revisions
- Retrieval timestamps
- Publication timestamps
- Transformation history
- Currency conversion methodology
- Aggregation methodology
- Missing-data treatment
- Score history
- Regime history
- Model version
- Validation status

The system must distinguish:

- Official reported data
- Calculated indicators
- Model-generated estimates
- Analytical interpretations
- Unverified hypotheses

Revised historical observations must not silently overwrite the original record.

## 22. FINAL OPERATING PRINCIPLE

GRIOS must understand global liquidity through its underlying mechanisms rather than relying on a single headline indicator.

The engine must answer:

1. Are global liquidity conditions expanding or contracting?
2. Which central banks and financial institutions are driving the change?
3. What is happening to US dollar funding?
4. Are banking reserves and credit conditions improving?
5. What role are Treasury cash flows and repo markets playing?
6. Are financial conditions confirming the liquidity assessment?
7. Which assets are most exposed?
8. What evidence would invalidate the current liquidity thesis?

**GRIOS v15 Objective:**

Measure global liquidity, identify funding stress, understand monetary transmission, and detect changes in financial-system risk capacity before they become fully reflected in market prices.

**We Track Capital Before The Crowd.**
