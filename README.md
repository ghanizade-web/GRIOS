# GRIOS Opportunity Scanner — MVP

Small, research-only Python scanner using direct CoinGecko and CoinMarketCap REST adapters for crypto, plus OpenBB provider connectors for listed equities/ETFs, ECB FX reference data, EIA energy series, and FRED macro context. It writes a Persian, Telegram-friendly text report, a machine-readable crypto audit JSON, and local SQLite snapshots/idea outcomes. Normalized market observations are written directly to the GRIOS Supabase Data Hub (`public.grios_market_observations`) through the Supabase REST API using server-side credentials; Cloudflare Worker/Data Hub is not part of the active architecture. A separate `market-pulse` repository contains a Twelve Data adapter that writes to the same Supabase table. The scanner itself does not place orders and does not claim validated alpha.

## Actual MVP coverage

- **Crypto spot:** queries CoinGecko markets (up to 250 rows) and CoinMarketCap quotes (up to 500 rows) directly, using `COINGECKO_API_KEY` and `COINMARKETCAP_API_KEY`. Requested symbols are checked against provider responses; provider timestamps, missing symbols, invalid/stale observations, duplicate ticker ambiguity, identity-name mismatch, and cross-source price deviations are recorded in `crypto-audit-<timestamp>.json`. The 2% cross-source price-deviation threshold is a data-quality gate, not a trading rule. The current adapters request the top market-cap pages only; they do not yet make per-symbol fallback requests for missing assets.
- **US/global shares and sector ETFs:** OpenBB V5 Cboe daily history for broad US indices, small caps, sector leadership, AI/semiconductor names, developed/emerging market proxies, and fixed-income ETFs. These are research history feeds, not executable quotes. The provider's coverage and terms control actual freshness.
- **Commodity proxies:** the same Cboe equity connector covers broad commodities, gold, silver, oil, natural gas, copper/base metals and agriculture ETF proxies. These are not underlying spot prices or futures; roll/tracking/issuer risks remain.
- **Oil and gas:** OpenBB EIA series for Brent spot and Henry Hub spot. They are published data, not a real-time futures feed. The MVP does not rank them as complete supply/demand theses because inventory, forward curve and dated catalysts are not joined to the price score.
- **Forex:** ECB reference-rate histories for a wider set of EUR pairs, plus the FRED broad dollar index. These are not bid/ask quotes and do not support direct execution rankings.
- **Macro context:** FRED daily observations for US 2Y/10Y yields, broad dollar index and VIX close. Each value keeps its observation date; this is context, not an automatic risk-on/off decision.
- **CFTC positioning:** `cftc_cot.py` and `cftc_advanced_positioning.py` ingest Legacy, Disaggregated Futures Only and TFF Futures Only reports. The daily briefing reads the latest validated CFTC records from Supabase, compares participant categories and flags positioning crowding/divergence. These are weekly exposures, not transaction-level flows or named fund holdings; futures-and-options combined datasets are kept separate.
- **Gold, silver and industrial metal outright prices:** not covered as underlying contracts in this MVP. Add an exchange-licensed source before ranking these markets.

Scores are **technical watch scores**, not G-Scores, expected returns, or trade signals. Current weights are visible in `market_score()`: crypto momentum 40%, multi-window alignment 30%, volume/market-cap turnover 20%, FDV/market-cap 10%; equities trend 35%, momentum 25%, volatility 20%, relative volume 20%; energy series trend 40%, momentum 35%, volatility 25%. Weights renormalize over available factors and the report shows factor coverage. If same-name crypto feeds disagree on price by more than 2%, that asset is suppressed; this threshold is a data-quality guard, not a calibrated market rule. The editorial daily report now uses a curated RSS news collector, official macro/energy/regulatory sources, CFTC weekly positioning and a cross-asset opportunity screen. For each selected market story it prints the available RSS excerpt, a market-specific transmission analysis, the exposed assets/sectors and a source verification link. It does not claim to have read full paywalled articles; when a feed provides no excerpt, the report explicitly discloses that gap. The current synthesis is deterministic and rule-based, not a hosted LLM full-text research service. No verified SEC 13F snapshot is currently available. Valuation and personalized portfolio suitability remain outside the daily screen, so opportunity labels are research candidates rather than direct buy instructions.

## Setup

Use Python 3.10–3.14 in a virtual environment. OpenBB V5 is modular; install the exact required provider connectors listed here:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
cp watchlist.example.json watchlist.json
```

Edit `.env` and `watchlist.json`. Set `COINGECKO_API_KEY` and `COINMARKETCAP_API_KEY` for the direct crypto adapters, `EIA_API_KEY` for EIA, and `FRED_API_KEY` for macro series. Keep all credentials in `.env` or the CI secret store; never place them in URLs, source files, audit JSON, or logs. The script loads local environment variables via `python-dotenv`; `.env` is gitignored. In GitHub Actions, the GRIOS scanner workflow supplies provider credentials as repository secrets. For persistent Data Hub publishing, set `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` as server-side GitHub Actions secrets. The scanner writes directly to `public.grios_market_observations`; never expose the service-role key in client code, reports, audit JSON, or logs.

Generate a report:

```bash
python scanner.py
```

If OpenBB feeds are not configured yet, explicitly run the crypto-only path:

```bash
python scanner.py --skip-openbb
```

The Persian, Telegram-ready report is printed and written to `reports/latest.txt`; it uses clear section dividers, compact explanatory labels and a right-to-left-safe Telegram publishing layer.  a dated report and `reports/crypto-audit-<timestamp>.json` are also generated. `data/opportunities.sqlite3` is the local journal. These are runtime outputs and should not be committed as source. The SEC 13F watchlist workflow also writes Persian per-filer reports and a consolidated `summary.txt` alongside machine-readable JSON and the SQLite registry. The `telegram_publisher.py` entrypoint can deliver `reports/latest.txt` to a Telegram channel using the Bot API. It chunks long reports, disables link previews, retries rate limits and transient failures, and never prints credentials. Configure `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` as GitHub Actions secrets in the private `market-pulse` repository; add the bot as a channel administrator with permission to post. The scheduled workflow runs daily at 12:00 UTC and still supports manual dispatch. If both Telegram secrets are absent, delivery is explicitly skipped while scanning and Data Hub ingestion continue. When Data Hub credentials are configured, the scanner attempts authenticated ingestion and includes the publisher status and accepted count in the report. A successful local scan alone does not prove that Worker ingestion or readback succeeded.

The crypto audit records the runtime GRIOS Git commit under `source_revision.git_commit_sha`. Run the focused test suite with `python -m py_compile scanner.py` and `python -m pytest -q`.

## Scoring and journal

The prototype computes market-specific scores from only available fields. Crypto combines the observed 24h/7d/30d changes, their sign alignment, volume/market-cap turnover and FDV/market-cap. Listed equities and commodity ETF proxies use 20/50-period trend, 20-period momentum, realized volatility and, when present, relative volume. EIA price series use trend/momentum/volatility only. ECB reference rates and FRED macro series are displayed as context and excluded from directional rank.

When a required field is missing, it is omitted and coverage falls; no zero or neutral value is imputed. Old observations are suppressed by market-specific age settings. Each input snapshot is recorded once by asset key and provider observation date. When a later scan reaches 1/7/30/90/365 days, the journal stores an observed mark-to-market checkpoint. It is not an execution/backtest and excludes fees, slippage and intraperiod drawdown.

## SEC Company Facts fundamentals\n\n`sec_company_facts.py` reads the latest original 10-K or 10-Q accession for the configured issuer watchlist, then extracts selected US-GAAP facts only when their accession and report-end date match that filing. It preserves XBRL start/end periods and filing dates, publishes structured facts, and generates a Persian report. Year-to-date and annual amounts are not relabeled as standalone quarters; no TTM, consensus, forecast or valuation multiple is inferred. The initial watchlist is a configurable sample of seven large U.S. issuers, not a complete equity universe.\n\n## Forward performance tracking

The scanner persists `WATCH_ONLY` candidates and 1/7/30/90/365-day evaluations in the Supabase `grios_paper_ideas` and `grios_paper_evaluations` tables; SQLite remains a local fallback. Benchmark-relative returns use same-date reference marks only: BTC for crypto, SPY for U.S. equities/ETFs and DBC for commodity proxies. The DBC benchmark is reference-only and is not ranked as a candidate. Optional assumed round-trip costs are configured with `GRIOS_PAPER_COST_BPS_CRYPTO`, `GRIOS_PAPER_COST_BPS_EQUITY` and `GRIOS_PAPER_COST_BPS_COMMODITY`; until configured, net returns remain null rather than assuming zero costs. These are prospective paper marks, not executions or a historical backtest. Actual spread, slippage, fees, taxes, financing, market impact, delisted-universe controls and full point-in-time replay remain outside the current model.

## EIA weekly petroleum supply and disposition\n\n`eia_petroleum_stocks.py` retrieves nine official EIA Weekly Petroleum Status Report series: commercial crude, gasoline and distillate inventories; crude production, imports and exports; refinery crude inputs and utilization; and total petroleum product supplied. Each series preserves its own units, weekly observation date, source URL, week-over-week change and raw historical percentile. The report distinguishes stock levels, supply flows, refinery inputs, utilization and a demand proxy. EIA weekly production and export figures are estimates; raw percentiles are not seasonally adjusted. The source series do not provide market consensus, release-time metadata or causal price direction; these are never inferred.\n\n## Macro event calendar\n\n`fred_release_calendar.py` retrieves upcoming dates for the configured FRED release catalog (CPI, employment, GDP, PCE, retail sales, industrial production and PPI). It writes a machine-readable JSON calendar and a Persian Telegram-ready text report. The FRED release-date endpoint does not provide a reliable release time, market consensus, actual result or impact score; those fields remain null and are not inferred. FRED also notes that source-published release dates do not guarantee the data will be available on FRED/ALFRED at that exact time.\n\n## Next stages

1. Licensed spot/futures feeds for FX, gold and industrial metals plus independent cross-checks.
2. Verified SEC Company Facts/13F snapshots, licensed spot/futures feeds for underlying metals and FX, and deeper commodity forward-curve data.
3. Market-specific quality gates and explainable G-Score calibration using point-in-time historical data.
4. Evaluation of false positives, delisted assets, survivorship bias, look-ahead bias, fees and slippage.
5. Licensed market data, SEC/13F and issuer-valuation integrations, plus point-in-time calibration.\n6. Telegram publishing is implemented but requires the channel bot token and destination to be configured as repository secrets. Order execution stays out of scope.


## Editorial daily intelligence briefing

`market_news.py` collects current RSS headlines from official Federal Reserve, SEC, EIA and BIS feeds and established financial reporting feeds/indexes from Bloomberg (including crypto), Reuters (including digital assets), CNBC, Wall Street Journal, Financial Times, Associated Press, The Block and CoinDesk. It validates publication dates, deduplicates headlines, classifies market catalysts and records publisher, timestamp and source URL. A news outage is non-blocking and explicitly reduces the confidence/coverage of the briefing.

`cftc_context.py` reads the latest fresh Futures Only positioning already stored in `public.grios_market_observations` using the existing GitHub Actions `SUPABASE_SERVICE_ROLE_KEY`. It validates asset keys, report age and participant categories. The report compares Asset Managers and Leveraged Funds for equity/FX futures and Managed Money/Producer-Merchant positioning for commodities. Raw contract counts, percentiles and price calculations remain internal; the Telegram output describes the positioning in plain Persian.

`daily_narrative_report.py` is the editorial layer. It publishes a concise symbol-and-direction radar plus separate market-specific news sections for FX, commodities/energy, US equities, crypto and bonds/rates. News coverage includes relevant political, economic, monetary, geopolitical, regulatory and company catalysts, attributed and linked to their sources. The Telegram signal list intentionally shows only each symbol and directional bias; it does not include per-symbol entry, invalidation, stop, target or timeframe cards. If evidence is missing or contradictory, the report says so rather than inventing a cause or signal.

The report is evidence-led but deterministic: it uses curated news headlines/RSS summaries and rule-based Persian analysis, not full-text review of every linked article or a generative language model. News publishers' full articles remain linked as sources for readers. SEC 13F holdings are shown only after a verified snapshot is available; 13F remains a delayed and partial disclosure, not real-time institutional flow.
