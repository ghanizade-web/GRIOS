> **Current architecture decision — 2026-11-07:** Supabase is the sole GRIOS Data Hub and persistent backend. Cloudflare Worker/Wrangler is deprecated and is not part of the active pipeline. Python collectors publish directly to Supabase PostgREST using server-side `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`. GitHub Actions remains the scheduled compute/orchestration layer; the existing daily schedule is unchanged. See [GRIOS_SUPABASE_ONLY_ARCHITECTURE.md](GRIOS_SUPABASE_ONLY_ARCHITECTURE.md) for the current verified state.

# GRIOS v15 — API Source Registry & Integration Health

**Project:** Ghanizadeh Research Intelligence Operating System  
**Version:** 15.0 Institutional Edition  
**Module:** Data Sources, API Registry & Health Monitoring  
**Status:** Core Operational Specification  
**Mission:** We Track Capital Before The Crowd.

---

## 1. Purpose

This document establishes the central registry for all external data providers, APIs, internal data services, and automated data connectors used by GRIOS v15.

The registry must answer:

- Which APIs are connected?
- What data does each source provide?
- Which GRIOS module consumes the data?
- How frequently is the data updated?
- Is the source currently operational?
- When was the last successful retrieval?
- Is the returned data valid and sufficiently fresh?
- What happens when the source becomes unavailable?

The objective is to establish traceability and operational visibility across the entire GRIOS data infrastructure.

## 2. System Architecture

```text
External Data Providers
          |
          v
API Connectors & Adapters
          |
          v
Market-Pulse Data Collection
          |
          v
GRIOS Data Ingestion
          |
          v
Validation & Normalization
          |
          v
Internal Data Registry
          |
          v
GRIOS Intelligence Modules
          |
          v
Reports, Watchlists & Signals
```

This is the logical integration architecture. Each connection must have its own operational health status.

## 3. Source Registry Structure

Every API or data connector must have a unique registry entry.

Required fields:

| Field | Description |
|---|---|
| source_id | Unique source identifier |
| provider | API provider or internal service |
| source_name | Human-readable source name |
| category | Data classification |
| endpoint_reference | Secure reference to endpoint configuration |
| authentication_type | Authentication method |
| data_products | Data types provided |
| consumer_modules | GRIOS modules using the source |
| expected_frequency | Expected update interval |
| last_success_at | Last successful retrieval |
| last_failure_at | Last recorded failure |
| health_status | Current operational status |
| freshness_status | Data freshness classification |
| validation_status | Data quality result |
| rate_limit | Provider request limitations |
| criticality | Operational importance |
| fallback_source | Alternative source, if available |
| owner | Responsible system component |

Secrets, API keys, access tokens, and passwords must never be stored in this public registry.

## 4. Source Categories

### 4.1 Market Data

- Equities
- Indices
- Foreign exchange
- Commodities
- Bonds
- Futures
- Market volume
- Volatility
- Historical prices

### 4.2 Macroeconomic Data

- Inflation
- Employment
- GDP
- Interest rates
- Treasury yields
- Central-bank balance sheets
- Monetary liquidity
- Economic indicators

### 4.3 Crypto Data

- Cryptocurrency prices
- Market capitalization
- Trading volume
- Exchange flows
- ETF flows
- Network activity
- Derivatives data

### 4.4 Energy and Commodities

- Crude oil
- Natural gas
- Refined products
- Electricity
- Uranium
- Copper
- Lithium
- Precious metals
- Strategic minerals

### 4.5 Corporate and Institutional Intelligence

- SEC filings
- Corporate financial statements
- Earnings
- Insider transactions
- Institutional ownership
- M&A
- Capital expenditure
- Procurement
- Strategic supply agreements

### 4.6 Geopolitical and News Intelligence

- Government announcements
- Sanctions
- Trade restrictions
- Elections
- Military and geopolitical developments
- Industrial policy
- Strategic infrastructure decisions

### 4.7 Internal GRIOS Services

- Market-Pulse repository
- Internal market scanner
- Data normalization services
- Supabase database
- Cloudflare Workers
- Internal reporting services

Only services that actually exist in the deployed architecture should be marked as active.

## 5. Known System Components

The following repositories are part of the GRIOS project architecture:

### GRIOS Repository

Repository:

`ghanizade-web/GRIOS`

Primary responsibility:

- Intelligence processing
- Analytical framework
- Signal generation
- Opportunity ranking
- Strategic reporting

### Market-Pulse Repository

Repository:

`ghanizade-web/market-pulse`

Primary responsibility:

- Market-data collection
- Scanner execution
- API data retrieval
- Market-pulse reporting
- Scheduled data workflows

### Operational Assumption

The project operator has confirmed that APIs in both repositories are connected and provide live data.

This confirmation is an operational input, not an independent technical audit.

The registry must therefore distinguish between:

- OPERATOR_CONFIRMED
- CONNECTION_TESTED
- DATA_RETRIEVAL_VERIFIED
- DATA_VALIDATED
- PRODUCTION_MONITORED

These statuses must not be treated as equivalent.

## 6. API Health Status

Each source must have a health status.

| Status | Meaning |
|---|---|
| OPERATIONAL | Recent requests succeed and required checks pass |
| DEGRADED | Requests work but performance or data quality is impaired |
| DELAYED | Data is older than expected |
| FAILING | Repeated requests fail |
| UNAVAILABLE | No usable connection |
| UNKNOWN | No recent health observation |
| MAINTENANCE | Intentionally disabled |

A successful HTTP response does not automatically mean that the data is valid.

The system must separately evaluate response success, schema validity, data completeness, and freshness.

## 7. Data Freshness Registry

Freshness thresholds must be configured individually.

Illustrative defaults:

| Data Type | Expected Monitoring |
|---|---|
| Intraday market quotes | Seconds to minutes |
| FX and commodity prices | Minutes |
| Crypto prices | Seconds to minutes |
| ETF flows | Provider publication schedule |
| Treasury yields | Provider publication schedule |
| Economic releases | Official release schedule |
| Corporate filings | Event-driven |
| Institutional ownership | Regulatory reporting schedule |
| Strategic supply contracts | Event-driven |

These are monitoring categories, not universal guarantees of provider update frequency.

The actual threshold must be defined using provider documentation and the relevant data product.

## 8. API Monitoring Metrics

The monitoring service should collect:

### Availability
- Successful request count
- Failed request count
- Availability percentage
- Consecutive failures

### Performance
- Response latency
- Average response time
- P95 latency
- Timeout frequency

### Data Quality
- Missing values
- Duplicate records
- Invalid schemas
- Unexpected units
- Abnormal observations
- Timestamp inconsistencies

### Freshness
- Last successful retrieval
- Last source publication timestamp
- Data age
- Freshness threshold violations

### Provider Constraints
- Rate-limit status
- Quota consumption
- Authentication failures
- Subscription restrictions

## 9. Security Requirements

All API credentials must remain server-side.

Approved approaches include:

- Cloudflare Worker secret bindings
- Secure server-side environment variables
- Managed secret stores
- Restricted service credentials

Prohibited practices:

1. Committing API keys to GitHub.
2. Embedding secrets in frontend code.
3. Publishing credentials in reports.
4. Writing secret values into logs.
5. Sending credentials through public API responses.
6. Exposing private credentials in debugging output.

Public configuration files may contain variable names and secret references, but never secret values.

## 10. Failure Handling

When a source becomes unavailable:

1. Record the failure timestamp.
2. Capture a sanitized error category.
3. Preserve the last valid observation.
4. Mark the source as failing or unavailable.
5. Attempt a configured fallback source if appropriate.
6. Avoid substituting zero for missing data.
7. Prevent stale data from generating new actionable signals.
8. Notify the relevant monitoring component.
9. Record recovery after successful validation.

The system must not silently present cached data as live data.

## 11. Source Independence and Cross-Validation

GRIOS should compare important observations across independent providers.

Examples:

- DXY or FX observations across market-data providers.
- Oil prices across independent market-data sources.
- Treasury yields against official publications.
- Corporate transactions against regulatory filings.
- Institutional ownership against primary disclosures.

Multiple news outlets repeating the same original report do not constitute independent confirmation.

## 12. API Registry Record Template

Every source should follow a consistent structure.

```yaml
source_id: PROVIDER_PRODUCT_ID

provider: PROVIDER_NAME
source_name: DATA_PRODUCT_NAME
category: market_data

endpoint_reference: SECURE_CONFIG_REFERENCE
authentication_type: api_key

data_products:
  - price
  - volume

consumer_modules:
  - market_dashboard
  - signal_scoring_engine

expected_frequency: provider_defined

health_status: UNKNOWN
freshness_status: UNKNOWN
validation_status: PENDING

last_success_at: null
last_failure_at: null

criticality: HIGH
fallback_source: null

owner: market_pulse
```

This is a schema template, not a declaration that a particular provider or endpoint has been configured.

## 13. Recommended Registry Files

The following files may be added as the implementation evolves:

- `config/api_sources.yaml`
- `config/data_freshness.yaml`
- `config/source_fallbacks.yaml`
- `config/health_thresholds.yaml`
- `docs/API_INTEGRATION_MAP.md`

Actual configuration paths must be aligned with the existing repository structure before implementation.

## 14. Daily Operational Dashboard

The GRIOS operational dashboard should show:

| Metric | Required Information |
|---|---|
| Total Sources | Number of registered sources |
| Operational | Sources passing health checks |
| Degraded | Sources with partial impairment |
| Unavailable | Sources failing connectivity |
| Stale Data | Sources violating freshness thresholds |
| Validation Failures | Invalid or inconsistent observations |
| Last Successful Sync | Latest verified retrieval |
| Critical Dependencies | Sources whose failure affects core modules |

The dashboard must distinguish source availability from data quality.

## 15. Module Dependency Mapping

Each analytical module must declare its dependencies.

Examples:

### Macro Intelligence
- Economic data
- Treasury yields
- FX
- Central-bank data

### Smart Money Intelligence
- Regulatory filings
- Institutional ownership
- ETF flows
- Corporate disclosures

### Megatrend Intelligence
- Corporate CapEx
- Supply agreements
- Strategic mineral data
- Government industrial policy
- Technology investment disclosures

### Trading Signal Engine
- Live market prices
- Volume
- Technical indicators
- Volatility
- Liquidity
- Fundamental catalysts

### Crypto Intelligence
- Crypto market data
- Exchange data
- ETF flows
- Derivatives and network metrics

Dependency mapping must reflect actual implemented connections.

## 16. Governance and Change Management

Every source change must be documented.

Examples:

- New API integration
- Provider migration
- Authentication change
- Endpoint modification
- Schema change
- Rate-limit change
- Fallback replacement
- Source deprecation

Each change should record:

- Date
- Source identifier
- Change description
- Reason
- Affected modules
- Validation result
- Responsible component

## 17. Operational Success Criteria

The API registry is considered operationally mature when:

1. All production sources are registered.
2. All critical dependencies are mapped.
3. API health is measured automatically.
4. Data freshness is monitored.
5. Schema validation is implemented.
6. Failure handling is documented and tested.
7. Secrets are protected.
8. Fallback behavior is defined.
9. Data lineage is preserved.
10. Reports identify material data-quality limitations.

## 18. Core Rule

GRIOS must know not only what the market data says, but also where the data came from, when it was observed, whether it is reliable, and which analytical conclusions depend on it.

**GRIOS v15 — We Track Capital Before The Crowd.**
