from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Any


FEED_DEFINITIONS = {
    "crypto_spot": {
        "asset_class": "crypto",
        "symbols_key": "crypto_symbols",
        "expected": None,
        "max_age_minutes": 30,
    },
    "us_equities_etfs": {
        "asset_class": "us_equity_etf",
        "symbols_key": "us_equities_etfs",
        "expected": None,
        "max_age_minutes": 4 * 24 * 60,
    },
    "commodity_etf_proxies": {
        "asset_class": "commodity_proxy",
        "symbols_key": "commodity_etf_proxies",
        "expected": None,
        "max_age_minutes": 4 * 24 * 60,
    },
    "fx_reference": {
        "asset_class": "fx_reference",
        "symbols_key": "fx_reference_pairs",
        "expected": None,
        "max_age_minutes": 4 * 24 * 60,
    },
    "eia_energy_spot": {
        "asset_class": "commodity_energy",
        "symbols_key": None,
        "expected": ["BRENT_SPOT", "HENRY_HUB_SPOT"],
        "max_age_minutes": 14 * 24 * 60,
    },
    "fred_macro": {
        "asset_class": "macro",
        "symbols_key": None,
        "expected": ["DGS10", "DGS2", "DTWEXBGS", "VIXCLS"],
        "max_age_minutes": 10 * 24 * 60,
    },
}

UNIMPLEMENTED_CAPABILITIES = [
    "underlying_gold_and_silver_spot_or_futures",
    "underlying_industrial_and_critical_metals_prices",
    "crypto_ohlcv_history_beyond_provider_snapshot",
    "order_book_spread_and_market_depth",
    "verified_institutional_fund_flows",
    "dated_catalyst_and_event_feed",
    "point_in_time_walk_forward_score_calibration",
]


def _field(item: Any, name: str, default: Any = None) -> Any:
    if isinstance(item, dict):
        return item.get(name, default)
    return getattr(item, name, default)


def _fresh(item: Any, max_age_minutes: int, now: datetime) -> bool | None:
    raw = _field(item, "observed_at")
    if not raw:
        return None
    try:
        stamp = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        if stamp.tzinfo is None:
            return None
        age = now - stamp.astimezone(timezone.utc)
        return timedelta(0) <= age <= timedelta(minutes=max_age_minutes)
    except (TypeError, ValueError):
        return None


def build_data_coverage_report(
    watchlist: dict[str, Any],
    series: list[Any],
    errors: list[str] | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    errors = errors or []
    feeds: dict[str, Any] = {}

    for feed_name, definition in FEED_DEFINITIONS.items():
        asset_class = definition["asset_class"]
        received_rows = [item for item in series if _field(item, "asset_class") == asset_class]
        received_symbols = sorted({str(_field(item, "symbol", "")).upper() for item in received_rows if _field(item, "symbol")})
        if definition["symbols_key"]:
            requested = sorted({str(value).strip().upper() for value in watchlist.get(definition["symbols_key"], []) if str(value).strip()})
        else:
            requested = list(definition["expected"] or [])
        discovery = feed_name == "crypto_spot" and str(watchlist.get("crypto_universe", {}).get("mode", "watchlist")).lower() == "discovery"

        if discovery:
            missing = []
            coverage_pct = None
            status = "DISCOVERY_MODE"
        else:
            missing = sorted(set(requested) - set(received_symbols))
            coverage_pct = round((len(set(requested) & set(received_symbols)) / len(requested)) * 100, 1) if requested else None
            status = "NOT_REQUESTED" if not requested else ("COMPLETE" if not missing else ("NONE" if not received_symbols else "PARTIAL"))

        fresh_symbols = []
        stale_symbols = []
        unknown_freshness = []
        for item in received_rows:
            symbol = str(_field(item, "symbol", "")).upper()
            fresh = _fresh(item, definition["max_age_minutes"], now)
            if fresh is True:
                fresh_symbols.append(symbol)
            elif fresh is False:
                stale_symbols.append(symbol)
            else:
                unknown_freshness.append(symbol)

        if stale_symbols and status in {"COMPLETE", "PARTIAL"}:
            status = "PARTIAL_STALE" if missing else "STALE"
        relevant_errors = [
            error for error in errors
            if (
                (feed_name.startswith("crypto") and any(token in error.lower() for token in ("crypto", "coingecko", "coinmarketcap")))
                or (feed_name.startswith("us_equities") and "equity" in error.lower())
                or (feed_name.startswith("commodity_etf") and "proxy" in error.lower())
                or (feed_name == "fx_reference" and "ecb" in error.lower())
                or (feed_name == "eia_energy_spot" and "eia" in error.lower())
                or (feed_name == "fred_macro" and "fred" in error.lower())
            )
        ]
        feeds[feed_name] = {
            "status": status,
            "requested_count": len(requested) if not discovery else None,
            "received_count": len(received_symbols),
            "coverage_pct": coverage_pct,
            "requested_symbols": requested if not discovery else [],
            "received_symbols": received_symbols,
            "missing_symbols": missing,
            "fresh_symbols": sorted(set(fresh_symbols)),
            "stale_symbols": sorted(set(stale_symbols)),
            "unknown_freshness_symbols": sorted(set(unknown_freshness)),
            "max_age_minutes": definition["max_age_minutes"],
            "errors": relevant_errors,
        }

    return {
        "schema_version": "1.0",
        "generated_at": now.astimezone(timezone.utc).isoformat(),
        "overall_status": (
            "DEGRADED" if any(item["status"] in {"NONE", "PARTIAL", "PARTIAL_STALE", "STALE"} for item in feeds.values())
            else "DISCOVERY" if any(item["status"] == "DISCOVERY_MODE" for item in feeds.values())
            else "COVERED"
        ),
        "feeds": feeds,
        "capabilities_not_implemented": UNIMPLEMENTED_CAPABILITIES,
        "error_count": len(errors),
    }


def serialize_market_series(item: Any) -> dict[str, Any]:
    return {
        "asset_key": str(_field(item, "key", "")),
        "symbol": str(_field(item, "symbol", "")),
        "name": str(_field(item, "name", "")),
        "asset_class": str(_field(item, "asset_class", "")),
        "instrument": str(_field(item, "instrument", "")),
        "provider": str(_field(item, "provider", "")),
        "feed_class": str(_field(item, "feed_class", "")),
        "currency": str(_field(item, "currency", "")),
        "observed_at": _field(item, "observed_at"),
        "data_as_of": _field(item, "data_as_of"),
        "caveat": _field(item, "caveat"),
        "observations": _field(item, "observations", []) or [],
        "extra": _field(item, "extra", {}) or {},
    }


def publish_market_series(
    series: list[Any],
    source_revision: str = "UNKNOWN",
    timeout: int = 20,
) -> dict[str, Any]:
    endpoint = os.getenv("GRIOS_DATA_HUB_URL", "").strip().rstrip("/")
    token = os.getenv("GRIOS_DATA_HUB_TOKEN", "").strip()
    if not endpoint or not token:
        return {"status": "NOT_CONFIGURED", "accepted": 0, "error": None}
    if not endpoint.startswith("https://"):
        return {"status": "CONFIG_ERROR", "accepted": 0, "error": "INVALID_ENDPOINT"}
    rows = [serialize_market_series(item) for item in series]
    if not rows:
        return {"status": "NO_DATA", "accepted": 0, "error": None}

    accepted = 0
    try:
        for offset in range(0, len(rows), 500):
            payload = {
                "schema_version": "1.0",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "source_revision": source_revision,
                "observations": rows[offset:offset + 500],
            }
            request = urllib.request.Request(
                endpoint + "/v1/ingest",
                data=json.dumps(payload, ensure_ascii=False, allow_nan=False).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                method="POST",
            )
            with urllib.request.urlopen(request, timeout=timeout) as response:
                result = json.loads(response.read().decode("utf-8"))
                if response.status not in (200, 202) or result.get("status") != "accepted":
                    return {"status": "REJECTED", "accepted": accepted, "error": "UNEXPECTED_RESPONSE"}
                accepted += int(result.get("accepted", 0))
        return {"status": "CONNECTED", "accepted": accepted, "error": None}
    except urllib.error.HTTPError as exc:
        # Keep diagnostics safe: never log request headers, response bodies, or credentials.
        detail = f"HTTP_{exc.code}"
        headers = exc.headers or {}
        server = str(headers.get("server", "")).lower()
        content_type = str(headers.get("content-type", "")).lower()
        mitigation = str(headers.get("cf-mitigated", "")).lower()
        if "challenge" in mitigation:
            detail += ":CF_CHALLENGE"
        elif "cloudflare" in server and "text/html" in content_type:
            detail += ":CF_EDGE_HTML"
        elif "cloudflare" in server:
            detail += ":CF_EDGE"
        else:
            try:
                body = json.loads(exc.read().decode("utf-8"))
                worker_code = body.get("error") if isinstance(body, dict) else None
                if isinstance(worker_code, str) and worker_code.replace("_", "").isalnum():
                    detail += f":{worker_code[:80]}"
            except (UnicodeDecodeError, ValueError, TypeError):
                pass
        return {"status": "FAILED", "accepted": accepted, "error": detail}
    except Exception as exc:
        return {"status": "FAILED", "accepted": accepted, "error": type(exc).__name__}
