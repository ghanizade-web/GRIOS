# Daily Iran Equity Watchlist

Local research-only pilot using the documented FundAI API. It keeps Iranian shares separate from GRIOS's global trade universe. The output is a technical watchlist, not a validated investment signal or personal buy/sell instruction.

## Setup

1. Copy `.env.example` to `.env` and set `FUNDAI_API_KEY` locally. Never commit `.env` or paste the key into chat.
2. Add symbols/slugs to `IRAN_EQUITY_SYMBOLS`. This is a watchlist, not whole-market coverage.
3. Set `FUNDAI_MAX_DAILY_CREDITS` explicitly. With 60 adjusted sessions, FundAI documents 12 credits per symbol plus 15 credits for the market flow call. Ten symbols therefore estimate to 135 credits per run. The scanner sends no paid requests when the configured ceiling is lower.
4. Run `python3 scanner.py` from this folder.

The script checks `/me/`, refuses sample Sandbox data, retains dates/units and provider update times, excludes stale/halted/malformed symbols, and fails closed. FundAI's public OpenAPI docs identify the endpoint cost and commercial-use exception for daily prices, flows and technicals. Confirm permission for publishing derived analysis through monetized channels before public release. This pilot does not fetch Codal fundamentals or authorize social posting.

## Daily Codex report

The Codex automation runs at 09:00 Asia/Tehran in this conversation. Until credentials and a symbol watchlist are configured and a live run is validated, it must report missing access rather than produce stock picks. It does not publish to social accounts.
