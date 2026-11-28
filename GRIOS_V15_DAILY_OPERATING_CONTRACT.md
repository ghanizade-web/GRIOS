# GRIOS v15 — Daily Operating Contract
**Status:** Canonical single-report operational standard  
**Effective:** 2026-11-28  
**Mission:** We Track Capital Before The Crowd.

This contract supersedes every conflicting historical daily-report instruction in this repository, including the former dual-output design, separate capital-flow/megatrend report, RSS-only news digest, and legacy one-line Telegram recap.

## 1. Sole daily deliverable

Exactly ONE report may be generated and published each day:

**گزارش فرصت‌های معاملاتی — Daily Trading Opportunities**

The canonical detailed prompt is [GRIOS_DAILY_REPORT_MASTER_PROMPT_FA.md](GRIOS_DAILY_REPORT_MASTER_PROMPT_FA.md). It is the sole editorial source of truth for the daily report.

Prohibited as separate outputs or Telegram posts:
- Daily Megatrends & Smart Money
- Strategic Capital Flows / capital-flows report
- Separate institutional-flow or strategic-materials report
- RSS-only headline digest
- One-line daily market recap
- Any reproduction or republishing of the previously rejected report

Do not merge, summarize, or replace the requested trading report with a different report type. A JSON audit file is machine-readable evidence, not a second report.

## 2. Required coverage and structure

The report is Persian-first, target 1,000–1,400 words, and must cover all seven markets in this exact order:
1. Forex
2. Crypto
3. Gold & Silver
4. Oil
5. US Stocks
6. Tehran Stocks
7. Iran Free Market

Required sections:
- Current date: weekday, Jalali and Gregorian, Asia/Tehran.
- Macro picture, 4–6 bullets.
- Catalyst calendar for today, next 7 days and material month-end events.
- For each of the seven markets: 2–4 sourced data points, causal mechanism, bullish/bearish triggers, invalidations, one focus asset or no-entry decision, confidence 1–5.
- Focus table covering all seven markets.
- Exactly three risk/correlation bullets.
- Changes vs yesterday only when yesterday’s actual report is available.
- Friday scorecard only when prior daily reports and observed prices are available.
- Source names, clickable URLs beside material claims, and the financial-risk disclaimer.
- Telegram mode: plain text, emoji-led headings, no Markdown tables, caption or TRACK block; append the approved social footer in the publisher and remove STATE_DIGEST before sending.

Market-specific rules for DXY and major pairs, BTC/ETH and ETF flows, gold/silver, Brent/WTI and OPEC, US indices/VIX/futures, Tehran breadth and retail flows, and Iran free-market USD/Emami coin/18k gold are defined in the canonical prompt.

## 3. Research and evidence gates

- 14–16 distinct targeted web searches per report.
- Current facts normally no older than 24 hours; up to 72 hours only for weekly/monthly context.
- Preserve observation time, publication time and timezone.
- Prefer primary sources, exchanges, central banks, official statistics, TSETMC, Fipiran, Rahavard365, TGJU, SEC filings, ETF issuers and established financial newswires.
- Open source pages when snippets do not contain material figures; cross-check material claims where feasible.
- Show ranges and flag conflicts. Do not silently average sources.
- Missing data must be written «داده در دسترس نبود».
- Never invent prices, flows, symbols, levels, probabilities, consensus, event times or technical levels.
- Tehran symbols may be named only when same-day evidence confirms positive real-money inflow into that exact symbol.
- A closed market must be identified as closed and the latest session date stated.
- Distinguish verified fact, reported claim, market expectation, interpretation and scenario.

## 4. Automated implementation

The private repository [ghanizade-web/market-pulse](https://github.com/ghanizade-web/market-pulse) owns the daily generation and Telegram publication workflow.

- Generator: scripts/build_daily_trading_report.py
- Prompt: GRIOS_DAILY_REPORT_MASTER_PROMPT_FA.md
- Publisher: GRIOS repository telegram_publisher.py
- Sole report: reports/trading-opportunities-latest.txt
- Audit: reports/trading-opportunities-audit.json
- Dated archive and Telegram delivery audit: reports/daily-market/

The generator uses the OpenAI Responses API hosted web_search tool, with model gpt-5.6 by default and high reasoning/search context. It records actual search queries, citations, response ID, report hash, word count and STATE_DIGEST.

The workflow must fail closed unless the required search count, date/title, seven market sections, source URL minimum, word-count guardrail and digest checks pass. No Telegram send occurs after a failed research or quality gate.

## 5. Schedule and secrets

- Daily schedule: 05:30 UTC = 09:00 Asia/Tehran.
- Report date is calculated in Asia/Tehran.
- Scheduled run: research → validate → archive one report → publish that same report → record Telegram message IDs and delivery state.
- Manual workflow dispatch publishes only when publish_to_telegram=true.
- Push/PR runs run tests only and never publish.
- Required GitHub Actions secrets in the private market-pulse repository: OPENAI_API_KEY and TELEGRAM_BOT_TOKEN.
- TELEGRAM_CHAT_ID is optional while the configured fallback channel ID remains valid. Never expose secrets in source, logs, reports or commits.

## 6. Delivery audit and acceptance

The report is operational only when a controlled GitHub Actions run proves:
1. 14–16 distinct searches were executed.
2. The Persian report passes all required content and evidence gates.
3. Exactly one report is archived.
4. Telegram returns a message_id for every chunk.
5. The delivery audit records PUBLISHED.
6. A subsequent scheduled run follows the same single-report path.

Telegram chunks are parts of the same report, not multiple reports. A green workflow badge alone is not proof of publication.

**Risk statement:** Scenarios are research, not personalized financial advice.