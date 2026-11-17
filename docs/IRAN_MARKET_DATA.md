# Iran Market Data Operating Addendum

Reviewed 2026-11-17 against the user-supplied iran-mcp v2.3 archive and current provider API documentation. This is source research, not proof of a live connection.

## Sources and practical fit

| Source | Coverage | Access and limits | Use |
| --- | --- | --- | --- |
| [FundAI API](https://fundai.ir/developers) | TSETMC company list, daily prices, technical series, indices, breadth, market flows, trading status, book, trades, Codal statements and monthly sales. | Bearer API key; credit billing; docs list 100 trial credits with a verified account. OpenAPI documents Rial units, ISO and Jalali dates, per-response meta.updated_at, and endpoint costs. Daily prices, technicals, index history, market flows, trading state, depth/history and trades are marked commercially usable without contract. Other datasets are noncommercial absent written approval. | Best documented candidate for a scheduled scan. Before public dissemination, confirm with FundAI in writing whether attribution, transformations, excerpts and derived public research are allowed for each endpoint used. Never store the key in Git or a client. |
| [Tindex API](https://tindex.app/en/developers/) | Equities, indicators, currency rates, news, inflation and macro data. | Token required; free tier documented at 3 requests/minute and 300/day. The developer docs reviewed here do not establish rights to redistribute raw or derived data. | Useful low-volume alternative or cross-check after written permission and live validation. |
| [TSETMC API](https://cdn.tsetmc.com/api) | Broad exchange-native quotes, history, order books, indices and individual/legal statistics. | Reverse-engineered endpoints, no stable public API contract or redistribution entitlement verified; sources report non-Iran IP blocking. | Potential fallback/validation source if operated from a permitted Iranian host. Not a public feed until written permission, stability and access are established. |
| [Codal](https://www.codal.ir/) | Official issuer statements, monthly reports, material events and filings. | Public portal; no documented public API confirmed in this review. codal-mcp is an unofficial stdio wrapper around undocumented site endpoints and may need Iranian network access. | Primary-source fundamentals and catalysts. Link the original filing and publication date; use a licensed data provider for automated parsing where required. |
| iran-mcp v2.3 | MCP wrappers for TSETMC, Codal, FIPIRAN, Fara Bourse, CBI, IME, TGJU and other Iranian services. | Mostly unofficial Python stdio packages over undocumented site APIs; some require Iranian IP/proxy. The supplied archive is a catalog, not implementation or proof of connectivity. No dedicated NIMA source was found. | Analyst-assisted access, not a deployed GRIOS ingestion service or redistribution license. |

FundAI documentation says the API's commercial-use exception covers only listed market datasets; it does not automatically settle rights for a monetized public channel, attribution, or publication of derived recommendations. Confirm intended use with the provider. No account, key or live API call has been configured in GRIOS as of this review.

## Data and daily report rules

- Keep Iranian listed shares in a distinct Iran-market section; do not add conventional equities to the global trade universe.
- Preserve ticker, provider company slug, TSETMC id/ISIN when supplied, board, trading state, original Rial units, session date in Gregorian and Jalali where available, provider meta.updated_at, and retrieval time.
- Use adjusted daily prices for long-history return calculations; retain unadjusted traded prices separately. Do not mistake market close for a live quote.
- Market breadth and individual/legal flows are observed aggregate context, not proof of insider or institutional intent. A price-only snapshot is not a candidate thesis.
- For every candidate include source timestamp, history window, liquidity context, relevant Codal filing dates, counter-evidence, risks, and an invalidation condition. Exclude halted, stale, future-dated, malformed or unmapped records. If data are insufficient, report no qualified opportunity.
- Daily reports may suggest research candidates and scenarios, not personalized buy/sell instructions or guaranteed returns.
- Public social publication to Telegram, Instagram, X, LinkedIn, Medium or Substack requires provider permission that clearly covers redistribution/display and derived analysis. Until confirmed, keep reports private or link to original sources without republishing licensed feed data.
- Keep CBI official FX, explicitly identified transactional/NIMA rates, and TGJU free-market rates as different series. Never infer one from another.

## Automation and status

A daily 09:00 Asia/Tehran report automation is configured in Codex for this conversation. It checks whether evidence is available and returns no signal when source connection or freshness gates fail. It is a report in this chat; it does not post to social platforms.

Live Iranian equity ingestion is not yet operational: the GRIOS runtime has no FundAI token or tested API adapter, and public redistribution rights are not fully verified. Do not describe ingestion as live until real responses pass schema, freshness, units, symbol-mapping and failure-behavior checks.
