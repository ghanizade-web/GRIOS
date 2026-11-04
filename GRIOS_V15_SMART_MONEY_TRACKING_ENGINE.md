# GRIOS v15 — Smart Money & Strategic Capital Tracking Engine

**Project:** Ghanizadeh Research Intelligence Operating System  
**Version:** 15.0 Institutional Edition  
**Module:** Smart Money & Strategic Capital Intelligence  
**Status:** Core Intelligence Specification  
**Mission:** We Track Capital Before The Crowd.

---

## 1. Purpose

The Smart Money Tracking Engine identifies, monitors, verifies, and interprets major capital allocation decisions across global financial markets and strategic industries.

Its objective is to understand:

- Who is allocating capital?
- Where is the capital moving?
- What asset, company, technology, or resource is receiving investment?
- Why is the capital being allocated?
- Is the activity confirmed or speculative?
- What is the potential market impact?
- Which publicly traded companies may benefit?
- What could invalidate the investment thesis?

GRIOS must identify capital allocation trends before they become widely recognized market narratives.

The module must prioritize verified evidence over rumors, headlines, and unsupported claims.

## 2. Intelligence Coverage

The engine must monitor six major categories.

### 2.1 Institutional Asset Managers

Monitor publicly disclosed activities and relevant investment information from:

- BlackRock
- Vanguard
- State Street
- Fidelity
- Capital Group
- JPMorgan Asset Management
- Goldman Sachs Asset Management
- Morgan Stanley Investment Management
- Invesco
- T. Rowe Price
- Other major institutional managers

Track:

- Institutional ownership changes
- Fund allocations
- ETF holdings
- Sector exposure
- Public investment strategies
- Regulatory disclosures
- Relevant fund inflows and outflows

Important distinction:

Institutional ownership through client funds must not be interpreted as proprietary investment by the asset manager itself.

### 2.2 Sovereign Wealth Funds and Government Capital

Monitor:

- Sovereign wealth funds
- Public pension funds
- Government investment corporations
- Strategic national investment vehicles
- State-backed industrial investment programs

Priority entities include major sovereign investment organizations in the United States, Middle East, Asia, and Europe.

Track:

- Direct investments
- Strategic acquisitions
- Infrastructure investments
- Technology investments
- Energy investments
- Critical mineral investments
- Long-term capital allocation

### 2.3 Corporate Capital Allocation

Monitor major corporate investment decisions, including:

- Capital expenditure
- Acquisitions
- Strategic partnerships
- Manufacturing expansion
- Data-center construction
- Energy procurement
- Long-term supply agreements
- Research and development investment
- New production facilities

Focus on transactions that can materially affect future supply, demand, production capacity, or competitive positioning.

### 2.4 Insider and Executive Transactions

Monitor:

- Insider purchases
- Insider sales
- Executive transactions
- Director transactions
- Significant ownership changes
- Share repurchases
- Equity issuance

Distinguish between:

- Open-market purchases
- Open-market sales
- Scheduled trading plans
- Automatic transactions
- Compensation-related share transfers
- Tax-related transactions

A transaction must not automatically be interpreted as a bullish or bearish signal.

### 2.5 ETF and Fund Capital Flows

Monitor:

- Daily ETF flows
- Weekly fund flows
- Monthly allocation changes
- Sector ETF demand
- Commodity ETF flows
- Gold and silver fund flows
- Bitcoin and Ethereum ETF flows
- Bond fund flows
- Emerging-market fund flows

Where available, distinguish:

- Net creations and redemptions
- Trading volume
- Assets under management changes
- Market-price appreciation
- Actual investor subscriptions

Changes in AUM alone must not be treated as pure capital inflows.

### 2.6 Strategic Industrial Capital

Monitor capital allocation into:

- Artificial intelligence
- Semiconductors
- HBM memory
- Data centers
- Electricity generation
- Nuclear energy
- Uranium
- Copper
- Lithium
- Rare earth elements
- Gallium
- Germanium
- Antimony
- Tungsten
- Platinum
- Palladium
- Rhodium
- Energy storage
- Robotics
- Autonomous systems
- Aerospace
- Defense
- Industrial automation

The objective is to detect strategic capital allocation toward critical infrastructure, scarce resources, and emerging technological platforms.

## 3. Transaction Classification

Every detected capital activity must be assigned a transaction type.

| Transaction Type | Definition |
|---|---|
| DIRECT_INVESTMENT | Direct deployment of corporate or institutional capital |
| FUND_OWNERSHIP | Ownership through an investment fund |
| ETF_FLOW | Net creation or redemption activity |
| INSIDER_BUY | Insider purchase |
| INSIDER_SELL | Insider sale |
| ACQUISITION | Purchase of a company or business |
| CAPEX | Capital expenditure commitment or execution |
| PROCUREMENT | Purchase order or procurement activity |
| SUPPLY_AGREEMENT | Contractual supply arrangement |
| JOINT_VENTURE | Joint commercial or industrial investment |
| STRATEGIC_PARTNERSHIP | Commercial or strategic partnership |
| GOVERNMENT_FUNDING | Public-sector funding or financial support |
| ANNOUNCED_INTENTION | Publicly announced but unexecuted intention |
| UNVERIFIED_CLAIM | Claim without adequate supporting evidence |

Transaction types must remain distinct throughout the data pipeline.

An announced intention must never be reported as completed investment.

A purchase order must not automatically be classified as a long-term supply agreement.

## 4. Evidence and Verification Framework

Every material capital-flow event must include evidence.

### Evidence Tier A — Primary Confirmation

- Regulatory filings
- Official company disclosures
- Government publications
- Signed contracts
- Official fund disclosures
- Audited financial statements
- Official transaction announcements

### Evidence Tier B — Institutional Confirmation

- Recognized institutional research
- Established financial data providers
- Credible industry research
- Multiple independent reports

### Evidence Tier C — Secondary Reporting

- Established financial media
- Specialist commodity publications
- Industry news organizations

### Evidence Tier D — Unverified Intelligence

- Social media posts
- Anonymous sources
- Market rumors
- Unconfirmed reports

Tier D information must remain UNVERIFIED until supported by stronger evidence.

## 5. Capital Flow Event Record

Every event must be stored in a standardized structure.

```json
{
  "event_id": "GRIOS-SM-YYYYMMDD-001",
  "entity": "ENTITY_NAME",
  "entity_type": "institution",
  "transaction_type": "DIRECT_INVESTMENT",
  "target": "TARGET_COMPANY_OR_ASSET",
  "sector": "sector_name",
  "asset_class": "equity",
  "geography": "country_or_region",
  "amount": null,
  "currency": null,
  "announcement_date": null,
  "transaction_date": null,
  "source": [],
  "evidence_tier": "PENDING",
  "verification_status": "UNVERIFIED",
  "execution_status": "UNKNOWN",
  "capital_direction": "INFLOW",
  "potential_market_impact": "PENDING_ANALYSIS",
  "created_at": null,
  "updated_at": null
}
```

Unknown values must remain null.

GRIOS must never estimate an undisclosed transaction amount and present it as a confirmed figure.

## 6. Verification Status

Use the following statuses:

- VERIFIED: Supported by sufficient primary evidence.
- CORROBORATED: Supported by multiple credible independent sources.
- PARTIALLY_VERIFIED: Some elements confirmed, others unresolved.
- UNVERIFIED: Insufficient evidence.
- DISPUTED: Credible sources provide conflicting information.
- REJECTED: Evidence disproves the original claim.

Verification status must be separate from execution status.

## 7. Execution Status

Track the lifecycle of capital activity:

1. RUMORED
2. ANNOUNCED
3. APPROVED
4. SIGNED
5. COMMITTED
6. IN_PROGRESS
7. COMPLETED
8. CANCELLED
9. TERMINATED

Not every transaction follows the same lifecycle.

The system must use only statuses supported by the underlying evidence.

## 8. Capital Flow Intelligence

GRIOS should evaluate the strategic significance of each event.

Key dimensions:

### Capital Magnitude
- Absolute disclosed amount
- Relative size versus entity assets or market capitalization
- Percentage of relevant project investment
- Capital commitment duration

### Strategic Importance
- Importance of the target asset
- Supply-chain position
- Technological significance
- Market concentration
- Availability of substitutes

### Capital Concentration
- Multiple investors entering the same sector
- Repeated investments in the same supply chain
- Increasing concentration of strategic ownership
- Expansion of institutional exposure

### Persistence
- One-time transaction
- Repeated purchases
- Multi-quarter allocation
- Multi-year strategic commitment

### Market Relevance
- Potential supply reduction
- Additional production capacity
- Demand acceleration
- Competitive advantage
- Pricing power
- Regulatory or geopolitical implications

## 9. Strategic Capital Scoring

Each event should receive an analytical score from 0 to 100.

Suggested weights:

| Dimension | Weight |
|---|---:|
| Evidence Quality | 25% |
| Capital Magnitude | 15% |
| Strategic Importance | 20% |
| Capital Persistence | 15% |
| Industry Impact | 15% |
| Independent Confirmation | 10% |
| Total | 100% |

The score represents research priority and strategic significance, not investment return probability.

Missing information must be disclosed.

A high score cannot compensate for an unverified material claim.

## 10. Beneficiary Mapping Engine

After verifying a capital-flow event, GRIOS should identify potential beneficiaries.

The mapping process:

1. Identify the receiving company or asset.
2. Identify the relevant industry.
3. Map upstream suppliers.
4. Map downstream customers.
5. Identify competing producers.
6. Identify substitute technologies.
7. Identify listed companies exposed to the development.
8. Evaluate revenue and earnings sensitivity.
9. Assess valuation and execution risks.

Example:

AI data-center investment may create exposure to:

- Semiconductor manufacturers
- HBM producers
- Networking equipment
- Optical components
- Power generation
- Transformers
- Switchgear
- Cooling systems
- Energy storage
- Copper suppliers
- Uranium and nuclear energy companies

The relationship between a trend and a listed company must be demonstrated, not assumed.

## 11. Critical Materials Tracking

The engine must maintain a dedicated strategic materials database.

For each material, track:

- Global production
- Major producing countries
- Refining concentration
- Major producers
- Import dependency
- Export restrictions
- Strategic stockpiles
- New mining projects
- Processing capacity
- Long-term supply agreements
- Demand growth
- Substitution risk
- Relevant listed companies

Priority materials:

- Copper
- Lithium
- Uranium
- Rare earth elements
- Gallium
- Germanium
- Antimony
- Tungsten
- Platinum
- Palladium
- Rhodium

Element identification must be precise.

Radium and rhodium are different elements and must never be confused.

## 12. Institutional Ownership Intelligence

Institutional ownership data must be analyzed with appropriate reporting limitations.

The system should track:

- Reporting entity
- Reporting date
- Filing date
- Security identifier
- Number of shares
- Ownership percentage, if available
- Change versus prior disclosure
- Portfolio concentration
- Reporting delay

Historical filings must not be represented as real-time positions.

The system must distinguish beneficial ownership, investment discretion, fund ownership, and proprietary holdings whenever the source provides that information.

## 13. Event Deduplication and Entity Resolution

Multiple publications may report the same transaction.

GRIOS must:

- Identify duplicate events.
- Resolve company name variations.
- Match subsidiaries with parent entities.
- Normalize ticker symbols and security identifiers.
- Preserve all independent source references.
- Avoid counting repeated coverage as separate transactions.

The same transaction reported by ten news outlets remains one capital-flow event unless there is evidence of ten distinct transactions.

## 14. Alert and Priority Engine

Generate alerts for:

- Major institutional allocation changes
- Significant insider purchases
- Large disclosed acquisitions
- New strategic supply agreements
- Major industrial CapEx announcements
- Government funding of critical industries
- Supply-chain disruptions
- Significant ETF flow changes
- Multiple institutions entering the same strategic sector

Alert priority:

- CRITICAL
- HIGH
- MEDIUM
- LOW
- INFORMATIONAL

Priority must be based on verified significance and potential impact, not headline popularity.

## 15. Integration with Other GRIOS Modules

### Signal Scoring Engine

Provides verified capital-flow evidence and strategic context.

### API Source Registry

Provides source metadata, health status, freshness, and retrieval traceability.

### Megatrend Intelligence

Connects capital allocation to structural industry developments.

### Macro Intelligence

Evaluates the effects of rates, liquidity, currencies, and policy.

### Trading Intelligence

Identifies possible market implications and conditional trading scenarios.

### Daily Reporting Engine

Produces a structured summary of verified capital activity and its investment implications.

## 16. Daily Smart Money Report

The daily report should contain:

1. Executive Capital Flow Brief
2. Major Institutional Activity
3. ETF and Fund Flows
4. Insider Transactions
5. Corporate CapEx and Procurement
6. M&A and Strategic Investments
7. Critical Materials Activity
8. AI and Semiconductor Capital Allocation
9. Energy and Infrastructure Investment
10. Government and Sovereign Capital
11. Potential Listed Beneficiaries
12. Verification and Confidence Matrix
13. Investment Implications
14. Risks and Contradictory Evidence

Each item must include its date, source, verification status, and strategic interpretation.

## 17. Historical Intelligence Database

GRIOS should maintain a historical record of capital-flow events.

This enables:

- Trend detection
- Institutional accumulation monitoring
- Repeated capital allocation analysis
- Sector rotation tracking
- Strategic investment mapping
- Event impact studies
- Historical thesis evaluation

Historical records must remain traceable to their original evidence.

## 18. Performance Evaluation

Evaluate the engine using:

- Event detection accuracy
- Verification accuracy
- Duplicate detection rate
- False-positive rate
- Source coverage
- Time from disclosure to detection
- Beneficiary mapping accuracy
- Historical thesis performance

Performance evaluation must distinguish between correct event detection and profitable investment outcomes.

## 19. Security and Governance

- Never expose API credentials.
- Never store private keys in public event records.
- Preserve original source attribution.
- Log methodology changes.
- Record manual verification overrides.
- Maintain audit trails.
- Separate automated classification from human confirmation.
- Preserve historical data and corrections.

## 20. Core Operating Principle

The Smart Money Engine must not simply report what major institutions own.

It must identify what capital is being committed to, why the allocation is happening, whether the activity is confirmed, how it affects strategic supply chains, and which assets may benefit.

The central analytical question is:

**Where is informed capital moving, what structural opportunity is it targeting, and what evidence confirms the thesis?**

GRIOS v15 — We Track Capital Before The Crowd.
