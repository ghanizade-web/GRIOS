# GRIOS Opportunity Scanner — MVP

Small, research-only Python scanner using OpenBB Python V5 connectors plus the existing GRIOS crypto Data Hub. It writes a Persian, Telegram-friendly text report and records snapshots/idea outcomes in local SQLite. It does not send Telegram messages, place orders, or claim validated alpha.

## Actual MVP coverage

- **Crypto spot:** reads the existing GRIOS `/v1/markets/latest` snapshot. Requires a configured Data Hub URL and observations within the configured freshness limit. Provider timestamps and missing fields are retained. OpenBB V5's maintained provider list does not include CoinGecko/CMC spot connectors.
- **US shares/ETFs:** OpenBB V5 Cboe daily history for a user-edited watchlist. It is a research history feed, not an executable quote. The provider's coverage and terms control actual freshness.
- **Commodity proxies:** the same Cboe equity connector can be used for listed ETF proxies such as GLD/SLV/USO/UNG/CPER. These are not underlying spot prices or futures; roll/tracking/issuer risks remain.
- **Oil and gas:** OpenBB EIA series for Brent spot and Henry Hub spot. They are published data, not a real-time futures feed. The MVP does not rank them as complete supply/demand theses because inventory, forward curve and dated catalysts are not joined to the price score.
- **Forex:** ECB reference-rate histories for EUR pairs only. They are not bid/ask quotes and do not support Buy/Sell rankings.
- **Macro context:** FRED daily observations for US 2Y/10Y yields, broad dollar index and VIX close. Each value keeps its observation date; this is context, not an automatic risk-on/off decision.
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

Edit `.env` and `watchlist.json`. `GRIOS_DATA_HUB_URL` is the deployed Worker base URL (for example `https://your-worker.example`); do not enter the API key in the URL. Set `EIA_API_KEY` for EIA and `FRED_API_KEY` for macro series. Both keys are free to request from their agencies. The script loads these secrets from local `.env`; `.env` is gitignored.

Generate a report:

```bash
python scanner.py
```

If OpenBB feeds are not configured yet, explicitly run the crypto-only path:

```bash
python scanner.py --skip-openbb
```

The report is printed and written to `reports/latest.txt`; dated reports and `data/opportunities.sqlite3` are local, ignored runtime files. Copy the text into Telegram manually. No bot token is required.

## Scoring and journal

The prototype computes market-specific scores from only available fields. Crypto combines the observed 24h/7d/30d changes, their sign alignment, volume/market-cap turnover and FDV/market-cap. Listed equities and commodity ETF proxies use 20/50-period trend, 20-period momentum, realized volatility and, when present, relative volume. EIA price series use trend/momentum/volatility only. ECB reference rates and FRED macro series are displayed as context and excluded from directional rank.

When a required field is missing, it is omitted and coverage falls; no zero or neutral value is imputed. Old observations are suppressed by market-specific age settings. Each input snapshot is recorded once by asset key and provider observation date. When a later scan reaches 1/7/30/90/365 days, the journal stores an observed mark-to-market checkpoint. It is not an execution/backtest and excludes fees, slippage and intraperiod drawdown.

## Next stages

1. Licensed spot/futures feeds for FX, gold and industrial metals plus independent cross-checks.
2. Dated issuer/commodity catalysts, SEC/company fundamentals, EIA stocks and CFTC positioning.
3. Market-specific quality gates and explainable G-Score calibration using point-in-time historical data.
4. Evaluation of false positives, delisted assets, survivorship bias, look-ahead bias, fees and slippage.
5. Only after credentials, licensing and delivery are configured: optional Telegram bot publishing. Order execution stays out of scope.
