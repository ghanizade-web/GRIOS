# GRIOS market report preferences

Use this as the durable editorial brief for GRIOS market reports.

The owner's broader operating blueprint is recorded in [GRIOS_OPERATING_MANUAL_v1.md](GRIOS_OPERATING_MANUAL_v1.md). Treat its agent organization, G-Score labels, and roadmap as intended design unless implementation and validation are explicitly verified. This report brief and `GRIOS/docs/COMMANDS.md` describe current evidence and command limits.

## Scope and style
- Write in fluent Persian, compact but substantive, ready to paste into Telegram; use clear headings, meaningful emojis, horizontal dividers and readable mobile-sized sections.
- Every human-readable report and Telegram publication must be right-to-left (RTL). Isolate Persian lines from Latin tickers, numbers, URLs and technical identifiers so mixed-direction text remains readable.
- Keep machine-readable JSON, API schemas, provider names, tickers, CIKs, CUSIPs and source URLs unchanged; localize the human-facing explanation and labels.
- Use explicit Persian labels for data freshness, reporting period, publication time, confidence, caveats, data coverage and pipeline status. Never translate a status in a way that changes its technical meaning.
- Exclude Iran's stock market. Cover global equities (especially US, and relevant Asia/Europe), FX, crypto, and commodities (energy, precious/base metals, and agriculture) only where a current catalyst or meaningful signal exists.
- The report has no fixed number of assets. Include only the assets materially affected by important, source-confirmed news or data from the day/week. The count may vary from zero to several; never add assets just to fill a quota. Explain the specific beneficiary/loser channel for every included asset.
- Prioritize differentiated, evidence-backed asset theses over quote boards and headline lists. Include prices only as useful anchors, with source and observation time.
- The reader should receive useful daily and weekly decision-support signals: conditional directional bias, expected horizon, asset-specific catalyst, causal transmission, confirmation trigger, invalidation condition, opposing scenario, and confidence. This is research, not a personalized trade instruction.
- Separate reported facts, market expectations, and GRIOS inference. Cross-check important claims when feasible. Mark delayed, indicative, conflicting, or non-independent data. Never invent prices, targets, news, flows, institutional accumulation, technical levels, consensus, or certainty.
- Do not issue personal buy/sell instructions, execute orders, allocate capital, or guarantee returns. A signal is a conditional scenario, never a command to trade.
- If quality evidence is absent, explicitly say «سیگنال معتبر نداریم» for that asset or horizon instead of filling space.

## Required causal analysis for every signal
For each signal, state all of the following in Persian:
1. **خبر یا داده محرک:** dated, source-confirmed development; distinguish a news catalyst from a scheduled event and from price action.
2. **دارایی و جهت نسبی:** name the instrument/exposure and explain what “up” or “down” means. For FX, explain both sides of the pair.
3. **زنجیره اثر:** show how the catalyst can affect expectations, rates, earnings/cash flows, supply/demand, risk appetite or funding, and then the asset. Do not claim causality from co-movement alone.
4. **شواهد و مخالفت:** provide the strongest available support and the strongest relevant counter-evidence; state what is already priced in or remains speculative when known.
5. **سیگنال مشروط و افق:** choose صعودی، نزولی، خنثی/انتظار, or no signal; label it روزانه (جلسه/۱ تا ۳ روز) or هفتگی (حدود ۱ تا ۴ هفته). Do not give unsupported entry, target or stop prices.
6. **تأیید و ابطال:** specify observable evidence that would strengthen the thesis and a concrete condition that would weaken or invalidate it. Avoid vague wording such as “if the market changes.”
7. **اطمینان و رویداد بعدی:** assign بالا/متوسط/پایین with a one-line reason, and give the next dated catalyst only when a reliable calendar confirms it.

Do not force every headline into a signal. News without a plausible transmission mechanism or asset-level confirmation belongs in a short “خبر مهم، بدون سیگنال” note or is omitted.

## Daily report order
1. Reporting timestamp, timezone, freshness and coverage caveat.
2. One-line cross-asset regime and the main verified catalyst(s).
3. A variable number of the strongest daily/weekly asset signals, selected according to the importance, novelty and asset-level transmission of verified news. Each signal uses the causal-analysis fields above. There is no minimum or fixed target count.
4. Brief “مهم اما بدون سیگنال” notes when a major headline cannot be linked reliably to an asset.
5. Upcoming source-confirmed catalysts with exact verified date/time precision; no inferred times or consensus.
6. Concise overall takeaway distinguishing the daily tactical view from the weekly view.
7. Compact official-profile footer (Telegram, Instagram, X, LinkedIn, TradingView).

## Weekly view
- Maintain a separate 1–4 week horizon. Summarize the week's dominant verified catalysts, beneficiaries/losers by asset, what changed versus the prior report when known, and the main event/risk that could invalidate the view.
- Do not stretch a one-day price move into a weekly thesis. A weekly view requires a structural, macro, earnings, policy, positioning or supply/demand channel that can plausibly persist.
- Where no durable weekly catalyst is verified, state «برای افق هفتگی شواهد کافی نیست».

## Idea-generation approach: follow the causal chain
- Look for opportunities by connecting a structural change to its bottleneck, cash flows, and investable exposures—not by repeating headlines or listing daily movers.
- Trace longer themes as: secular/macro driver → physical, regulatory, financing, or supply-chain bottleneck → companies/commodities/currencies likely to benefit or lose → evidence of demand turning into contracts, orders, prices, or cash flow → what would invalidate the thesis and on what horizon.
- Example: AI data-center electricity demand → firm power and grid connection constraints → gas-fired generation, coal where locally relevant, nuclear fuel/uranium, grid equipment, transformers, turbines, and power developers. Distinguish near-term beneficiaries from long-lead-time themes; do not infer uranium demand directly from AI growth without reactor buildout, fuel contracts, or procurement evidence.
- Separate investable, evidence-supported opportunities from early hypotheses worth monitoring. Highlight when a theme may already be priced in, when the bottleneck lies elsewhere, and who bears the downside.
- Prefer primary evidence for confirmation: company filings and investor releases, grid/operator and utility plans, regulator and government data, signed power/fuel/supply contracts, procurement orders, project permits, inventory/production data, and credible sector statistics. Use research/news commentary to discover ideas and competing interpretations, then cross-check important claims independently.

## News-to-asset coverage requirement
- Before publishing a directional signal attributed to a news story, verify the story's publication time, primary source where available, and at least one independent corroborating source for material claims.
- If no news feed or current source is available to the daily pipeline, do not simulate a news-driven signal. Clearly disclose that news coverage is unavailable and limit analysis to verified market data/events.
- Never imply that social sentiment, volume, open interest, price action or a scheduled calendar item proves institutional buying or predicts direction.
- News can affect assets differently: explicitly identify likely beneficiaries and harmed exposures, and explain the transmission for each instead of applying one headline to all markets.

## Research sources to consider
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

Broker/exchange referral URLs are not part of the recurring market-report footer; include them only when the user explicitly asks for a broker/exchange promotional post.