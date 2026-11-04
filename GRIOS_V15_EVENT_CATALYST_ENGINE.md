# GRIOS v15 — Event Catalyst Engine
## Institutional Event Monitoring, Catalyst Intelligence & Market Impact Analysis

**System:** Ghanizadeh Research Intelligence Operating System (GRIOS)  
**Version:** 15.0 Institutional Edition  
**Module:** Event Catalyst Engine  
**Status:** Architecture and operating specification

---

## 1. Mission

The Event Catalyst Engine identifies, classifies, monitors, and evaluates scheduled and unscheduled events capable of changing market expectations, capital allocation, asset pricing, volatility, or portfolio risk.

Its mission is to transform event information into structured, evidence-based market intelligence.

**Core principle:**

An event is not automatically a catalyst. Its importance depends on surprise, market expectations, positioning, liquidity, transmission channels, and the resulting change in investor behavior.

---

## 2. Core Objectives

The engine must:

1. Maintain a structured global event calendar.
2. Identify high-impact scheduled and unscheduled catalysts.
3. Monitor official announcements and event revisions.
4. Compare actual outcomes with consensus expectations.
5. Measure event surprise and market reaction.
6. Map transmission across asset classes and sectors.
7. Evaluate pre-event positioning and liquidity conditions.
8. Generate conditional scenarios and risk alerts.
9. Track post-event outcomes and historical impact.
10. Supply verified catalyst intelligence to the GRIOS Daily Report and Signal Scoring Engine.

---

## 3. Event Taxonomy

### 3.1 Macroeconomic Events

- CPI and Core CPI
- PCE and Core PCE
- Nonfarm Payrolls (NFP)
- Unemployment Rate
- Initial Jobless Claims
- GDP and GDP revisions
- PMI and ISM
- Retail Sales
- Industrial Production
- Consumer Confidence
- Housing Data
- Wage Growth
- Productivity

### 3.2 Central Bank Events

- Federal Reserve meetings
- FOMC statements and minutes
- Federal Reserve speeches
- ECB meetings
- Bank of England decisions
- Bank of Japan decisions
- Other major central bank decisions
- Monetary policy guidance
- Quantitative tightening or easing announcements

### 3.3 Rates and Fiscal Events

- US Treasury auctions
- Treasury refunding announcements
- Government budget decisions
- Fiscal stimulus or austerity
- Debt ceiling developments
- Sovereign credit rating changes
- Government financing announcements

### 3.4 Corporate Events

- Earnings releases
- Earnings guidance
- Revenue and margin revisions
- Investor days
- Capital expenditure announcements
- M&A announcements
- Share buybacks
- Dividend decisions
- IPOs and secondary offerings
- Lockup expirations
- Shareholder votes
- Major contracts and procurement announcements
- Product launches

### 3.5 Geopolitical and Policy Events

- Elections
- Sanctions
- Trade restrictions
- Tariff decisions
- Export controls
- Regulatory decisions
- Court rulings
- Diplomatic negotiations
- Military escalation or de-escalation
- OPEC+ meetings
- Energy policy changes
- Strategic industrial policy

### 3.6 Commodity and Supply Events

- EIA inventory releases
- OPEC production decisions
- Oil and gas supply disruptions
- Mining production updates
- Critical mineral export restrictions
- Strategic reserve decisions
- Agricultural supply reports
- Nuclear fuel supply developments
- Major commodity supply agreements

### 3.7 Digital Assets and Crypto Events

- Spot ETF regulatory decisions
- ETF launches and closures
- Token unlocks
- Protocol upgrades
- Network hard forks
- Regulatory announcements
- Exchange developments
- Major liquidation events
- Institutional custody and adoption announcements

### 3.8 Technology and Megatrend Events

- AI infrastructure investments
- Semiconductor capacity announcements
- Advanced packaging and HBM developments
- Data center construction
- Power purchase agreements
- Nuclear energy contracts
- Robotics commercialization
- Defense technology procurement
- Strategic supply-chain agreements

---

## 4. Event Classification Framework

Every event must be classified across the following dimensions.

### 4.1 Scheduling Status

- Scheduled
- Unscheduled
- Recurring
- One-time
- Ongoing
- Event window uncertain

### 4.2 Verification Status

- Officially Confirmed
- Independently Verified
- Reported — Awaiting Confirmation
- Rumored
- Unverified
- Cancelled
- Postponed

Rumors must never be presented as confirmed events.

### 4.3 Event Lifecycle

1. Detected
2. Registered
3. Verified
4. Classified
5. Monitored
6. Approaching
7. Released or Occurred
8. Impact Assessed
9. Archived

### 4.4 Market Sensitivity

- Very High
- High
- Moderate
- Low
- Unknown

Market sensitivity must be supported by historical evidence, affected asset exposure, or a documented analytical rationale.

---

## 5. Event Impact Scoring

The Event Catalyst Engine must maintain a dedicated Event Impact Score.

This score is separate from the GRIOS Signal Score, Systematic Risk Score, and Megatrend Score.

Suggested weighted framework:

| Component | Weight |
|---|---:|
| Economic or Strategic Significance | 20% |
| Surprise Potential | 20% |
| Cross-Asset Transmission Potential | 15% |
| Market Sensitivity | 15% |
| Positioning and Crowding | 10% |
| Liquidity and Volatility Conditions | 10% |
| Evidence Quality and Verification | 10% |

**Total: 100%**

Suggested interpretation:

- Tier 1: 85–100 — Critical Catalyst
- Tier 2: 70–84 — High Impact
- Tier 3: 55–69 — Moderate Impact
- Tier 4: 40–54 — Limited Impact
- Tier 5: 0–39 — Low Impact

Missing information must not be silently treated as neutral or positive. The engine must identify incomplete inputs and reduce confidence accordingly.

A high Event Impact Score does not imply a predictable market direction.

---

## 6. Consensus and Surprise Analysis

For economic and corporate releases, the engine should capture:

- Previous value
- Revised previous value
- Consensus estimate
- Actual value
- Release timestamp
- Source
- Units
- Reporting period
- Revision history

Where appropriate, calculate:

**Absolute Surprise:**

Actual Value − Consensus Estimate

**Standardized Surprise:**

(Actual Value − Consensus Estimate) / Historical Standard Deviation of Forecast Errors

Standardization must only be performed when the required historical observations and methodology are available.

For metrics where lower values are favorable, the engine must apply metric-specific interpretation rather than assuming positive numerical surprises are always bullish.

For earnings, analyze:

- EPS surprise
- Revenue surprise
- Margin surprise
- Guidance revisions
- Management commentary
- Forward estimates
- Segment-level performance

The engine must distinguish reported results from forward guidance.

---

## 7. Pre-Event Intelligence

Before a major catalyst, the engine should evaluate:

- Current market expectations
- Consensus dispersion
- Historical event volatility
- Recent revisions
- Current market regime
- Institutional positioning
- Options-implied volatility, where available
- Liquidity conditions
- Relevant technical structure
- Existing market narratives
- Potential asymmetric risks

### Pre-Event Scenario Framework

For every high-impact event, construct:

1. Base Case
2. Upside Surprise
3. Downside Surprise
4. Tail-Risk Scenario

Each scenario must include:

- Trigger conditions
- Expected transmission mechanism
- Potentially affected assets
- Supporting evidence
- Contradicting evidence
- Confidence level
- Invalidation conditions

Scenarios are conditional analytical frameworks, not guaranteed forecasts.

---

## 8. Post-Event Impact Analysis

After an event, measure:

- Initial price reaction
- Intraday reaction
- Closing reaction
- Follow-through over subsequent sessions
- Volatility expansion or contraction
- Changes in yields and currency markets
- Sector rotation
- Commodity reaction
- ETF and fund-flow changes, where verified
- Changes in market expectations

The engine must distinguish:

**Headline Reaction:** Immediate response to the announcement.

**Fundamental Repricing:** A sustained change in expected economic or corporate fundamentals.

**Positioning Reaction:** Price movement driven by crowded trades, short covering, liquidation, or repositioning.

**Liquidity Reaction:** Movement caused or amplified by market depth and funding conditions.

A price move alone does not establish its underlying cause.

---

## 9. Cross-Asset Transmission

Every significant event should be mapped to relevant transmission channels.

| Event Type | Primary Channels | Assets to Monitor |
|---|---|---|
| Inflation surprise | Rates, real yields, policy expectations | DXY, Treasuries, Gold, Equities |
| Labor market surprise | Growth, rates, Fed expectations | USD, Bonds, Equity Indices |
| Central bank decision | Policy rates, liquidity, currency | FX, Bonds, Gold, Equities |
| Geopolitical escalation | Energy supply, risk premium | Oil, Gold, Defense, FX |
| AI CapEx announcement | Infrastructure demand, power demand | Semiconductors, Data Centers, Utilities |
| Critical mineral restriction | Supply risk, industrial costs | Copper, Uranium, Lithium, Related Equities |
| Crypto regulatory decision | Market access, liquidity, adoption | BTC, ETH, Crypto Equities |

These are monitoring relationships, not deterministic price predictions.

The Cross-Asset Transmission Engine must provide the deeper causal analysis.

---

## 10. Event and Positioning Interaction

The engine must connect upcoming catalysts with the Institutional Positioning Engine.

Monitor, where reliable data exists:

- COT positioning
- Futures open interest
- Options open interest
- Implied volatility
- Put/call positioning
- ETF holdings and flows
- Public institutional disclosures
- Crowded positioning indicators
- Short interest
- Liquidation exposure

Important limitations:

- Options open interest does not independently reveal dealer directional exposure.
- Public institutional disclosures may be delayed.
- ETF holdings are not equivalent to daily net flows.
- Estimated dealer gamma must include its assumptions and methodology.

The engine must flag situations where a major catalyst coincides with unusually crowded positioning or fragile liquidity.

---

## 11. Event Risk and Portfolio Integration

The Event Catalyst Engine must communicate with the Systematic Risk Engine.

For relevant portfolios or monitored instruments, evaluate:

- Event exposure
- Earnings concentration
- Macro event concentration
- Correlated catalyst exposure
- Overnight gap risk
- Liquidity deterioration
- Volatility expansion
- Leverage and margin sensitivity
- Potential drawdown impact

The engine may generate risk alerts and conditional exposure warnings.

It must not automatically recommend position sizing without validated portfolio and instrument data.

---

## 12. Event Data Architecture

Each event record should contain:

| Field | Description |
|---|---|
| event_id | Unique event identifier |
| event_name | Official or standardized event name |
| event_category | Macro, Central Bank, Corporate, Geopolitical, etc. |
| event_subcategory | More specific classification |
| country_region | Relevant geography |
| affected_assets | Related tickers, sectors, and asset classes |
| scheduled_status | Scheduled or unscheduled |
| verification_status | Confirmation level |
| event_timestamp | Original event timestamp |
| normalized_timestamp_utc | Normalized UTC timestamp |
| local_timezone | Original or relevant timezone |
| previous_value | Previous reported value |
| revised_previous_value | Revised previous value |
| consensus_value | Market expectation |
| actual_value | Released value |
| event_impact_score | Dedicated event score |
| confidence_level | Evidence-based confidence |
| source_id | API Source Registry reference |
| source_timestamp | Source publication or update time |
| last_updated | Latest record update |
| lifecycle_status | Current event lifecycle stage |
| scenario_reference | Linked scenario records |
| post_event_assessment | Final impact analysis |

Unknown fields must remain null or explicitly unavailable. The system must not fabricate missing values.

---

## 13. Source Hierarchy and Verification

Preferred source hierarchy:

**Tier 1 — Primary Sources**
- Central banks
- Government statistical agencies
- Treasury departments
- Regulatory authorities
- Corporate investor relations
- Exchange announcements
- Official commodity agencies
- Official event organizers

**Tier 2 — Institutional Sources**
- Recognized research institutions
- Established financial data providers
- Industry associations
- Official company filings and transcripts

**Tier 3 — Independent Reporting**
- Reputable financial news organizations
- Established specialist publications
- Independent industry research

**Tier 4 — Unverified Information**
- Social media claims
- Anonymous sources without corroboration
- Unconfirmed rumors

Tier 4 information may trigger investigation but must not be represented as established fact.

All event data must follow the API Source Registry and Data Intelligence & Validation protocols.

---

## 14. Data Quality and Event Integrity

The engine must implement:

- Duplicate event detection
- Timezone normalization
- Daylight-saving-time handling
- Calendar revision tracking
- Source timestamp validation
- Missing-field detection
- Unit consistency
- Consensus source attribution
- Actual-value verification
- Cancelled and postponed event handling
- Conflicting-source alerts
- Historical event versioning

Events from different providers must not be merged solely because their names are similar.

Event identity should consider event type, geography, reporting period, issuer, and timestamp.

---

## 15. Alert and Notification Framework

Suggested alert categories:

- CRITICAL EVENT DETECTED
- HIGH-IMPACT EVENT APPROACHING
- EVENT TIME UPDATED
- EVENT CANCELLED
- CONSENSUS REVISION
- MAJOR DATA SURPRISE
- UNEXPECTED POLICY DECISION
- GEOPOLITICAL ESCALATION
- EARNINGS GUIDANCE SHOCK
- CROSS-ASSET TRANSMISSION DETECTED
- POSITIONING FRAGILITY BEFORE EVENT
- POST-EVENT REGIME CHANGE

Each alert should include:

1. Event name
2. Timestamp and timezone
3. Verification status
4. Event Impact Score
5. Affected assets
6. Relevant evidence
7. Expected transmission channels
8. Scenario implications
9. Confidence and data limitations

Notifications must only be described as operational when the corresponding alert pipeline has been implemented and tested.

---

## 16. Historical Event Intelligence

Maintain a historical database of major events and market responses.

Analyze:

- Historical surprise magnitude
- Asset-specific reaction
- Volatility response
- Directional consistency
- Reaction duration
- Market regime dependence
- Positioning dependence
- Liquidity dependence
- Forecast error
- Scenario accuracy

Historical correlations must not be interpreted as universal causal relationships.

Backtests must account for data revisions, publication timestamps, survivorship bias, and look-ahead bias.

---

## 17. Integration With GRIOS v15

The Event Catalyst Engine must integrate with:

- API Source Registry
- Data Intelligence & Validation Engine
- Signal Scoring Engine
- Smart Money Tracking Engine
- Megatrend Discovery Engine
- Cross-Asset Transmission Engine
- Global Liquidity Engine
- Institutional Positioning Engine
- Systematic Risk Engine
- Daily Market & Investment Intelligence Report

### Integration Logic

**API Source Registry → Event Data Collection**

**Data Validation → Verified Event Records**

**Event Catalyst Engine → Event Classification and Impact Analysis**

**Cross-Asset Transmission → Asset-Level Implications**

**Institutional Positioning → Crowding and Pre-Event Exposure**

**Global Liquidity → Liquidity Regime Context**

**Systematic Risk → Portfolio Risk Implications**

**Signal Scoring → Evidence-Based Opportunity Assessment**

**Daily Intelligence Report → Executive-Level Event Intelligence**

---

## 18. Daily Reporting Requirements

The GRIOS Daily Market & Investment Intelligence report must include:

### A. Upcoming Critical Events
List the most important events over the next 24–72 hours.

### B. High-Impact Events
Explain why each event matters and which assets may be affected.

### C. Consensus and Expectations
Provide previous, consensus, and actual values when available.

### D. Event-Driven Scenarios
Present conditional bullish, bearish, and neutral outcomes where relevant.

### E. Positioning and Liquidity Risks
Highlight crowded positioning and fragile liquidity before major catalysts.

### F. Post-Event Review
Explain what happened, how markets reacted, and whether the initial thesis remains valid.

All timestamps must identify the relevant timezone.

---

## 19. Governance and Operational Rules

1. Never fabricate event dates or release times.
2. Never present rumors as confirmed announcements.
3. Never confuse consensus with actual results.
4. Preserve revisions and historical records.
5. Never infer market direction from event importance alone.
6. Separate event impact from signal confidence.
7. Identify conflicting evidence.
8. Do not issue unsupported entry, stop-loss, or target levels.
9. Do not claim real-time monitoring without verified operational evidence.
10. Record source and retrieval timestamps.
11. Respect provider terms and API access restrictions.
12. Keep credentials outside public repositories and frontend code.
13. Maintain an auditable record of event classifications and impact assessments.

---

## 20. Final Operating Principle

The Event Catalyst Engine must answer five questions:

1. What is happening?
2. How reliable is the information?
3. What does the market expect?
4. Through which channels can the event affect capital and asset prices?
5. What evidence would confirm or invalidate the expected market reaction?

**GRIOS does not trade the headline. It analyzes the expectation gap, capital positioning, transmission mechanism, and resulting repricing.**

**Mission:** We Track Capital Before The Crowd.
