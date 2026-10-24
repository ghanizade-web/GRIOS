# GRIOS Command Menu

The terminal command center is available at `/menu`. Enter a slash command in
its command field or select one of the menu cards. Every response must show
data freshness and source coverage where market data is involved.

## Routed commands

| Command | Current behavior | Data / limitation |
| --- | --- | --- |
| `/menu` | Opens the command center and lists commands. | Static menu; no market request. |
| `/start` | Shows Worker and provider health. | Requires deployed `/v1/status`. |
| `/` | Opens the market overview. | Existing overview page. |
| `/alpha` | Opens the crypto alpha scanner. | Existing scanner; coverage follows its connected provider and stored universe. |
| `/ai` | Opens the CIO evidence brief. | Existing deterministic brief; no live LLM council. |
| `/journal` | Opens the signal journal. | Requires deployed Worker and applied journal migration. |
| `/report today\|week\|month\|year\|long` | Calls `/v1/opportunities` for the requested horizon. | Year/long return `insufficient_history` until required data exists. |
| `/trades SYMBOL [horizon]` | Calls `/v1/intelligence` filtered to a symbol. | Evidence research only. No entry, stop, target or order execution is invented. |
| `/pumpfinder [universe]` | Runs an availability gate and explains missing evidence. | No confirmed derivatives/spot-flow ingestion; does not infer institutional accumulation. |
| `/portfolio` | Explains portfolio connection state. | No private account/portfolio is connected; no holdings are displayed. |
| `/flows [symbol]` | Explains flow-source availability. | No attributable ETF/exchange/on-chain flow feed is connected. |
| `/macro [region]` | Explains macro-source availability. | No dated official macro series is integrated into the Worker. |

The command center does not fabricate an opportunity when the Worker, fresh
observations, or history is unavailable. `/pumpfinder`, `/portfolio`, `/flows`,
and `/macro` are routed but remain data-gated; their messages are explicit
availability results, not completed market-analysis modules. The Codex MCP
market connectors can support research in chat, but they do not automatically
become data sources inside the deployed web terminal.

## Horizon support

| Horizon | API status |
| --- | --- |
| `today` / `day` | Maps to the available 24-hour return window. |
| `week` | Maps to the available 7-day return window. |
| `month` | Maps to the available 30-day return window. |
| `year` | `insufficient_history` until 90/365-day history and required context are present. |
| `long` | `insufficient_history` until multi-year history and fundamental/catalyst evidence are present. |

Research responses are not personalized investment advice and never execute
orders. A missing or stale observation suppresses rankings; it is not treated
as evidence for or against an asset.
