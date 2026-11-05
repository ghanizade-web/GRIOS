# GRIOS market report preferences

Use this as the durable editorial brief for GRIOS market reports.

The owner's broader operating blueprint is recorded in [`GRIOS_OPERATING_MANUAL_v1.md`](GRIOS_OPERATING_MANUAL_v1.md). Treat its agent organization, G-Score labels, and roadmap as intended design unless implementation and validation are explicitly verified. This report brief and `GRIOS/docs/COMMANDS.md` describe current evidence and command limits.

## Scope and style
- Write in fluent Persian, compact and engaging, ready to paste into Telegram; use clear headings, meaningful emojis, horizontal dividers and readable mobile-sized sections.
- Every human-readable report and Telegram publication must be right-to-left (RTL). Isolate Persian lines from Latin tickers, numbers, URLs and technical identifiers so mixed-direction text remains readable.
- Keep machine-readable JSON, API schemas, provider names, tickers, CIKs, CUSIPs and source URLs unchanged; localize the human-facing explanation and labels.
- Use explicit Persian labels for data freshness, reporting period, publication time, confidence, caveats, data coverage and pipeline status. Never translate a status in a way that changes its technical meaning.
- Exclude Iran's stock market. Cover global equities (especially US, and relevant Asia/Europe), FX, crypto, and commodities: energy, precious/base metals, and agriculture when there is a meaningful signal.
- Prefer a small set of differentiated, evidence-backed signals over a long quote board. Include prices only as useful anchors, with source and observation time; spend more space on why the move matters.
- For each selected signal explain the catalyst, the causal link to the asset, the supporting and opposing evidence, what would confirm or invalidate the thesis, and the next dated/near-term event when verified.
- Separate facts from inference. Cross-check important market claims when feasible. Mark delayed, indicative, conflicting, or non-independent data. Never invent prices, targets, news, flows, institutional accumulation, or certainty.
- Do not claim social sentiment, volume, open interest, or price action proves institutional buying. Do not issue personal buy/sell instructions, execute orders, allocate capital, or guarantee returns.
- Keep the final takeaway useful and short. If no quality signal is supported, say so plainly rather than filling space.

## Idea-generation approach: follow the causal chain
- Look for opportunities by connecting a structural change to its bottleneck, cash flows, and investable exposures—not by repeating headlines or listing daily movers.
- Trace each thesis as: secular/macro driver → physical, regulatory, financing, or supply-chain bottleneck → companies/commodities/currencies likely to benefit or lose → evidence of demand turning into contracts, orders, prices, or cash flow → what would invalidate the thesis and on what time horizon.
- Example: AI data-center electricity demand → firm power and grid connection constraints → gas-fired generation, coal where locally relevant, nuclear fuel/uranium, grid equipment, transformers, turbines, and power developers. Distinguish near-term beneficiaries from long-lead-time themes; do not infer uranium demand directly from AI growth without reactor buildout, fuel contracts, or procurement evidence.
- Separate an investable, evidence-supported opportunity from an early hypothesis worth monitoring. Highlight when a theme may already be priced in, when the bottleneck lies elsewhere, and who bears the downside.
- Prefer primary evidence for confirmation: company filings and investor releases, grid/operator and utility plans, regulator and government data, signed power/fuel/supply contracts, procurement orders, project permits, inventory/production data, and credible sector statistics. Use research/news commentary to discover ideas and competing interpretations, then cross-check important claims independently.

## Forex explanation standard
- Always explain pair direction in plain Persian. For NZD/USD, a rise means the New Zealand dollar is strengthening against the US dollar; a fall means it is weakening.
- Explain the cause: what changed in the relative outlook for the two economies or central banks, how that affects expected interest-rate differences or risk demand, and why it could move the pair.
- Separate confirmed decisions from market expectations and inference. Include the opposing scenario, the next dated catalyst, and what would invalidate the view. If evidence is insufficient, say so instead of implying a trade signal.

## Adapted workflow from day-trader-skill

- Reference: [Jakeschincariol/day-trader-skill](https://github.com/Jakeschincariol/day-trader-skill), reviewed 2026-10-26. Its 11 Claude-oriented modules cover a US-equity chart scanner, news monitor, entry/exit planning, historical replay, risk/budget checks, broker tickets, alerts, SEC earnings facts, and delayed House-trade disclosures.
- Adapt only the research methods for GRIOS reports: scan a stated US-stock universe for rule-matching setups; pair chart context with a verified, dated catalyst and opposing evidence; use SEC/company filings for earnings facts; disclose scan coverage, timestamp, source freshness, partial results and missing data; keep dated ideas for later outcome review.
- A scanner match is a watchlist candidate, never a buy signal. Historical replay is evidence only when the rule, sample, timeframe, costs and out-of-sample limitations are disclosed; simulation frequencies are not forecasts or calibrated probabilities. Congressional disclosures are delayed public records, not proof of current institutional accumulation or superior returns.
- The reference implementation is US-equity-focused and partly relies on Yahoo endpoints that its README calls unofficial and potentially delayed or rate-limited. It does not provide native FX, crypto or commodity analysis. Do not claim its scripts are installed, run or integrated into GRIOS unless verified; adapt methods only to valid market-specific data.
- Keep GRIOS research-only: do not import its broker, order-ticket, personalized position-sizing, or automated entry/exit workflow into reports. No order execution, personal allocation, guaranteed outcome, or unsupported entry/target/stop.



## SEC Company Facts fundamentals\n- Select facts by exact SEC accession number, form and report-end date; preserve XBRL tag, unit, period start/end and filing date.\n- Do not convert year-to-date or annual amounts into standalone quarterly values unless the derivation is explicit, validated and separately labeled.\n- Keep reported facts separate from analyst estimates, management guidance, consensus, valuation and GRIOS interpretation.\n- Treat the configured issuer list as a watchlist sample, not market-wide coverage.\n\n## Forward performance tracking\n- Report only matured forward observations from the SQLite journal. Keep checkpoint tolerances visible and do not annualize short-horizon returns.\n- Show sample size alongside average, median and positive-return rate. Warn when the sample is small; do not infer statistical significance from a small number of outcomes.\n- Describe this as forward paper tracking, not a backtest. Disclose missing transaction costs, slippage, benchmark comparison, survivorship controls and full point-in-time replay.\n\n## CFTC positioning taxonomy\n- Keep Legacy, Disaggregated and TFF reports separate; do not merge participant categories across reports.\n- Disaggregated: Producer/Merchant, Swap Dealers, Managed Money and Other Reportables. TFF: Dealer/Intermediary, Asset Manager/Institutional, Leveraged Funds and Other Reportables. Non-reportable positions may be shown separately but must not be conflated with reportable categories.\n- Use Futures Only and Futures-and-Options Combined as distinct datasets. Never combine their positions or historical percentiles.\n- These are weekly Tuesday exposures released later, not trade records, named fund holdings, beneficial ownership or real-time flows.\n\n## Commodity inventory reporting\n- Distinguish inventory stock levels from weekly production, imports, exports and product supplied; do not mix units or describe a stock-level change as a transaction flow.\n- Preserve the EIA observation week separately from retrieval time. If the API does not provide a publication timestamp, label it unavailable.\n- Do not describe a stock draw/build as a directional oil signal without checking production, imports, exports, refinery inputs, product supplied, SPR changes and the relevant demand context.\n- Do not claim an inventory surprise without a separately sourced, timestamped consensus estimate.\n\n## Event calendar and catalyst discipline\n- Use official release calendars for event dates and preserve the source's exact date and time precision. If the source provides only a date, do not invent an hour or timezone.\n- Keep consensus, actual result, revision and surprise as unavailable until a source explicitly provides them. A calendar event alone does not justify a directional market thesis.\n- Mark events as source-confirmed calendar entries, not as verified market catalysts; assess impact only after expectations, actual release and market reaction can be compared.\n\n## Research sources to consider
- Idea discovery and investment theses: [Capitalist Exploits](https://capitalistexploits.at/), [CAPEX Insider](https://capexinsider.com/), [Real Vision](https://www.realvision.com/your-future), and [Seeking Alpha](https://seekingalpha.com/), plus comparable global research/commentary sources when relevant and accessible.
- These are leads and viewpoints, not automatic confirmation. Note paywalls, author incentives, publication dates, and whether claims are independently verified. Do not imply access to subscriber-only material when unavailable.
- For validation, prioritize primary sources and high-quality independent reporting/data: company filings and releases, SEC, EIA, FRED, CFTC, grid operators, energy agencies, exchange/inventory data, and other relevant regulators or statistical agencies. Cite the source nearest to the claim.

## Official profile links for Telegram-ready post footer
- Telegram: https://t.me/drghanizade
- Instagram: https://www.instagram.com/dr.ghanizade
- X: https://x.com/DrGhanizadeh
- LinkedIn: https://www.linkedin.com/in/drghanizade
- Farcaster: https://farcaster.xyz/drghanizade
- GitHub: https://github.com/ghanizade-web
- Medium: https://medium.com/@drghanizade
- TradingView: https://www.tradingview.com/u/DrGhanizadeh
- Clubhouse: https://www.clubhouse.com/@drghanizade
- Virgool: https://virgool.io/@Drghanizade
- Substack: https://substack.com/@drghanizade
- YouTube: https://www.youtube.com/@drghanizade

Use a compact footer by default: Telegram, Instagram, X, LinkedIn, and TradingView; add other profiles only when relevant or requested. Link directly to relevant TradingView charts in the body when useful.

The supplied broker/exchange referral URLs are not part of the recurring market-report footer; include them only when the user explicitly asks for a broker/exchange promotional post.
