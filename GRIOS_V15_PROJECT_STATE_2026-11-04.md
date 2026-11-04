# GRIOS Terminal v15
## Project State, Architecture & Continuity Log

**Date:** 2026-11-04  
**Project:** Ghanizadeh Research Intelligence Operating System  
**Version:** v15 Institutional Edition  
**Mission:** We Track Capital Before The Crowd.  
**Status:** Active Development

---

# 1. Project Identity

GRIOS v15 is the official development branch and
institutional research framework.

This document is the continuity record for project
standards, architecture, reporting requirements,
repository access, integration plans and outstanding work.

Older experimental versions (v7, v12, v13, v14)
must not be treated as the current source of truth.

---

# 2. GitHub Repository Access Status

The GitHub integration successfully returned the
following repositories and permissions on 2026-11-04:

| Repository | Visibility | Reported Access |
|---|---|---|
| ghanizade-web/GRIOS | Public | Admin / Read / Write |
| ghanizade-web/market-pulse | Private | Admin / Read / Write |
| ghanizade-web/Walter-bloomberg | Public | Admin / Read / Write |
| ghanizade-web/freebuff | Public | Admin / Read / Write |

Important:
Repository listing and permission visibility do not
prove that repository source code has been audited,
that APIs are operational, or that credentials work.

No repository source-code audit or commit is recorded
by this document.

---

# 3. market-pulse Integration

The private repository `ghanizade-web/market-pulse`
is designated as a specialized data-source layer.

The user has stated that it contains credentials for:
- Two oil and energy data websites.
- Federal Reserve / FRED data.

Intended architecture:

market-pulse
    |
    v
Secure Data Adapters
    |
    v
GRIOS Data Hub
    |
    v
Data Validation & Normalization
    |
    v
GRIOS v15 Intelligence Engine
    |
    v
Daily Market & Investment Intelligence

Integration objectives:

1. Retrieve oil and energy market information.
2. Retrieve Federal Reserve and macroeconomic data.
3. Normalize timestamps, units and source identifiers.
4. Validate data freshness and completeness.
5. Detect missing values and conflicting observations.
6. Make validated data available to GRIOS analysis.
7. Preserve source attribution and auditability.

Current status:
Repository access was confirmed through GitHub repository
listing. Internal code inspection, API execution and
credential validation remain pending.

---

# 4. Security Requirements

These requirements are mandatory.

- Never expose API keys or private credentials in reports.
- Never place private credentials in frontend code.
- Keep credentials in server-side secret storage.
- Never print secrets in logs.
- Never commit secret values to public repositories.
- Do not make market-pulse public.
- Inspect secret names and storage locations only when
  possible; never disclose secret values.
- Validate access controls and server-side authorization.
- Rotate credentials if accidental exposure is detected.

Preferred architecture:
Cloudflare Worker secret bindings or another secure
server-side secret manager.

---

# 5. GRIOS Daily Report Standard

Official report title:

GRIOS v15 | Daily Market & Investment Intelligence

The daily report combines market intelligence,
institutional capital tracking and investment opportunities.

Required sections:

1. Executive Brief / Macro Dashboard
2. Geopolitics & Policy
3. Macro & Interest Rates
4. Commodities
5. Foreign Exchange
6. Equity Indices & Sector Intelligence
7. Cryptocurrency
8. Smart Money & Institutional Capital Flows
9. Megatrends
10. Trading Opportunities
11. Investment Watchlist
12. Risk Matrix
13. Event Calendar / Next 24–72 Hours
14. Final Executive View
15. Social Links

Coverage:
- United States
- China
- Europe
- Iran and the Middle East
- Global financial markets

Markets:
- DXY and major FX pairs
- US Treasury yields
- Oil and natural gas
- Gold and silver
- Copper and strategic metals
- Uranium and critical minerals
- Global equity indices
- Technology and semiconductor stocks
- Bitcoin and Ethereum
- Institutional capital flows

---

# 6. Smart Money & Strategic Capital Flows

A permanent GRIOS research module.

Research objectives:

- Track institutional ownership changes.
- Track fund inflows and outflows.
- Monitor major acquisitions and strategic deals.
- Monitor company CapEx and procurement.
- Track supply agreements and long-term contracts.
- Identify strategic investments in critical materials.
- Identify bottlenecks in industrial supply chains.

Priority themes:

## Critical Materials
Lithium, copper, uranium, rare earth elements,
gallium, germanium, antimony, tungsten,
platinum, palladium and rhodium.

## Technology & Infrastructure
AI, data centers, semiconductors, HBM,
robotics, autonomous vehicles, aerospace,
defense technology, energy storage and nuclear power.

## Institutional Capital
Asset managers, sovereign wealth funds,
strategic investors and major corporations.

Verification rules:

- Distinguish direct corporate investment from
  ownership of client funds managed by an asset manager.
- Distinguish completed acquisitions from proposed deals.
- Distinguish purchase orders from supply agreements.
- Distinguish signed contracts from announcements of interest.
- Do not present unverified social media claims as facts.
- Use regulatory filings, official disclosures and
  independent evidence whenever available.

Terminology warning:
Radium and Rhodium are different chemical elements.
Do not confuse them.

---

# 7. Analytical Standards

Every important development should be analyzed through:

Cause
    ->
Transmission Mechanism
    ->
Asset / Sector Impact
    ->
Scenario
    ->
Invalidation Conditions

Separate:
- Confirmed facts
- Official company disclosures
- Independent reporting
- GRIOS interpretation
- Inference
- Speculation

Never fabricate:
- Market prices
- Institutional flows
- Technical levels
- Order-flow signals
- Entry or exit prices
- Stop losses
- Targets
- Risk/reward ratios

If reliable market or chart data is unavailable,
provide conditional scenarios rather than invented
trading levels.

Trading opportunities should specify:
- Instrument / ticker
- Direction
- Fundamental catalyst
- Activation condition
- Entry / stop / target, only when supported
- Time horizon
- Risk and invalidation conditions

Investment watchlists must consider:
- Growth catalyst
- Valuation
- Liquidity
- Geopolitical exposure
- Supply-chain position
- Time horizon
- Thesis invalidation

---

# 8. AI Infrastructure & Energy Megatrend

A priority research theme.

Core thesis to investigate:

AI infrastructure is becoming an energy and grid
investment cycle.

Monitor the full value chain:

AI compute demand
    ->
Data center expansion
    ->
Power generation
    ->
Transmission and grid capacity
    ->
Transformers and electrical equipment
    ->
Cooling systems
    ->
Energy storage
    ->
Nuclear and other reliable power sources

Do not limit analysis to GPU manufacturers.

Track companies involved in:
- Semiconductors and HBM
- Data center infrastructure
- Power generation
- Grid equipment
- Transformers
- Cooling
- Nuclear energy
- Energy storage
- Strategic materials

---

# 9. Reference File

Project reference file:

`گزارش روزانه مگاترندها.txt`

This file establishes the following permanent analytical
requirements:

1. Strategic materials and critical minerals.
2. Institutional capital and major asset managers.
3. Industrial and technological megatrends.
4. Corporate acquisitions, procurement and CapEx.
5. Conversion of research into investment opportunities.
6. Evidence-based verification of major claims.
7. Distinction between client-fund ownership and
   direct corporate investment.

This reference should remain part of the GRIOS
analytical knowledge base.

---

# 10. Sample Report Record — 2026-11-04

A combined sample report was generated in ChatGPT:

Title:
GRIOS v15 | Daily Market & Investment Intelligence

Main themes covered:

- US political developments and market reaction.
- Dollar and Treasury yield movements.
- Gold and oil market risks.
- Middle East energy supply exposure.
- Critical minerals and strategic investment.
- AI infrastructure and electricity demand.
- PJM grid capacity constraints.
- AMD Q3 2026 results and data-center growth.
- Institutional capital verification standards.
- Conditional investment watchlists.
- 24–72 hour risk monitoring.

Important limitations:

This sample used public research and the project
reference file.

It did not use verified live API responses from
market-pulse.

It did not establish that private credentials or
data adapters were operational.

No trading entry, stop or target was invented
without supporting technical evidence.

---

# 11. Integration Work Remaining

The following tasks remain open:

[ ] Inspect market-pulse repository structure.
[ ] Identify oil and energy data providers.
[ ] Identify FRED data adapters.
[ ] Inspect credential variable names without
    exposing credential values.
[ ] Verify server-side secret storage.
[ ] Inspect Cloudflare Worker configuration.
[ ] Verify API authentication and authorization.
[ ] Test each provider endpoint securely.
[ ] Record source timestamps and units.
[ ] Implement data normalization.
[ ] Implement data quality checks.
[ ] Connect validated adapters to GRIOS Data Hub.
[ ] Verify GRIOS frontend never receives private keys.
[ ] Add source-level audit logs.
[ ] Run end-to-end integration tests.
[ ] Document operational failures and fallbacks.

Do not mark a task complete until evidence exists.

---

# 12. Operational Continuity Rules

At the beginning of each new GRIOS session:

1. Treat this document as the project continuity record.
2. Review the latest repository state when access permits.
3. Check whether integration tasks have changed.
4. Do not assume previous API tests succeeded.
5. Do not assume credentials are valid merely because
   the repository is accessible.
6. Use the latest verified data, not stale values.
7. Preserve the reporting and verification standards.
8. Record significant architectural changes in GitHub.

The latest committed version of this document
should be treated as the durable project state.

---

# 13. Research & Publication Links

Instagram:
https://www.instagram.com/dr.ghanizade

X:
https://x.com/DrGhanizadeh

LinkedIn:
https://www.linkedin.com/in/drghanizade

Farcaster:
https://farcaster.xyz/drghanizade

GitHub:
https://github.com/ghanizade-web

---

# 14. Final Project Principle

GRIOS does not merely report what markets did.

It investigates:
- Where capital is moving.
- Why capital is moving.
- Which bottlenecks are becoming strategic.
- Which companies control critical assets.
- What the market has already priced in.
- What could invalidate the investment thesis.

Mission:

WE TRACK CAPITAL BEFORE THE CROWD.
