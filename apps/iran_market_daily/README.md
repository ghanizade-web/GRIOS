# Daily Iran Equity Watchlist

Private research-only pilot using the documented FundAI API. Iranian shares remain separate from GRIOS's global trade universe. The report aims to return up to three daily candidates from a broad-market screen; it never fabricates names to guarantee a count and does not place orders or issue personalized buy instructions.

## Setup

1. Copy `.env.example` to `.env` and set `FUNDAI_API_KEY` locally. Never commit `.env` or paste the key into chat.
2. The scan screens for positive latest-session individual net money flow, then validates up to three distinct, non-halted symbols using 30 adjusted daily sessions. It is not a whole-market technical ranking: only the screener's first 20 results are considered, and score/freshness gates can leave fewer than three.
3. The expected ceiling is 58 credits per Tehran trading day: 25 for a 20-result screener page, 18 for three adjusted 30-session histories and 15 for one market-flow row. Set `FUNDAI_MAX_DAILY_CREDITS` explicitly. If the cap is lower, no paid call is made. The local Tehran-date state file blocks duplicate paid scans; Thursday and Friday skip API calls.
4. Run `python3 scanner.py` from this folder.

The script checks `/me/`, refuses Sandbox data, preserves source/update/session dates and Rial units, and fails closed on stale, halted, malformed or unavailable data. Current implementation changes have not yet been live-tested against the screener endpoint, so it must not claim that broad-market ingestion is operational until a successful run verifies the response and credit charge. The technical score is experimental, has no backtest or full fundamental/Codal join, and is a research watchlist only. The provider's commercial-use exception does not explicitly include the screener; do not publish screener-derived recommendations to monetized channels without written permission.

## Daily Codex report

The existing Codex automation is intended to run at 09:00 Asia/Tehran in this conversation. It should report up to three qualified candidates after evidence checks; if fewer pass, it should say how many passed instead of padding the list. It does not publish to Telegram, Instagram, X, LinkedIn, Medium or Substack. API keys, local environment files and the daily idempotency state are excluded from Git.
