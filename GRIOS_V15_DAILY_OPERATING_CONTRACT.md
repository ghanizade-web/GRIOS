# GRIOS v15 — Daily Operating Contract
**Status:** Canonical operational standard  
**Effective:** 2026-11-26  
**Mission:** We Track Capital Before The Crowd.

This document is the single operational contract for the scheduled GRIOS daily pipeline. If an older README, editorial standard, workflow comment or module note conflicts with this contract, this document governs the daily publication pipeline until an explicit versioned amendment is approved.

## 1. Two independent daily outputs

The daily pipeline produces two distinct reports from one timestamped evidence run. They must not be merged into one message or confused with Telegram message chunking.

### A. Catalyst-Driven Trading Brief
Eligible trading universe:
- Crypto assets and directly tradable crypto instruments.
- FX pairs and currency instruments.
- Commodities, including metals, energy, agriculture, uranium and strategic materials, only where a reliable market reference or tradable instrument exists.

Equities, individual company shares and equity ETFs are excluded as trading candidates. Company and equity-market developments may appear only as contextual evidence in the strategic-capital report.

Target coverage is at least 10 independent qualified candidates, but this is not a quota. If fewer than 10 pass the evidence gate, report the actual count. Do not pad with duplicate, stale or unsupported ideas.

Every LONG, SHORT or WATCH candidate must include:
- Instrument, asset class and direction.
- Latest price, quote type, provider/venue and timezone-aware timestamp.
- Fresh catalyst with publication timestamp and event date.
- Quote freshness gate: maximum age 30 minutes for crypto and 24 hours for FX/commodities; future-dated quotes are rejected.
- Catalyst publication must be timezone-aware, not future-dated beyond tolerance, and no older than 72 hours.
- Causal transmission from catalyst to instrument.
- Observable activation trigger.
- Explicit invalidation.
- Horizon, risk label and evidence grade.
- HTTPS source references.

Evidence grade C is WATCH-only. Missing price, catalyst, timestamp, trigger, invalidation or source means rejection. No candidate object means “No confirmed trade; monitor only.” The system must not invent entries, stops, targets, order-flow levels or institutional activity.

### B. Strategic Capital Flows & Megatrends
This report tracks the structural themes in the user-approved daily megatrend framework:
1. Critical materials and hard-to-substitute inputs: copper, lithium, uranium, rare earths, gallium, germanium, antimony, tungsten, platinum, palladium, rhodium, graphite, nickel, cobalt and other officially designated strategic materials.
2. Institutional capital and major asset managers, sovereign wealth funds and public investment vehicles.
3. Industrial and technology megatrends: AI and data centres, semiconductors, power grids, nuclear, robotics, autonomy, aerospace, drones, defense, storage and advanced manufacturing.
4. Corporate procurement and capital allocation: filings, financial statements, purchase orders, supply/offtake agreements, acquisitions, CapEx, mine/refining projects, production expansion and government procurement.
5. Conversion of verified evidence into opportunities: catalyst, horizon, valuation, liquidity, geopolitical exposure, beneficiary mapping and thesis invalidation.

The report must distinguish:
- Rumour, reported claim, official announcement and verified primary evidence.
- Expression of interest, announced plan, approved project, signed contract, committed CapEx, in-progress activity and completed transaction.
- Purchase order, supply contract, equity investment, acquisition, grant, ETF flow and disclosed holdings.
- Assets managed for clients from a manager's proprietary investment.
- A manager's 13F-reported holdings snapshot from real-time buying or selling.

A 13F filing is a delayed quarterly holdings disclosure. It does not identify trade dates, prove current buying, reveal short positions, establish beneficial ownership in every case, or prove the manager invested proprietary capital. Client fund holdings may be represented. Never call a 13F position a fresh purchase without independent transaction evidence.

A strategic theme is not automatically an investable opportunity. Beneficiary mapping requires demonstrable exposure; valuation, liquidity and execution risks must be evaluated separately. A company must not be named as a beneficiary solely because a keyword appears in its business description.

## 2. Source hierarchy and evidence contract

Prefer:
1. Official filings, regulators, government procurement records, statistical agencies, exchanges and signed corporate disclosures.
2. Established financial newswires and financial press.
3. Specialist sector datasets and market-data providers with methodology and timestamps.
4. On-chain, analyst and social material only as supporting leads, never as sole proof of material capital activity.

Every source-backed item should retain source URL, publisher, publication timestamp, event date when known, evidence tier, retrieval timestamp and verification status. RSS headlines/excerpts are not full-text research. An excerpt does not prove transaction execution.

Unknown amounts remain unknown. Do not infer undisclosed purchase values, proprietary capital, fund flows, contract execution or production capacity. Do not confuse Radium with Rhodium.

## 3. Current executable coverage and limitations

The current dual-output builder consumes:
- The configured 72-hour source-attributed RSS intelligence file.
- The SEC 13F watchlist snapshots when SEC_USER_AGENT and Supabase credentials are configured.
- A candidate JSON contract for the trading brief.

The trading-candidate contract is deliberately fail-closed. Until the upstream scanner emits a candidate record that satisfies every required field, the trading brief reports no confirmed trade rather than relabelling the legacy integrated market recap as a trading recommendation.

The current capital-flow report is an initial operational evidence feed, not complete institutional-flow surveillance. It does not yet provide comprehensive coverage of:
- Every SEC filing, all institutional managers or beneficial ownership disclosures.
- ETF creations/redemptions across all issuers and asset classes.
- Sovereign wealth fund transactions.
- Private purchase orders, private supply contracts and all government procurement databases.
- Full issuer-level valuation and beneficiary modelling.

A missing feed or no matching headline is a coverage limitation, not proof that no activity occurred. Report feed status and missing coverage. Do not describe the Megatrend Registry as a live crawler until ingestion, persistence and end-to-end validation are proven.

## 4. Canonical outputs and archive

Each run must produce:
- reports/trading-brief-latest.txt
- reports/capital-flows-latest.txt
- reports/trading-brief-audit.json
- reports/capital-flows-evidence.json
- Dated independent archives for each report and its evidence.
- Source GRIOS commit SHA, workflow run ID, report date, quality-gate result and publication state.

The two Telegram posts must be separate sends. Multiple chunks within one post are not multiple reports. Capture the Telegram message_id for every sent chunk and archive the IDs against the report filename.

## 5. Quality gates

Before either report can be published:
- Both output files exist, are non-empty, contain Persian copy and include the social footer.
- Trading candidates pass the strict schema; only crypto, FX and commodities are eligible.
- Evidence grade C cannot produce LONG or SHORT.
- Each candidate has a fresh timestamped quote, catalyst, transmission, trigger, invalidation, horizon, risk and HTTPS source.
- Capital-flow items have a fresh source URL and publication timestamp.
- 13F caveats are present whenever holdings are reported.
- Reported claims are not upgraded to verified transactions without primary evidence.
- The two reports are independently archived and independently validated.
- Telegram delivery is counted only after API success and a returned message ID for each chunk.

A workflow success status alone is not evidence that a report met the editorial contract or was published.

## 6. Schedule and publication control

The canonical scheduled run is 07:30 UTC. This corresponds to 08:30 in the Netherlands during winter time and 09:30 during summer time. The report date and archive date use Europe/Amsterdam.

Until the new outputs pass an end-to-end acceptance run and the user approves the content, scheduled runs may build and archive reports but must not publish to the public Telegram channel. Telegram publication is enabled only by an explicit manual dispatch with publish_to_telegram=true. After acceptance and approval, the schedule may be changed to automatic publication in a separately recorded change.

## 7. Social footer

Include the following links in publication-ready reports:
- Instagram: https://www.instagram.com/dr.ghanizade
- X: https://x.com/DrGhanizadeh
- LinkedIn: https://www.linkedin.com/in/drghanizade
- Farcaster: https://farcaster.xyz/drghanizade
- GitHub: https://github.com/ghanizade-web

## 8. Acceptance criteria

The pipeline is not “fixed” until a controlled GitHub Actions run demonstrates:
1. Two different report files with independent report types and audit artifacts.
2. Persian translation and content validation for both.
3. No equities/equity ETFs as trading candidates.
4. Capital-flow report with explicit evidence tier, source lineage and 13F caveats.
5. Two separate Telegram sends when explicitly authorized.
6. A distinct Telegram message ID for each sent chunk, archived with run ID and source commit.
7. A later scheduled run uses the new pipeline and does not regress to the legacy single-report publisher.

**Operational rule:** no successful end-to-end evidence, no “fixed” claim.
