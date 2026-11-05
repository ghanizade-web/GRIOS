# GRIOS Opportunity Scanner — MVP

Small, research-only Python scanner using direct CoinGecko and CoinMarketCap REST adapters for crypto, plus OpenBB provider connectors for listed equities/ETFs, ECB FX reference data, EIA energy series, and FRED macro context. It writes a Persian, Telegram-friendly text report, a machine-readable crypto audit JSON, and local SQLite snapshots/idea outcomes. An optional authenticated publisher sends normalized observations to the GRIOS Cloudflare Data Hub when `GRIOS_DATA_HUB_URL` and `GRIOS_DATA_HUB_TOKEN` are configured; without both values, scanning continues locally and publishing reports `NOT_CONFIGURED`. A separate `market-pulse` repository also contains a Twelve Data adapter and a manual scanner-to-Data-Hub workflow; that adapter is a distinct feed and should not be confused with this scanner's CoinGecko/CMC/OpenBB/ECB/EIA/FRED coverage. The scanner itself does not place orders and does not claim validated alpha.

## Actual MVP coverage

- **Crypto spot:** queries CoinGecko markets (up to 250 rows) and CoinMarketCap quotes (up to 500 rows) directly, using `COINGECKO_API_KEY` and `COINMARKETCAP_API_KEY`. Requested symbols are checked against provider responses; provider timestamps, missing symbols, invalid/stale observations, duplicate ticker ambiguity, identity-name mismatch, and cross-source price deviations are recorded in `crypto-audit-<timestamp>.json`. The 2% cross-source price-deviation threshold is a data-quality gate, not a trading rule. The current adapters request the top market-cap pages only; they do not yet make per-symbol fallback requests for missing assets.
- **US shares/ETFs:** OpenBB V5 Cboe daily history for a user-edited watchlist. It is a research history feed, not an executable quote. The provider's coverage and terms control actual freshness.
- **Commodity proxies:** the same Cboe equity connector can be used for listed ETF proxies such as GLD/SLV/USO/UNG/CPER. These are not underlying spot prices or futures; roll/tracking/issuer risks remain.
- **Oil and gas:** OpenBB EIA series for Brent spot and Henry Hub spot. They are published data, not a real-time futures feed. The MVP does not rank them as complete supply/demand theses because inventory, forward curve and dated catalysts are not joined to the price score.
- **Forex:** ECB reference-rate histories for EUR pairs only. They are not bid/ask quotes and do not support Buy/Sell rankings.
- **Macro context:** FRED daily observations for US 2Y/10Y yields, broad dollar index and VIX close. Each value keeps its observation date; this is context, not an automatic risk-on/off decision.
- **CFTC positioning (separate weekly feed):** the CFTC Legacy Futures Only adapter retrieves configured contract markets and preserves the Tuesday report date, commercial/non-commercial long and short positions, net exposure, weekly change, open interest, historical percentile and z-score. It is a weekly exposure disclosure, not transaction-level flow or a real-time institutional signal. The first implementation does not yet cover Disaggregated or TFF classifications, options-combined positions, or dealer gamma.
- **Gold, silver and industrial metal outright prices:** not covered as underlying contracts in this MVP. Add an exchange-licensed source before ranking these markets.

Scores are **technical watch scores**, not G-Scores, expected returns, or trade signals. Current weights are visible in `market_score()`: crypto momentum 40%, multi-window alignment 30%, volume/market-cap turnover 20%, FDV/market-cap 10%; equities trend 35%, momentum 25%, volatility 20%, relative volume 20%; energy series trend 40%, momentum 35%, volatility 25%. Weights renormalize over available factors and the report shows factor coverage. If same-name crypto feeds disagree on price by more than 2%, that asset is suppressed; this threshold is a data-quality guard, not a calibrated market rule. A catalyst/news feed, verified institutional flow, fundamentals for issuers/protocols, risk-reward model and external calibration are absent. Therefore the CIO line is deliberately `WATCH` only.

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

Edit `.env` and `watchlist.json`. Set `COINGECKO_API_KEY` and `COINMARKETCAP_API_KEY` for the direct crypto adapters, `EIA_API_KEY` for EIA, and `FRED_API_KEY` for macro series. Keep all credentials in `.env` or the CI secret store; never place them in URLs, source files, audit JSON, or logs. The script loads local environment variables via `python-dotenv`; `.env` is gitignored. In GitHub Actions, the GRIOS scanner workflow supplies provider credentials as repository secrets. For optional Data Hub publishing, set `GRIOS_DATA_HUB_URL` to the deployed Worker HTTPS origin and `GRIOS_DATA_HUB_TOKEN` to the same bearer token configured on the Worker. Never place secret values in source, reports, audit JSON, or logs.

Generate a report:

```bash
python scanner.py
```

If OpenBB feeds are not configured yet, explicitly run the crypto-only path:

```bash
python scanner.py --skip-openbb
```

The report is printed and written to `reports/latest.txt`; a dated report and `reports/crypto-audit-<timestamp>.json` are also generated. `data/opportunities.sqlite3` is the local journal. These are runtime outputs and should not be committed as source. The `telegram_publisher.py` entrypoint can deliver `reports/latest.txt` to a Telegram channel using the Bot API. It chunks long reports, disables link previews, retries rate limits and transient failures, and never prints credentials. Configure `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` as GitHub Actions secrets in the private `market-pulse` repository; add the bot as a channel administrator with permission to post. The scheduled workflow runs daily at 12:00 UTC and still supports manual dispatch. If both Telegram secrets are absent, delivery is explicitly skipped while scanning and Data Hub ingestion continue. When Data Hub credentials are configured, the scanner attempts authenticated ingestion and includes the publisher status and accepted count in the report. A successful local scan alone does not prove that Worker ingestion or readback succeeded.

The crypto audit records the runtime GRIOS Git commit under `source_revision.git_commit_sha`. Run the focused test suite with `python -m py_compile scanner.py` and `python -m pytest -q`.

## Scoring and journal

The prototype computes market-specific scores from only available fields. Crypto combines the observed 24h/7d/30d changes, their sign alignment, volume/market-cap turnover and FDV/market-cap. Listed equities and commodity ETF proxies use 20/50-period trend, 20-period momentum, realized volatility and, when present, relative volume. EIA price series use trend/momentum/volatility only. ECB reference rates and FRED macro series are displayed as context and excluded from directional rank.

When a required field is missing, it is omitted and coverage falls; no zero or neutral value is imputed. Old observations are suppressed by market-specific age settings. Each input snapshot is recorded once by asset key and provider observation date. When a later scan reaches 1/7/30/90/365 days, the journal stores an observed mark-to-market checkpoint. It is not an execution/backtest and excludes fees, slippage and intraperiod drawdown.

## Next stages

1. Licensed spot/futures feeds for FX, gold and industrial metals plus independent cross-checks.
2. Dated issuer/commodity catalysts, SEC/company fundamentals, EIA stocks and CFTC positioning.
3. Market-specific quality gates and explainable G-Score calibration using point-in-time historical data.
4. Evaluation of false positives, delisted assets, survivorship bias, look-ahead bias, fees and slippage.
5. Licensed market data, dated catalysts, SEC/13F and CFTC positioning integrations, plus point-in-time calibration.\n6. Telegram publishing is implemented but requires the channel bot token and destination to be configured as repository secrets. Order execution stays out of scope.
