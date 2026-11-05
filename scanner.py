from __future__ import annotations

import argparse
import json
import math
import os
import re
import sqlite3
import statistics
import time
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import httpx
from dotenv import load_dotenv

from data_coverage import build_data_coverage_report, publish_market_series
from report_formatting import social_footer_lines

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

CG_URL = "https://api.coingecko.com/api/v3/coins/markets"
CMC_URL = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest"

DEFAULT_CRYPTO_SYMBOLS = [
    "BTC", "ETH", "BNB", "SOL", "XRP", "DOGE", "ADA",
    "TRX", "LINK", "AVAX", "LTC", "BCH", "DOT", "GRAM",
]

CRYPTO_UNIVERSE_DEFAULTS = {
    "mode": "watchlist",
    "min_market_cap_usd": 250_000_000,
    "min_volume_24h_usd": 10_000_000,
    "min_turnover_ratio": 0.01,
    "max_fdv_market_cap_ratio": 3.0,
    "require_two_sources": False,
    "excluded_symbols": [
        "USDT", "USDC", "USDS", "DAI", "USDE",
        "FDUSD", "TUSD", "USDD", "PYUSD", "FRAX",
        "WBTC", "WETH", "STETH", "WSTETH",
    ],
    "excluded_name_terms": [
        "stablecoin", "wrapped", "bridged", "leveraged",
        "3x long", "3x short", "2x long", "2x short",
    ],
}


@dataclass
class MarketSeries:
    key: str
    symbol: str
    name: str
    asset_class: str
    instrument: str
    provider: str
    feed_class: str
    currency: str
    observations: list[dict[str, Any]] = field(default_factory=list)
    observed_at: str | None = None
    data_as_of: str | None = None
    caveat: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime | None = None) -> str:
    return (dt or now_utc()).isoformat(timespec="seconds")


def parse_timestamp(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return None
        return parsed.astimezone(timezone.utc)
    except (ValueError, TypeError):
        return None


def as_float(value: Any) -> float | None:
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except (TypeError, ValueError):
        return None


def as_date(value: Any) -> str | None:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()[:10]
    return str(value)[:10]


def load_watchlist(path: Path) -> dict[str, Any]:
    keys = (
        "us_equities_etfs",
        "commodity_etf_proxies",
        "fx_reference_pairs",
        "crypto_symbols",
    )

    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("Watchlist root must be a JSON object.")
    else:
        data = {}

    result: dict[str, Any] = {
        key: [
            str(v).strip().upper()
            for v in data.get(key, [])
            if str(v).strip()
        ]
        for key in keys
    }

    # TON was the legacy ticker for the same native asset now named GRAM.
    # Normalize old watchlists at the boundary and keep one canonical symbol.
    result["crypto_symbols"] = list(dict.fromkeys(
        "GRAM" if symbol == "TON" else symbol
        for symbol in result["crypto_symbols"]
    ))

    config = data.get("crypto_universe", {})
    if not isinstance(config, dict):
        raise ValueError("crypto_universe must be a JSON object.")

    universe = {**CRYPTO_UNIVERSE_DEFAULTS, **config}

    mode = str(universe.get("mode", "watchlist")).lower()
    if mode not in {"watchlist", "discovery"}:
        raise ValueError("crypto_universe.mode must be watchlist or discovery.")

    universe["mode"] = mode

    for key in (
        "min_market_cap_usd",
        "min_volume_24h_usd",
        "min_turnover_ratio",
        "max_fdv_market_cap_ratio",
    ):
        value = as_float(universe.get(key))
        if value is None or value < 0:
            raise ValueError(f"Invalid crypto_universe setting: {key}")
        universe[key] = value

    universe["require_two_sources"] = bool(
        universe.get("require_two_sources", False)
    )

    universe["excluded_symbols"] = [
        str(x).strip().upper()
        for x in universe.get("excluded_symbols", [])
        if str(x).strip()
    ]

    universe["excluded_name_terms"] = [
        str(x).strip().casefold()
        for x in universe.get("excluded_name_terms", [])
        if str(x).strip()
    ]

    # An empty Watchlist must never mean "scan everything".
    if mode == "watchlist" and not result["crypto_symbols"]:
        result["crypto_symbols"] = DEFAULT_CRYPTO_SYMBOLS.copy()

    result["crypto_universe"] = universe
    return result


def get_openbb() -> Any:
    from openbb import obb

    eia_key = os.getenv("EIA_API_KEY", "").strip()
    fred_key = os.getenv("FRED_API_KEY", "").strip()

    if eia_key:
        obb.user.credentials.eia_api_key = eia_key
    if fred_key:
        obb.user.credentials.fred_api_key = fred_key

    return obb


def dataframe_rows(result: Any) -> list[dict[str, Any]]:
    frame = result.to_dataframe()
    if frame is None or frame.empty:
        return []
    frame = frame.reset_index()
    return frame.where(frame.notna(), None).to_dict(orient="records")


def normalized_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.casefold())


def valid_crypto_row(
    symbol: str,
    name: str,
    price: Any,
    stamp: Any,
    max_age_minutes: int,
) -> tuple[float, datetime] | None:
    parsed_price = as_float(price)
    parsed_stamp = parse_timestamp(stamp)

    if (
        not symbol or not name or parsed_price is None
        or parsed_price <= 0 or parsed_stamp is None
    ):
        return None

    age = now_utc() - parsed_stamp
    if age < timedelta(0) or age > timedelta(minutes=max_age_minutes):
        return None

    return parsed_price, parsed_stamp


def crypto_series(
    *,
    symbol: str,
    name: str,
    provider: str,
    stamp: datetime,
    price: float,
    market_cap: Any,
    volume: Any,
    fdv: Any,
    change_24h: Any,
    change_7d: Any,
    change_30d: Any,
    slug: str = "",
) -> MarketSeries:
    identity = slug.strip().lower() or normalized_name(name)

    return MarketSeries(
        key=f"crypto:asset:{symbol.upper()}:{identity}",
        symbol=symbol.upper(),
        name=name,
        asset_class="crypto",
        instrument="spot token",
        provider=provider,
        feed_class="Aggregated crypto spot; provider timestamp checked",
        currency="USD",
        observations=[{"date": stamp.date().isoformat(), "close": price}],
        observed_at=stamp.isoformat(timespec="seconds"),
        data_as_of=stamp.date().isoformat(),
        caveat=(
            "Spot snapshot only; no historical OHLCV, order-book spread, "
            "verified institutional flow or catalyst feed."
        ),
        extra={
            "market_cap": as_float(market_cap),
            "volume_24h": as_float(volume),
            "fdv": as_float(fdv),
            "change_24h": as_float(change_24h),
            "change_7d": as_float(change_7d),
            "change_30d": as_float(change_30d),
            "slug": slug,
        },
    )



def fetch_coingecko(
    api_key: str,
    symbols: list[str],
    max_age_minutes: int,
    audit: dict[str, Any] | None = None,
) -> tuple[list[MarketSeries], str | None]:
    if not api_key:
        if audit is not None:
            audit.update({"provider": "CoinGecko", "status": "MISSING_API_KEY"})
        return [], "COINGECKO_API_KEY تنظیم نشده است."

    params = {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": 250,
        "page": 1,
        "sparkline": "false",
        "price_change_percentage": "24h,7d,30d",
    }
    try:
        response = httpx.get(
            CG_URL,
            params=params,
            headers={"x-cg-demo-api-key": api_key},
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, list):
            if audit is not None:
                audit.update({"provider": "CoinGecko", "status": "INVALID_RESPONSE"})
            return [], "CoinGecko پاسخ با ساختار مورد انتظار برنگرداند."
        provider_audit, valid = audit_crypto_provider(
            "CoinGecko", payload, symbols, max_age_minutes
        )
        rows = [
            crypto_series(
                symbol=item["symbol"],
                name=item["name"],
                provider="CoinGecko",
                stamp=stamp,
                price=price,
                market_cap=item["market_cap"],
                volume=item["volume"],
                fdv=item["fdv"],
                change_24h=item["change_24h"],
                change_7d=item["change_7d"],
                change_30d=item["change_30d"],
                slug=item["slug"],
            )
            for item, price, stamp in valid.values()
        ]
        if audit is not None:
            audit.update(provider_audit)
        return rows, None if rows else "CoinGecko داده معتبر و تازه‌ای برای Watchlist برنگرداند."
    except (httpx.HTTPError, ValueError, TypeError) as exc:
        if audit is not None:
            audit.update({
                "provider": "CoinGecko",
                "status": "PROVIDER_ERROR",
                "error_type": type(exc).__name__,
            })
        return [], "اتصال CoinGecko ناموفق بود؛ جزئیات محرمانه در گزارش ثبت نشد."


def fetch_coinmarketcap(
    api_key: str,
    symbols: list[str],
    max_age_minutes: int,
    audit: dict[str, Any] | None = None,
) -> tuple[list[MarketSeries], str | None]:
    if not api_key:
        if audit is not None:
            audit.update({"provider": "CoinMarketCap", "status": "MISSING_API_KEY"})
        return [], "COINMARKETCAP_API_KEY تنظیم نشده است."

    params = {"start": 1, "limit": 500, "convert": "USD"}
    try:
        response = httpx.get(
            CMC_URL,
            params=params,
            headers={
                "X-CMC_PRO_API_KEY": api_key,
                "Accept": "application/json",
            },
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            if audit is not None:
                audit.update({"provider": "CoinMarketCap", "status": "INVALID_RESPONSE"})
            return [], "CoinMarketCap پاسخ با ساختار مورد انتظار برنگرداند."
        status = payload.get("status")
        if isinstance(status, dict) and status.get("error_code") not in (None, 0):
            if audit is not None:
                audit.update({
                    "provider": "CoinMarketCap",
                    "status": "PROVIDER_ERROR",
                    "provider_error_code": status.get("error_code"),
                })
            return [], "CoinMarketCap درخواست را با خطا رد کرد."
        items = payload.get("data", [])
        if not isinstance(items, list):
            if audit is not None:
                audit.update({"provider": "CoinMarketCap", "status": "INVALID_RESPONSE"})
            return [], "CoinMarketCap پاسخ با ساختار مورد انتظار برنگرداند."
        provider_audit, valid = audit_crypto_provider(
            "CoinMarketCap", items, symbols, max_age_minutes
        )
        rows = [
            crypto_series(
                symbol=item["symbol"],
                name=item["name"],
                provider="CoinMarketCap",
                stamp=stamp,
                price=price,
                market_cap=item["market_cap"],
                volume=item["volume"],
                fdv=item["fdv"],
                change_24h=item["change_24h"],
                change_7d=item["change_7d"],
                change_30d=item["change_30d"],
                slug=item["slug"],
            )
            for item, price, stamp in valid.values()
        ]
        if audit is not None:
            audit.update(provider_audit)
        return rows, None if rows else "CoinMarketCap داده معتبر و تازه‌ای برای Watchlist برنگرداند."
    except (httpx.HTTPError, ValueError, TypeError) as exc:
        if audit is not None:
            audit.update({
                "provider": "CoinMarketCap",
                "status": "PROVIDER_ERROR",
                "error_type": type(exc).__name__,
            })
        return [], "اتصال CoinMarketCap ناموفق بود؛ جزئیات محرمانه در گزارش ثبت نشد."



GRAM_PROVIDER_IDS = {
    "CoinGecko": "the-open-network",
    "CoinMarketCap": "11419",
}
CMC_QUOTES_URL = "https://pro-api.coinmarketcap.com/v2/cryptocurrency/quotes/latest"


def fetch_gram_by_provider_id(
    provider: str,
    api_key: str,
    max_age_minutes: int,
    audit: dict[str, Any] | None = None,
) -> tuple[list[MarketSeries], str | None]:
    """Fetch GRAM by immutable provider asset ID; never resolve by ticker alone."""
    if not api_key:
        if audit is not None:
            audit.update({"provider": provider, "status": "MISSING_API_KEY", "fallback": True})
        return [], f"{provider} GRAM fallback skipped: API key is missing."

    try:
        if provider == "CoinGecko":
            response = httpx.get(
                CG_URL,
                params={
                    "vs_currency": "usd",
                    "ids": GRAM_PROVIDER_IDS[provider],
                    "sparkline": "false",
                    "price_change_percentage": "24h,7d,30d",
                },
                headers={"x-cg-demo-api-key": api_key},
                timeout=30,
            )
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, list):
                raise ValueError("INVALID_RESPONSE")
            records = payload
            identity_evidence = [
                {
                    "provider_asset_id": str(item.get("id") or ""),
                    "symbol": str(item.get("symbol") or ""),
                    "name": str(item.get("name") or ""),
                    "checks": {
                        "asset_id_matches": str(item.get("id") or "").lower() == GRAM_PROVIDER_IDS[provider],
                        "symbol_matches": str(item.get("symbol") or "").upper() == "GRAM",
                        "name_matches": normalized_name(str(item.get("name") or "")) in {"gram", "gramprevtoncoin"},
                    },
                }
                for item in records if isinstance(item, dict)
            ]
            identity_ok = bool(identity_evidence) and all(
                all(item["checks"].values()) for item in identity_evidence
            )
        elif provider == "CoinMarketCap":
            response = httpx.get(
                CMC_QUOTES_URL,
                params={"id": GRAM_PROVIDER_IDS[provider], "convert": "USD"},
                headers={
                    "X-CMC_PRO_API_KEY": api_key,
                    "Accept": "application/json",
                },
                timeout=30,
            )
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict):
                raise ValueError("INVALID_RESPONSE")
            data = payload.get("data", {})
            if isinstance(data, dict):
                records = [data[GRAM_PROVIDER_IDS[provider]]] if GRAM_PROVIDER_IDS[provider] in data else []
            elif isinstance(data, list):
                records = data
            else:
                raise ValueError("INVALID_RESPONSE")
            identity_evidence = [
                {
                    "provider_asset_id": str(item.get("id") or ""),
                    "slug": str(item.get("slug") or ""),
                    "symbol": str(item.get("symbol") or ""),
                    "name": str(item.get("name") or ""),
                    "checks": {
                        "asset_id_matches": str(item.get("id")) == GRAM_PROVIDER_IDS[provider],
                        "slug_matches": str(item.get("slug") or "").lower() in {"gram", "gramprevtoncoin"},
                        "symbol_matches": str(item.get("symbol") or "").upper() == "GRAM",
                        "name_matches": normalized_name(str(item.get("name") or "")) in {"gram", "gramprevtoncoin"},
                    },
                }
                for item in records if isinstance(item, dict)
            ]
            identity_ok = bool(identity_evidence) and all(
                all(item["checks"].values()) for item in identity_evidence
            )
        else:
            raise ValueError("UNSUPPORTED_PROVIDER")

        if not records:
            if audit is not None:
                audit.update({
                    "provider": provider,
                    "status": "NOT_RETURNED",
                    "fallback": True,
                    "provider_asset_id": GRAM_PROVIDER_IDS[provider],
                    "symbols": {"GRAM": {"status": "NOT_RETURNED"}},
                })
            return [], f"{provider} GRAM fallback returned no asset."

        if not all(isinstance(item, dict) for item in records):
            raise ValueError("INVALID_RESPONSE")
        if not identity_ok:
            if audit is not None:
                audit.update({
                    "provider": provider,
                    "status": "IDENTITY_MISMATCH",
                    "fallback": True,
                    "provider_asset_id": GRAM_PROVIDER_IDS[provider],
                    "identity_evidence": identity_evidence,
                    "symbols": {"GRAM": {"status": "IDENTITY_MISMATCH"}},
                })
            return [], f"{provider} GRAM fallback failed strict asset identity validation."

        normalized, valid = audit_crypto_provider(
            provider, records, ["GRAM"], max_age_minutes
        )
        if audit is not None:
            audit.update(normalized)
            audit["fallback"] = True
            audit["provider_asset_id"] = GRAM_PROVIDER_IDS[provider]
            audit["endpoint_mode"] = "provider_asset_id"
        if "GRAM" not in valid:
            return [], f"{provider} GRAM fallback did not produce a fresh valid quote."

        item, price, stamp = valid["GRAM"]
        row = crypto_series(
            symbol="GRAM",
            name=item["name"],
            provider=provider,
            stamp=stamp,
            price=price,
            market_cap=item["market_cap"],
            volume=item["volume"],
            fdv=item["fdv"],
            change_24h=item["change_24h"],
            change_7d=item["change_7d"],
            change_30d=item["change_30d"],
            slug=item["slug"] or GRAM_PROVIDER_IDS[provider],
        )
        return [row], None
    except (httpx.HTTPError, ValueError, TypeError, KeyError) as exc:
        if audit is not None:
            audit.update({
                "provider": provider,
                "status": "PROVIDER_ERROR" if not isinstance(exc, ValueError) or str(exc) != "INVALID_RESPONSE" else "INVALID_RESPONSE",
                "error_type": type(exc).__name__,
                "fallback": True,
                "provider_asset_id": GRAM_PROVIDER_IDS.get(provider),
            })
        return [], f"{provider} GRAM fallback failed ({type(exc).__name__})."

def save_crypto_audit(
    audit: dict[str, Any],
    output_dir: Path,
    timestamp: str,
    source_commit_sha: str,
    mode: str,
    max_age_minutes: int,
) -> Path:
    document = {
        "schema_version": "1.0",
        "engine": "GRIOS Crypto Universe Audit",
        "source_revision": {"repository_file": "scanner.py", "git_commit_sha": source_commit_sha},
        "generated_at": iso(),
        "run": {
            "timestamp": timestamp,
            "mode": mode,
            "max_age_minutes": max_age_minutes,
        },
        "audit": audit,
    }
    target = output_dir / f"crypto-audit-{timestamp}.json"
    temporary = target.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(document, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(target)
    return target



def audit_crypto_provider(
    provider: str,
    raw_items: list[Any],
    symbols: list[str],
    max_age_minutes: int,
    error_type: str | None = None,
) -> tuple[dict[str, Any], dict[str, tuple[dict[str, Any], float, datetime]]]:
    """Validate provider rows and retain only sanitized audit metadata."""
    requested = {str(x).strip().upper() for x in symbols if str(x).strip()}
    audit: dict[str, Any] = {
        "provider": provider,
        "requested_symbols": sorted(requested),
        "requested_count": len(requested),
        "returned_rows": len(raw_items),
        "status": "OK",
        "symbols": {},
    }
    valid: dict[str, tuple[dict[str, Any], float, datetime]] = {}
    grouped: dict[str, list[dict[str, Any]]] = {}

    if error_type:
        audit.update({"status": "PROVIDER_ERROR", "error_type": error_type})
        return audit, valid

    for item in raw_items:
        if not isinstance(item, dict):
            audit["invalid_rows"] = audit.get("invalid_rows", 0) + 1
            continue
        symbol = str(item.get("symbol") or "").strip().upper()
        if not symbol or (requested and symbol not in requested):
            continue
        grouped.setdefault(symbol, []).append(item)

    all_symbols = sorted(set(grouped) | requested)
    now = now_utc()

    for symbol in all_symbols:
        records = grouped.get(symbol, [])
        if not records:
            audit["symbols"][symbol] = {"status": "NOT_RETURNED"}
            continue
        if len(records) != 1:
            audit["symbols"][symbol] = {
                "status": "AMBIGUOUS_SYMBOL",
                "record_count": len(records),
                "reason": "Multiple provider records share the requested symbol.",
            }
            continue

        item = records[0]
        name = str(item.get("name") or "").strip()
        if provider == "CoinGecko":
            price_raw = item.get("current_price")
            stamp_raw = item.get("last_updated")
            market_cap = item.get("market_cap")
            volume = item.get("total_volume")
            fdv = item.get("fully_diluted_valuation")
            change_24h = item.get("price_change_percentage_24h")
            change_7d = item.get("price_change_percentage_7d_in_currency")
            change_30d = item.get("price_change_percentage_30d_in_currency")
            asset_id = str(item.get("id") or "")
        else:
            quote = item.get("quote")
            if isinstance(quote, list):
                quote = quote[0] if quote else {}
            if not isinstance(quote, dict):
                quote = {}
            usd = quote.get("USD")
            if isinstance(usd, list):
                usd = usd[0] if usd else {}
            if not isinstance(usd, dict):
                usd = {}
            price_raw = usd.get("price")
            stamp_raw = usd.get("last_updated") or item.get("last_updated")
            market_cap = usd.get("market_cap")
            volume = usd.get("volume_24h")
            fdv = usd.get("fully_diluted_market_cap")
            change_24h = usd.get("percent_change_24h")
            change_7d = usd.get("percent_change_7d")
            change_30d = usd.get("percent_change_30d")
            asset_id = str(item.get("slug") or "")

        if symbol == "GRAM":
            if provider == "CoinGecko":
                identity_checks = {
                    "asset_id_matches": str(item.get("id") or "").lower() == GRAM_PROVIDER_IDS["CoinGecko"],
                    "symbol_matches": symbol == "GRAM",
                    "name_matches": normalized_name(name) in {"gram", "gramprevtoncoin"},
                }
            elif provider == "CoinMarketCap":
                identity_checks = {
                    "asset_id_matches": str(item.get("id") or "") == GRAM_PROVIDER_IDS["CoinMarketCap"],
                    "slug_matches": str(item.get("slug") or "").lower() in {"gram", "gramprevtoncoin"},
                    "symbol_matches": symbol == "GRAM",
                    "name_matches": normalized_name(name) in {"gram", "gramprevtoncoin"},
                }
            else:
                identity_checks = {"supported_provider": False}
            if not all(identity_checks.values()):
                audit["symbols"][symbol] = {
                    "status": "IDENTITY_MISMATCH",
                    "provider_identity_checks": identity_checks,
                }
                continue

        if not name:
            audit["symbols"][symbol] = {"status": "INVALID_NAME"}
            continue
        price = as_float(price_raw)
        if price is None or price <= 0:
            audit["symbols"][symbol] = {"status": "INVALID_PRICE"}
            continue
        stamp = parse_timestamp(stamp_raw)
        if stamp is None:
            audit["symbols"][symbol] = {"status": "INVALID_TIMESTAMP"}
            continue
        age = now - stamp
        if age < timedelta(0):
            audit["symbols"][symbol] = {"status": "FUTURE_TIMESTAMP"}
            continue
        if age > timedelta(minutes=max_age_minutes):
            audit["symbols"][symbol] = {"status": "STALE"}
            continue

        audit["symbols"][symbol] = {
            "status": "VALID",
            "name": name,
            "provider_asset_id": asset_id,
            "observed_at": stamp.isoformat(timespec="seconds"),
        }
        valid[symbol] = ({
            "symbol": symbol,
            "name": name,
            "provider": provider,
            "stamp": stamp,
            "price": price,
            "market_cap": market_cap,
            "volume": volume,
            "fdv": fdv,
            "change_24h": change_24h,
            "change_7d": change_7d,
            "change_30d": change_30d,
            "slug": asset_id,
        }, price, stamp)

    if any(v["status"] == "AMBIGUOUS_SYMBOL" for v in audit["symbols"].values()):
        audit["status"] = "AMBIGUOUS_SYMBOLS_PRESENT"
    elif not valid:
        audit["status"] = "NO_VALID_ROWS"
    audit["valid_count"] = len(valid)
    return audit, valid


def reconcile_crypto(
    rows: list[MarketSeries],
    audit: dict[str, Any] | None = None,
) -> tuple[list[MarketSeries], list[str]]:
    """Reconcile by ticker, explicitly blocking identity and source conflicts."""
    grouped: dict[str, list[MarketSeries]] = {}
    for row in rows:
        grouped.setdefault(row.symbol.strip().upper(), []).append(row)

    accepted: list[MarketSeries] = []
    conflicts: list[str] = []
    outcomes: dict[str, dict[str, Any]] = {}

    for symbol, group in sorted(grouped.items()):
        names = {normalized_name(item.name) for item in group}
        providers: dict[str, list[MarketSeries]] = {}
        for item in group:
            providers.setdefault(item.provider.strip(), []).append(item)

        if len(names) != 1 or "" in names:
            outcomes[symbol] = {"status": "IDENTITY_MISMATCH"}
            conflicts.append(f"{symbol}: هویت نام دارایی بین منابع سازگار نبود؛ حذف شد.")
            continue

        if any(len(items) > 1 for items in providers.values()):
            outcomes[symbol] = {"status": "AMBIGUOUS_SYMBOL"}
            conflicts.append(f"{symbol}: نماد تکراری در یک یا چند منبع؛ حذف شد.")
            continue

        prices = [price_now(item) for item in group]
        if any(price is None or price <= 0 for price in prices):
            outcomes[symbol] = {"status": "INVALID_PRICE"}
            conflicts.append(f"{symbol}: قیمت نامعتبر در تطبیق منابع؛ حذف شد.")
            continue

        deviation = 0.0
        if len(group) >= 2:
            median = statistics.median(prices)
            deviation = ((max(prices) - min(prices)) / median * 100) if median else 999.0
            if deviation > 2.0:
                outcomes[symbol] = {
                    "status": "SOURCE_CONFLICT",
                    "price_deviation_pct": round(deviation, 4),
                }
                conflicts.append(f"{symbol}: اختلاف قیمت منابع {deviation:.2f}% بود؛ حذف شد.")
                continue

        chosen = max(
            group,
            key=lambda item: parse_timestamp(item.observed_at) or datetime.min.replace(tzinfo=timezone.utc),
        )
        provider_names = sorted(providers)
        chosen.key = f"crypto:asset:{symbol}:{next(iter(names))}"
        chosen.provider = " + ".join(provider_names)
        chosen.extra["provider_count"] = len(provider_names)
        chosen.extra["identity_status"] = "UNCONFIRMED_NAME_MATCH"
        chosen.extra["source_price_deviation_pct"] = round(deviation, 4)
        chosen.extra["universe_status"] = "CROSS_SOURCE" if len(provider_names) >= 2 else "SINGLE_SOURCE"
        outcomes[symbol] = {
            "status": "ACCEPTED_CROSS_SOURCE" if len(provider_names) >= 2 else "ACCEPTED_SINGLE_SOURCE",
            "providers": provider_names,
            "price_deviation_pct": round(deviation, 4),
            "identity_status": "UNCONFIRMED_NAME_MATCH",
        }
        accepted.append(chosen)

    if audit is not None:
        audit["reconciliation"] = outcomes
        audit["reconciliation_summary"] = {
            "input_rows": len(rows),
            "accepted_rows": len(accepted),
            "rejected_symbols": len(outcomes) - len(accepted),
        }
    return accepted, conflicts


def fetch_crypto(
    symbols: list[str],
    max_age_minutes: int,
    audit: dict[str, Any] | None = None,
) -> tuple[list[MarketSeries], list[str]]:
    provider_audits: dict[str, Any] = {}
    provider_rows: dict[str, list[MarketSeries]] = {}
    provider_errors: list[str] = []

    for provider, fetcher, env_key in (
        ("CoinGecko", fetch_coingecko, "COINGECKO_API_KEY"),
        ("CoinMarketCap", fetch_coinmarketcap, "COINMARKETCAP_API_KEY"),
    ):
        local_audit: dict[str, Any] = {}
        rows, error = fetcher(
            os.getenv(env_key, "").strip(),
            symbols,
            max_age_minutes,
            audit=local_audit,
        )
        provider_audits[provider] = local_audit
        provider_rows[provider] = rows
        if "GRAM" in {str(value).strip().upper() for value in symbols} and local_audit.get("symbols", {}).get("GRAM", {}).get("status") in {"NOT_RETURNED", "IDENTITY_MISMATCH"}:
            fallback_audit: dict[str, Any] = {}
            fallback_rows, fallback_error = fetch_gram_by_provider_id(
                provider,
                os.getenv(env_key, "").strip(),
                max_age_minutes,
                audit=fallback_audit,
            )
            provider_audits[provider]["gram_fallback"] = fallback_audit
            if fallback_rows:
                provider_rows[provider].extend(fallback_rows)
                provider_audits[provider].setdefault("symbols", {})["GRAM"] = fallback_audit.get("symbols", {}).get("GRAM", {"status": "VALID"})
            elif fallback_error:
                provider_errors.append(fallback_error)
                if fallback_audit.get("symbols", {}).get("GRAM", {}).get("status"):
                    provider_audits[provider].setdefault("symbols", {})["GRAM"] = fallback_audit["symbols"]["GRAM"]
        if error:
            provider_errors.append(error)

    blocked: set[str] = set()
    for provider_audit in provider_audits.values():
        for symbol, item in provider_audit.get("symbols", {}).items():
            if item.get("status") == "AMBIGUOUS_SYMBOL":
                blocked.add(symbol)

    combined_rows = [
        row
        for provider, rows in provider_rows.items()
        for row in rows
        if row.symbol.upper() not in blocked
    ]

    reconciliation_audit: dict[str, Any] = {}
    combined, conflicts = reconcile_crypto(combined_rows, audit=reconciliation_audit)
    errors = provider_errors + conflicts

    if audit is not None:
        audit.update({
            "providers": provider_audits,
            **reconciliation_audit,
            "summary": {
                "requested_symbols": len(symbols),
                "coingecko_valid_rows": len(provider_rows.get("CoinGecko", [])),
                "coinmarketcap_valid_rows": len(provider_rows.get("CoinMarketCap", [])),
                "ambiguous_symbols_blocked": sorted(blocked),
                "reconciled_rows": len(combined),
                "conflict_count": len(conflicts),
            },
        })

    if not combined and not errors:
        errors.append("هیچ داده معتبر کریپتو دریافت نشد.")
    return combined, errors


def filter_crypto_universe(
    rows: list[MarketSeries],
    config: dict[str, Any],
    audit: dict[str, Any] | None = None,
) -> tuple[list[MarketSeries], dict[str, Any]]:
    eligible: list[MarketSeries] = []
    excluded: dict[str, int] = {}
    asset_audit: dict[str, Any] = {}

    min_market_cap = config["min_market_cap_usd"]
    min_volume = config["min_volume_24h_usd"]
    min_turnover = config["min_turnover_ratio"]
    max_fdv_ratio = config["max_fdv_market_cap_ratio"]
    excluded_symbols = set(config["excluded_symbols"])
    excluded_terms = config["excluded_name_terms"]
    require_two_sources = config["require_two_sources"]

    def reject(reason: str) -> None:
        excluded[reason] = excluded.get(reason, 0) + 1

    for series in rows:
        extra = series.extra
        market_cap = as_float(extra.get("market_cap"))
        volume = as_float(extra.get("volume_24h"))
        fdv = as_float(extra.get("fdv"))
        reason: str | None = None

        if series.symbol.upper() in excluded_symbols:
            reason = "excluded_symbol"
        elif any(term in series.name.casefold() for term in excluded_terms):
            reason = "excluded_name_pattern"
        elif market_cap is None or market_cap <= 0:
            reason = "missing_market_cap"
        elif market_cap < min_market_cap:
            reason = "market_cap_below_minimum"
        elif volume is None or volume <= 0:
            reason = "missing_volume"
        elif volume < min_volume:
            reason = "volume_below_minimum"

        turnover = volume / market_cap if volume is not None and market_cap else None
        if reason is None and turnover is not None and turnover < min_turnover:
            reason = "turnover_below_minimum"

        fdv_ratio = fdv / market_cap if fdv is not None and fdv > 0 and market_cap else None
        if reason is None and fdv_ratio is not None and fdv_ratio > max_fdv_ratio:
            reason = "fdv_dilution_risk"

        providers = {part.strip() for part in series.provider.split("+") if part.strip()}
        provider_count = len(providers)
        if reason is None and require_two_sources and provider_count < 2:
            reason = "single_source"

        if reason:
            reject(reason)
            asset_audit[series.symbol] = {
                "accepted": False,
                "status": "REJECTED",
                "reason": reason,
                "market_cap_usd": market_cap,
                "volume_24h_usd": volume,
                "turnover_ratio": turnover,
                "fdv_market_cap_ratio": fdv_ratio,
                "provider_count": provider_count,
            }
            continue

        extra["provider_count"] = provider_count
        extra["volume_market_cap_ratio"] = turnover
        extra["fdv_market_cap_ratio"] = fdv_ratio
        extra["universe_status"] = "CROSS_SOURCE" if provider_count >= 2 else "SINGLE_SOURCE"
        asset_audit[series.symbol] = {
            "accepted": True,
            "status": "ELIGIBLE",
            "market_cap_usd": market_cap,
            "volume_24h_usd": volume,
            "turnover_ratio": turnover,
            "fdv_market_cap_ratio": fdv_ratio,
            "provider_count": provider_count,
        }
        eligible.append(series)

    stats = {
        "input_count": len(rows),
        "eligible_count": len(eligible),
        "excluded_count": len(rows) - len(eligible),
        "excluded_reasons": excluded,
    }
    if audit is not None:
        audit["universe_filter"] = {
            "rules": {
                "min_market_cap_usd": min_market_cap,
                "min_volume_24h_usd": min_volume,
                "min_turnover_ratio": min_turnover,
                "max_fdv_market_cap_ratio": max_fdv_ratio,
                "require_two_sources": require_two_sources,
                "excluded_symbols": sorted(excluded_symbols),
                "excluded_name_terms": list(excluded_terms),
            },
            "summary": stats,
            "assets": asset_audit,
        }
    return eligible, stats


def fetch_equity(
    obb: Any,
    symbols: list[str],
    proxy: bool = False,
) -> tuple[list[MarketSeries], list[str]]:
    result: list[MarketSeries] = []
    errors: list[str] = []

    start = (date.today() - timedelta(days=220)).isoformat()
    end = date.today().isoformat()

    for symbol in symbols:
        try:
            response = obb.cboe.equity.historical(
                symbol=symbol,
                start_date=start,
                end_date=end,
                provider="cboe",
            )

            points = []

            for row in dataframe_rows(response):
                stamp = as_date(row.get("date") or row.get("index"))
                close = as_float(row.get("close"))

                if stamp and close and close > 0:
                    points.append({
                        "date": stamp,
                        "close": close,
                        "volume": as_float(row.get("volume")),
                    })

            points.sort(key=lambda p: p["date"])

            if not points:
                errors.append(f"{symbol}: Cboe داده قابل استفاده نداد.")
                continue

            result.append(MarketSeries(
                key=f"{'commodity-proxy' if proxy else 'equity'}:cboe:{symbol}",
                symbol=symbol,
                name=symbol,
                asset_class="commodity_proxy" if proxy else "us_equity_etf",
                instrument="listed ETF proxy" if proxy else "US listed equity/ETF",
                provider="OpenBB Cboe",
                feed_class="Daily historical bars; potentially delayed",
                currency="USD",
                observations=points,
                observed_at=iso(),
                data_as_of=points[-1]["date"],
                caveat=(
                    "ETF proxy; not the underlying commodity spot or futures."
                    if proxy else
                    "Historical bars; not a live executable quote."
                ),
            ))

        except Exception as exc:
            errors.append(
                f"{symbol}: Cboe unavailable ({type(exc).__name__})."
            )

    return result, errors


def sanitized_exception_message(exc: Exception, limit: int = 240) -> str:
    """Return bounded diagnostic text without URLs or credential-like values."""
    message = " ".join(str(exc).split())
    message = re.sub(r"https?://\S+", "[URL]", message)
    message = re.sub(
        r"(?i)\b(api[_-]?key|token|authorization|bearer)\b\s*[:=]\s*[^\s,;]+",
        r"\1=[REDACTED]",
        message,
    )
    message = re.sub(
        r"(?i)([?&](?:api_key|apikey|token|access_token|key)=)[^&\s]+",
        r"\1[REDACTED]",
        message,
    )
    return message[:limit]


def fetch_fx_reference(
    obb: Any,
    pairs: list[str],
) -> tuple[list[MarketSeries], list[str]]:
    result: list[MarketSeries] = []
    errors: list[str] = []

    start = (date.today() - timedelta(days=220)).isoformat()

    for pair in pairs:
        try:
            if not pair.startswith("EUR"):
                errors.append(
                    f"{pair}: ECB در این اسکن فقط جفت‌های دارای EUR را پوشش می‌دهد."
                )
                continue

            # ECB's public endpoint can intermittently time out for an
            # individual currency pair. Retry only timeout failures once;
            # do not retry provider/schema errors or weaken data validation.
            retry_count = 1
            for attempt in range(retry_count + 1):
                try:
                    response = obb.ecb.exchange_rates(
                        provider="ecb",
                        symbol=pair,
                        start_date=start,
                    )
                    break
                except Exception as request_exc:
                    timeout_error = any(
                        isinstance(item, TimeoutError)
                        or "timeout" in type(item).__name__.casefold()
                        or "timeout" in str(item).casefold()
                        for item in (
                            request_exc,
                            request_exc.__cause__,
                            request_exc.__context__,
                        )
                        if item is not None
                    )
                    if not timeout_error or attempt >= retry_count:
                        raise
                    time.sleep(0.5)

            points = []

            for row in dataframe_rows(response):
                stamp = as_date(row.get("date") or row.get("index"))
                raw_value = row.get("value")

                if raw_value is None:
                    raw_value = row.get("close")

                close = as_float(raw_value)

                if stamp and close and close > 0:
                    points.append({
                        "date": stamp,
                        "close": close,
                        "volume": None,
                    })

            points.sort(key=lambda p: p["date"])

            if not points:
                errors.append(f"{pair}: ECB سری نرخ مرجع برنگرداند.")
                continue

            result.append(MarketSeries(
                key=f"fx-reference:ecb:{pair}",
                symbol=pair,
                name=pair,
                asset_class="fx_reference",
                instrument="ECB reference rate",
                provider="OpenBB ECB",
                feed_class="Official daily reference rate; not executable quote",
                currency=pair[-3:],
                observations=points,
                observed_at=iso(),
                data_as_of=points[-1]["date"],
                caveat="Reference rate only; no bid/ask, spread or market depth.",
            ))

        except Exception as exc:
            detail = sanitized_exception_message(exc)
            suffix = f": {detail}" if detail else ""
            errors.append(
                f"{pair}: ECB unavailable ({type(exc).__name__}){suffix}."
            )

    return result, errors


def fetch_energy(
    obb: Any,
    key_present: bool,
) -> tuple[list[MarketSeries], list[str]]:
    if not key_present:
        return [], ["EIA_API_KEY تنظیم نشده است."]

    result: list[MarketSeries] = []
    errors: list[str] = []

    calls = [
        (
            "Brent spot",
            "brent_spot",
            lambda: obb.eia.data_browser(
                provider="eia",
                route="petroleum/pri/spt",
                frequency="daily",
                facets="product:EPCBRENT",
                data_type="value",
                limit=260,
            ),
        ),
        (
            "Henry Hub spot",
            "henry_hub_spot",
            lambda: obb.eia.data_browser(
                provider="eia",
                route="natural-gas/pri/fut",
                frequency="daily",
                facets="series:RNGWHHD",
                data_type="value",
                limit=260,
            ),
        ),
    ]

    for title, key, fetch in calls:
        try:
            points = []

            for row in dataframe_rows(fetch()):
                stamp = as_date(row.get("date") or row.get("index"))
                raw_value = row.get("value")

                if raw_value is None:
                    raw_value = row.get("close")

                close = as_float(raw_value)

                if stamp and close is not None and close > 0:
                    points.append({
                        "date": stamp,
                        "close": close,
                        "volume": None,
                    })

            points.sort(key=lambda p: p["date"])

            if not points:
                errors.append(f"{title}: EIA داده قابل استفاده نداد.")
                continue

            result.append(MarketSeries(
                key=f"commodity:eia:{key}",
                symbol=key.upper(),
                name=title,
                asset_class="commodity_energy",
                instrument="published spot price series",
                provider="OpenBB EIA",
                feed_class="Official published daily observation; not real-time futures",
                currency="USD",
                observations=points,
                observed_at=iso(),
                data_as_of=points[-1]["date"],
                caveat="Published spot series; not an executable futures quote.",
            ))

        except Exception as exc:
            errors.append(
                f"{title}: EIA unavailable ({type(exc).__name__})."
            )

    return result, errors


def fetch_macro(
    obb: Any,
    key_present: bool,
) -> tuple[list[MarketSeries], list[str]]:
    if not key_present:
        return [], ["FRED_API_KEY تنظیم نشده است."]

    definitions = {
        "DGS10": ("US 10Y Treasury yield", "%"),
        "DGS2": ("US 2Y Treasury yield", "%"),
        "DTWEXBGS": ("US broad trade-weighted dollar index", "index"),
        "VIXCLS": ("Cboe VIX close", "index"),
    }

    result: list[MarketSeries] = []
    errors: list[str] = []

    start = (date.today() - timedelta(days=45)).isoformat()

    for symbol, (name, unit) in definitions.items():
        try:
            response = obb.fred.economy.fred_series(
                symbol=symbol,
                provider="fred",
                start_date=start,
            )

            points = []

            for row in dataframe_rows(response):
                stamp = as_date(row.get("date") or row.get("index"))
                raw_value = row.get("value")

                if raw_value is None:
                    raw_value = row.get(symbol)

                value = as_float(raw_value)

                if stamp and value is not None:
                    points.append({
                        "date": stamp,
                        "close": value,
                        "volume": None,
                    })

            points.sort(key=lambda p: p["date"])

            if not points:
                errors.append(f"FRED {symbol}: داده قابل استفاده نداد.")
                continue

            result.append(MarketSeries(
                key=f"macro:fred:{symbol}",
                symbol=symbol,
                name=name,
                asset_class="macro",
                instrument="economic/market context series",
                provider="OpenBB FRED",
                feed_class="Official published series",
                currency=unit,
                observations=points,
                observed_at=iso(),
                data_as_of=points[-1]["date"],
                caveat="Contextual macro data; not a standalone trade signal.",
            ))

        except Exception as exc:
            errors.append(
                f"FRED {symbol}: unavailable ({type(exc).__name__})."
            )

    return result, errors


def pct_change(new: float, old: float) -> float | None:
    if old == 0:
        return None
    return (new / old - 1) * 100


def clamp(value: float, low: float = 0, high: float = 100) -> float:
    return max(low, min(high, value))


def market_score(series: MarketSeries) -> dict[str, Any]:
    if series.asset_class in {"fx_reference", "macro"}:
        return {
            "score": None,
            "coverage": 0,
            "decision": "DATA_ONLY",
            "why": "Context/reference series; not independently tradable.",
        }

    if series.asset_class == "crypto":
        extra = series.extra

        changes = [
            extra.get("change_24h"),
            extra.get("change_7d"),
            extra.get("change_30d"),
        ]

        present = [float(v) for v in changes if v is not None]
        factors: list[tuple[float, float]] = []

        if len(present) >= 2:
            factors.append((
                clamp(50 + statistics.mean(present) * 2),
                0.40,
            ))

        if len(present) == 3:
            positive = sum(v > 0 for v in present)
            alignment = {3: 100, 2: 65, 1: 35, 0: 10}[positive]
            factors.append((alignment, 0.30))

        market_cap = extra.get("market_cap")
        volume = extra.get("volume_24h")
        fdv = extra.get("fdv")

        if market_cap and volume and market_cap > 0:
            factors.append((
                clamp(volume / market_cap * 100 * 10),
                0.20,
            ))

        if market_cap and fdv and market_cap > 0:
            ratio = fdv / market_cap
            dilution = (
                90 if ratio <= 1.1 else
                70 if ratio <= 1.5 else
                45 if ratio <= 2.5 else
                20
            )
            factors.append((dilution, 0.10))

        coverage = len(factors) / 4

        if coverage < 0.75:
            return {
                "score": None,
                "coverage": round(coverage * 100),
                "decision": "INSUFFICIENT_DATA",
                "why": "At least three of four crypto factors are required.",
            }

        weight = sum(w for _, w in factors)

        return {
            "score": round(sum(s * w for s, w in factors) / weight),
            "coverage": round(coverage * 100),
            "decision": "WATCH_ONLY",
            "why": (
                "Preliminary momentum, alignment, turnover and FDV screen; "
                "not a calibrated trading signal."
            ),
        }

    points = series.observations
    closes = [as_float(p.get("close")) for p in points]
    closes = [v for v in closes if v is not None and v > 0]

    if len(closes) < 61:
        return {
            "score": None,
            "coverage": round(len(closes) / 61 * 100),
            "decision": "INSUFFICIENT_HISTORY",
            "why": "Fewer than 61 valid observations.",
        }

    last = closes[-1]
    sma20 = statistics.mean(closes[-20:])
    sma50 = statistics.mean(closes[-50:])

    mom20 = pct_change(last, closes[-21])
    mom60 = pct_change(last, closes[-61])

    trend = (
        100 if last > sma20 > sma50
        else 75 if last > sma20 and last > sma50
        else 50 if last > sma20 or last > sma50
        else 20
    )

    momentum = clamp(50 + (mom20 or 0) * 2)

    returns = [
        closes[i] / closes[i - 1] - 1
        for i in range(1, len(closes))
        if closes[i - 1] > 0
    ]

    annual_factor = math.sqrt(252)

    volatility = (
        statistics.stdev(returns[-20:]) * annual_factor * 100
        if len(returns) >= 20 else None
    )

    volatility_score = clamp(100 - (volatility or 0) * 1.5)

    last_volume = as_float(points[-1].get("volume"))

    previous_volumes = [
        as_float(p.get("volume"))
        for p in points[-21:-1]
    ]

    previous_volumes = [
        v for v in previous_volumes if v is not None and v > 0
    ]

    volume_ratio = (
        last_volume / statistics.mean(previous_volumes)
        if last_volume and previous_volumes else None
    )

    drawdown = pct_change(last, max(closes[-60:]))

    if series.asset_class in {"us_equity_etf", "commodity_proxy"}:
        factors = [
            (trend, 0.35),
            (momentum, 0.25),
            (volatility_score, 0.20),
        ]

        if volume_ratio is not None:
            factors.append((
                clamp(50 + (volume_ratio - 1) * 35),
                0.20,
            ))
    else:
        factors = [
            (trend, 0.40),
            (momentum, 0.35),
            (volatility_score, 0.25),
        ]

    score = round(
        sum(s * w for s, w in factors)
        / sum(w for _, w in factors)
    )

    expected_factors = (
        4 if series.asset_class in {
            "us_equity_etf", "commodity_proxy"
        } else 3
    )

    coverage = min(100, round(len(factors) / expected_factors * 100))

    return {
        "score": score,
        "coverage": coverage,
        "decision": "WATCH_ONLY" if score >= 55 else "NO_RANK",
        "why": (
            f"20-period return {mom20:.1f}%; technical heuristic only."
            if mom20 is not None else
            "Historical observations available."
        ),
        "latest_price": last,
        "momentum_20": mom20,
        "momentum_60": mom60,
        "volatility_annualized_pct": volatility,
        "drawdown_from_60_period_high_pct": drawdown,
        "volume_ratio_20": volume_ratio,
    }


def stale(series: MarketSeries) -> bool:
    if not series.data_as_of:
        return True

    try:
        observation_date = date.fromisoformat(series.data_as_of[:10])
        age = date.today() - observation_date
    except ValueError:
        return True

    if age < timedelta(0):
        return True

    limits = {
        "us_equity_etf": int(os.getenv("MAX_EQUITY_AGE_DAYS", "4")),
        "commodity_proxy": int(os.getenv("MAX_EQUITY_AGE_DAYS", "4")),
        "commodity_energy": int(os.getenv("MAX_EIA_AGE_DAYS", "14")),
        "fx_reference": int(os.getenv("MAX_ECB_AGE_DAYS", "4")),
        "macro": int(os.getenv("MAX_FRED_AGE_DAYS", "10")),
    }

    if series.asset_class == "crypto":
        stamp = parse_timestamp(series.observed_at)

        if stamp is None:
            return True

        delta = now_utc() - stamp

        return (
            delta < timedelta(0)
            or delta > timedelta(
                minutes=int(os.getenv("MAX_CRYPTO_AGE_MINUTES", "30"))
            )
        )

    return age > timedelta(days=limits.get(series.asset_class, 30))


def ensure_db(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)

    db = sqlite3.connect(path)
    db.execute("PRAGMA foreign_keys = ON")

    db.execute("""
        CREATE TABLE IF NOT EXISTS ideas (
            id INTEGER PRIMARY KEY,
            asset_key TEXT NOT NULL,
            symbol TEXT NOT NULL,
            asset_class TEXT NOT NULL,
            source TEXT NOT NULL,
            data_as_of TEXT NOT NULL,
            recorded_at TEXT NOT NULL,
            price REAL NOT NULL,
            technical_score REAL,
            factor_coverage_pct INTEGER NOT NULL,
            decision TEXT NOT NULL,
            thesis TEXT NOT NULL,
            invalidation TEXT NOT NULL,
            UNIQUE(asset_key, data_as_of)
        )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS evaluations (
            id INTEGER PRIMARY KEY,
            idea_id INTEGER NOT NULL REFERENCES ideas(id),
            checkpoint_days INTEGER NOT NULL,
            evaluated_at TEXT NOT NULL,
            observed_at TEXT NOT NULL,
            price REAL NOT NULL,
            return_pct REAL NOT NULL,
            UNIQUE(idea_id, checkpoint_days)
        )
    """)

    db.commit()
    return db


def price_now(series: MarketSeries) -> float | None:
    if not series.observations:
        return None
    return as_float(series.observations[-1].get("close"))


def record_and_evaluate(
    db: sqlite3.Connection,
    series_list: list[MarketSeries],
    scores: dict[str, dict[str, Any]],
) -> None:
    timestamp = iso()

    current = {
        s.key: (s, price_now(s))
        for s in series_list
        if not stale(s)
    }

    for s in series_list:
        score = scores.get(s.key, {})
        price = price_now(s)

        if stale(s):
            continue

        if score.get("decision") == "DATA_ONLY":
            continue

        if score.get("score") is None or price is None or not s.data_as_of:
            continue

        db.execute("""
            INSERT OR IGNORE INTO ideas
            (asset_key,symbol,asset_class,source,data_as_of,recorded_at,
             price,technical_score,factor_coverage_pct,decision,thesis,invalidation)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            s.key,
            s.symbol,
            s.asset_class,
            s.provider,
            s.data_as_of,
            timestamp,
            price,
            score.get("score"),
            score.get("coverage", 0),
            score.get("decision", "NO_RANK"),
            score.get("why", ""),
            "Reassess when subsequent observations invalidate the recorded thesis.",
        ))

    pending = db.execute(
        "SELECT id,asset_key,data_as_of,price FROM ideas"
    ).fetchall()

    for idea_id, key, origin, origin_price in pending:
        match = current.get(key)

        if not match or match[1] is None or not origin_price:
            continue

        series, current_price = match

        try:
            days = (
                date.fromisoformat(series.data_as_of[:10])
                - date.fromisoformat(origin[:10])
            ).days
        except (ValueError, TypeError):
            continue

        if days < 0:
            continue

        tolerances = {1: 1, 7: 2, 30: 4, 90: 10, 365: 21}

        for checkpoint, tolerance in tolerances.items():
            exists = db.execute(
                "SELECT 1 FROM evaluations WHERE idea_id=? AND checkpoint_days=?",
                (idea_id, checkpoint),
            ).fetchone()

            if not exists and checkpoint <= days <= checkpoint + tolerance:
                db.execute("""
                    INSERT OR IGNORE INTO evaluations
                    (idea_id,checkpoint_days,evaluated_at,observed_at,price,return_pct)
                    VALUES(?,?,?,?,?,?)
                """, (
                    idea_id,
                    checkpoint,
                    timestamp,
                    series.data_as_of,
                    current_price,
                    (current_price / origin_price - 1) * 100,
                ))

    db.commit()



def persian_score_reason(reason: Any) -> str:
    translations = {
        "Context/reference series; not independently tradable.": "این سری صرفاً برای زمینه‌سازی و مرجع است و به‌تنهایی ابزار معاملاتی محسوب نمی‌شود.",
        "At least three of four crypto factors are required.": "برای محاسبه امتیاز، حداقل سه عامل از چهار عامل رمزارزی باید داده معتبر داشته باشند.",
        "Preliminary momentum, alignment, turnover and FDV screen; not a calibrated trading signal.": "غربالگری مقدماتی بر پایه مومنتوم، هم‌جهتی بازده‌ها، گردش معاملات و ارزش‌گذاری رقیق‌شده است؛ هنوز سیگنال معاملاتی کالیبره‌شده نیست.",
        "Fewer than 61 valid observations.": "کمتر از ۶۱ مشاهده معتبر در تاریخچه موجود است.",
        "Historical observations available.": "تاریخچه مشاهدات معتبر در دسترس است.",
    }
    text = str(reason or "").strip()
    if text in translations:
        return translations[text]
    match = re.match(r"20-period return ([+-]?\d+(?:\.\d+)?)%; technical heuristic only\.", text)
    if match:
        return f"بازده ۲۰ دوره‌ای: {float(match.group(1)):+.1f}٪؛ این فقط یک شاخص فنی مقدماتی است."
    if any("\u0600" <= char <= "\u06ff" for char in text):
        return text
    return "توضیح فنی امتیاز در نسخه فعلی موجود نیست."


def telegram_report(
    series_list: list[MarketSeries],
    errors: list[str],
    scores: dict[str, dict[str, Any]],
    universe_summary: str | None = None,
) -> str:
    tehran = now_utc().astimezone(ZoneInfo("Asia/Tehran"))
    divider = "━━━━━━━━━━━━━━━━━━━━"
    lines = [
        "🌐 گزارش روزانه رادار بازار GRIOS",
        f"🕒 زمان تهیه: {tehran.strftime('%Y-%m-%d | %H:%M')} به وقت تهران",
        divider,
        "📡 وضعیت پوشش بازار",
    ]

    labels = {
        "crypto": "رمزارزها",
        "us_equity_etf": "سهام و ETF آمریکا",
        "commodity_proxy": "صندوق‌های کالایی",
        "commodity_energy": "داده‌های انرژی",
        "fx_reference": "نرخ‌های مرجع ارز",
        "macro": "شاخص‌های اقتصاد کلان",
    }
    lines.extend(
        f"• {label}: {sum(s.asset_class == key for s in series_list)} نماد"
        for key, label in labels.items()
    )

    if universe_summary:
        lines.extend([divider, "🧪 فیلتر بازار رمزارز", universe_summary])

    ranked = []
    for item in series_list:
        score = scores.get(item.key, {})
        if stale(item):
            continue
        if score.get("score") is not None and score.get("decision") == "WATCH_ONLY":
            ranked.append((score["score"], item, score))
    ranked.sort(key=lambda value: value[0], reverse=True)

    if ranked:
        lines.extend([
            divider,
            "🔎 نامزدهای قابل‌پایش",
            "رتبه‌ها آزمایشی‌اند و سیگنال خرید یا فروش محسوب نمی‌شوند.",
        ])
        for index, (value, item, score) in enumerate(ranked[:7], 1):
            price = price_now(item)
            lines.extend([
                divider,
                f"{index}) {item.symbol} — امتیاز آزمایشی: {value}/100",
                f"📍 نوع دارایی: {labels.get(item.asset_class, item.asset_class)}",
                f"💵 آخرین قیمت: {price:g} {item.currency}" if price is not None else "💵 قیمت معتبر در دسترس نیست",
                f"🗓 تاریخ داده: {item.data_as_of or 'نامشخص'} | منبع: {item.provider}",
                f"📊 پوشش عوامل: {score.get('coverage', 0)}٪",
                f"🧩 مبنای امتیاز: {persian_score_reason(score.get('why'))}",
            ])

            if item.asset_class == "crypto":
                extra = item.extra
                momentum = " / ".join(
                    "ناموجود" if extra.get(key) is None else f"{extra[key]:+.1f}٪"
                    for key in ("change_24h", "change_7d", "change_30d")
                )
                lines.append(f"📈 تغییر قیمت (۲۴ ساعت / ۷ روز / ۳۰ روز): {momentum}")
                if extra.get("market_cap") and extra.get("volume_24h"):
                    turnover = extra["volume_24h"] / extra["market_cap"] * 100
                    lines.append(f"🔄 نسبت حجم معاملات به ارزش بازار: {turnover:.2f}٪")
                if extra.get("market_cap") and extra.get("fdv"):
                    lines.append(f"🧮 نسبت ارزش‌گذاری رقیق‌شده به ارزش بازار: {extra['fdv'] / extra['market_cap']:.2f} برابر")
                lines.append(f"🧾 وضعیت احراز داده: {extra.get('universe_status', 'نامشخص')}")

            if item.caveat:
                lines.append(f"⚠️ محدودیت داده: {item.caveat}")

    else:
        lines.extend([divider, "⏸️ در این نوبت، داده تازه و کافی برای معرفی نامزد قابل‌رتبه‌بندی وجود ندارد."])

    fx = [item for item in series_list if item.asset_class == "fx_reference" and not stale(item)]
    if fx:
        lines.extend([
            divider,
            "💱 بازار ارز",
            "داده‌های ارز در این بخش نرخ مرجع روزانه بانک مرکزی اروپا هستند؛ قیمت لحظه‌ای، نرخ خریدوفروش و فاصله Bid/Ask در این فید وجود ندارد.",
        ])

    macro = [item for item in series_list if item.asset_class == "macro" and not stale(item)]
    if macro:
        macro_labels = {
            "DGS10": "بازده اوراق ۱۰ساله آمریکا",
            "DGS2": "بازده اوراق ۲ساله آمریکا",
            "DTWEXBGS": "شاخص گسترده دلار",
            "VIXCLS": "شاخص نوسان VIX",
        }
        parts = [
            f"{macro_labels.get(item.symbol, item.symbol)}: {price_now(item):g} ({item.data_as_of})"
            for item in macro if price_now(item) is not None
        ]
        values = {item.symbol: price_now(item) for item in macro}
        if values.get("DGS10") is not None and values.get("DGS2") is not None:
            parts.append(f"اختلاف بازده ۱۰ساله و ۲ساله: {values['DGS10'] - values['DGS2']:+.2f} واحد درصد")
        lines.extend([divider, "🧭 نمای کلی اقتصاد کلان", *parts])

    if errors:
        lines.extend([divider, "⚠️ هشدارهای منابع داده"])
        lines.extend(f"• {error}" for error in errors[:8])

    lines.extend([
        divider,
        "🧭 جمع‌بندی کمیته سرمایه‌گذاری",
        "وضعیت این نسخه: فقط پایش (WATCH). داده جریان سرمایه نهادیِ تأییدشده، کاتالیست بنیادیِ کامل و مدل جامع ریسک به بازده هنوز در این گزارش ادغام نشده‌اند.",
        "⛔ امتیازها هنوز کالیبره و با آزمون تاریخی مستقل اعتبارسنجی نشده‌اند. این گزارش توصیه شخصی، سفارش معاملاتی یا تخصیص سرمایه صادر نمی‌کند.",
    ])
    lines.extend(social_footer_lines())
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="GRIOS research-only multi-source market scanner"
    )

    parser.add_argument(
        "--watchlist",
        default=str(ROOT / "watchlist.json"),
    )

    parser.add_argument(
        "--out",
        default=os.getenv("REPORT_DIR", "reports"),
    )

    parser.add_argument(
        "--db",
        default=os.getenv("JOURNAL_PATH", "data/opportunities.sqlite3"),
    )

    parser.add_argument("--skip-openbb", action="store_true")

    parser.add_argument(
        "--crypto-audit-source-commit-sha",
        default=os.getenv("GRIOS_SOURCE_COMMIT_SHA", "UNKNOWN"),
    )

    args = parser.parse_args()

    max_crypto_age = int(os.getenv("MAX_CRYPTO_AGE_MINUTES", "30"))
    crypto_audit: dict[str, Any] = {}

    watchlist = load_watchlist(Path(args.watchlist))
    crypto_config = watchlist["crypto_universe"]
    crypto_mode = crypto_config["mode"]

    crypto_symbols = (
        []
        if crypto_mode == "discovery"
        else watchlist["crypto_symbols"]
    )

    raw_crypto, crypto_errors = fetch_crypto(
        crypto_symbols,
        max_crypto_age,
        audit=crypto_audit,
    )

    crypto, universe_stats = filter_crypto_universe(
        raw_crypto,
        crypto_config,
        audit=crypto_audit,
    )

    excluded_text = ", ".join(
        f"{key}={value}"
        for key, value in sorted(
            universe_stats["excluded_reasons"].items()
        )
    )

    universe_mode_label = "کشف دارایی‌های واجد شرایط" if crypto_mode == "discovery" else "فهرست نمادهای منتخب"
    universe_summary = (
        f"حالت: {universe_mode_label} | "
        f"ورودی: {universe_stats['input_count']} | "
        f"واجد شرایط: {universe_stats['eligible_count']} | "
        f"حذف‌شده: {universe_stats['excluded_count']}"
    )

    if excluded_text:
        universe_summary += f" | دلایل: {excluded_text}"

    series: list[MarketSeries] = list(crypto)
    hub_series: list[MarketSeries] = list(raw_crypto)
    errors: list[str] = list(crypto_errors)

    if not args.skip_openbb:
        try:
            obb = get_openbb()

            equities, equity_errors = fetch_equity(
                obb,
                watchlist["us_equities_etfs"],
            )

            proxies, proxy_errors = fetch_equity(
                obb,
                watchlist["commodity_etf_proxies"],
                proxy=True,
            )

            fx, fx_errors = fetch_fx_reference(
                obb,
                watchlist["fx_reference_pairs"],
            )

            energy, energy_errors = fetch_energy(
                obb,
                bool(os.getenv("EIA_API_KEY", "").strip()),
            )

            macro, macro_errors = fetch_macro(
                obb,
                bool(os.getenv("FRED_API_KEY", "").strip()),
            )

            collected_series = equities + proxies + fx + energy + macro
            series.extend(collected_series)
            hub_series.extend(collected_series)

            errors.extend(
                equity_errors
                + proxy_errors
                + fx_errors
                + energy_errors
                + macro_errors
            )

        except ImportError:
            errors.append("OpenBB نصب یا قابل بارگذاری نیست.")

        except Exception as exc:
            errors.append(
                f"راه‌اندازی OpenBB ناموفق بود ({type(exc).__name__})."
            )

    scores = {
        item.key: market_score(item)
        for item in series
    }

    coverage_report = build_data_coverage_report(
        watchlist,
        hub_series,
        errors,
    )
    hub_result = publish_market_series(
        hub_series,
        source_revision=args.crypto_audit_source_commit_sha,
    )
    coverage_report["data_hub"] = {
        "status": hub_result["status"],
        "accepted": hub_result["accepted"],
        "error": hub_result["error"],
    }

    report = telegram_report(
        series,
        errors,
        scores,
        universe_summary=universe_summary,
    )
    coverage_labels = {
        "COVERED": "پوشش کامل فیدهای درخواستی",
        "DEGRADED": "پوشش ناقص",
        "DISCOVERY": "حالت کشف دارایی",
    }
    hub_labels = {
        "DIRECT_SUPABASE": "اتصال مستقیم به پایگاه داده برقرار",
        "CONNECTED": "اتصال به هاب داده برقرار",
        "NOT_CONFIGURED": "اتصال تنظیم نشده",
        "FAILED": "ارسال ناموفق",
        "NO_DATA": "داده‌ای برای ارسال وجود نداشت",
        "CONFIG_ERROR": "خطای تنظیمات",
        "REJECTED": "داده توسط مقصد پذیرفته نشد",
    }
    report += (
        f"\n\n━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 جمع‌بندی پوشش داده: {coverage_labels.get(coverage_report['overall_status'], 'وضعیت نامشخص')}\n"
        f"🔗 وضعیت ذخیره‌سازی: {hub_labels.get(hub_result['status'], 'وضعیت نامشخص')}\n"
        f"📥 تعداد رکورد پذیرفته‌شده: {hub_result['accepted']}\n"
    )

    output_dir = Path(args.out)
    output_dir.mkdir(parents=True, exist_ok=True)

    stamp = now_utc().strftime("%Y%m%dT%H%M%SZ")

    coverage_path = output_dir / f"data-coverage-{stamp}.json"
    coverage_path.write_text(
        json.dumps(coverage_report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (output_dir / "latest-coverage.json").write_text(
        json.dumps(coverage_report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    audit_path = save_crypto_audit(
        crypto_audit,
        output_dir,
        stamp,
        args.crypto_audit_source_commit_sha,
        crypto_mode,
        max_crypto_age,
    )

    report_path = output_dir / f"grios-{stamp}.txt"

    report_path.write_text(report + "\n", encoding="utf-8")
    (output_dir / "latest.txt").write_text(
        report + "\n",
        encoding="utf-8",
    )

    db = ensure_db(Path(args.db))

    try:
        record_and_evaluate(db, series, scores)
    finally:
        db.close()

    print(report)
    print(f"\nSaved: {report_path}")
    print(f"Crypto audit: {audit_path}")
    print(f"Data coverage: {coverage_path}")
    print("Data Hub: " + hub_result["status"] + " (" + str(hub_result["accepted"]) + " accepted)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
