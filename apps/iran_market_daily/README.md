# Daily Iran Equity Watchlist

Local research-only pilot using the documented FundAI API. It keeps Iranian shares separate from GRIOS's global trade universe. The output is a technical watchlist, not a validated investment signal or personal buy/sell instruction.

## Setup

1. Copy `.env.example` to `.env` and set `FUNDAI_API_KEY` locally. Never commit `.env` or paste the key into chat.
2. Add symbols/slugs to `IRAN_EQUITY_SYMBOLS`. This is a watchlist, not whole-market coverage.
3. The pilot uses three representative symbols and 30 adjusted sessions. FundAI documents 6 credits per symbol plus 15 credits for market flow: 33 credits per run. The local cap is set to 33, and a Tehran-date state file prevents a second paid scan on the same day. Thursday and Friday skip the data calls because the exchange is closed.
4. Run `python3 scanner.py` from this folder.

The script checks `/me/`, refuses sample Sandbox data, retains dates/units and provider update times, excludes stale/halted/malformed symbols, and fails closed. It only emits a technical watchlist; it does not claim fundamental validation or an actionable buy/sell signal. FundAI's public OpenAPI docs identify endpoint costs and commercial-use exceptions for daily prices, flows and technicals. Confirm permission for publishing derived analysis through monetized channels before public release. This pilot does not fetch Codal fundamentals or authorize social posting.

## Daily Codex report

The Codex automation runs at 09:00 Asia/Tehran in this conversation. Local settings currently use a 33-credit ceiling per Tehran trading day for فولاد, فملی and شپنا. It reports no candidates when history is stale, halted, malformed or below the experimental score threshold. It does not publish to social accounts. API keys, local environment files and the daily idempotency state file are excluded from Git.
