from __future__ import annotations

import argparse
import json
import math
import os
import re
import sqlite3
import statistics
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

CG_URL = "https://api.coingecko.com/api/v3/coins/markets"
CMC_URL = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest"

DEFAULT_CRYPTO_SYMBOLS = [
    "BTC", "ETH", "BNB", "SOL", "XRP", "DOGE", "ADA",
    "TRX", "LINK", "AVAX", "LTC", "BCH", "DOT", "TON",
]


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


def load_watchlist(path: Path) -> dict[str, list[str]]:
    keys = (
        "us_equities_etfs",
        "commodity_etf_proxies",
        "fx_reference_pairs",
        "crypto_symbols",
    )
    if not path.exists():
        return {key: [] for key in keys}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {
        key: [str(v).strip().upper() for v in data.get(key, []) if str(v).strip()]
        for key in keys
    }


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
    if not symbol or not name or parsed_price is None or parsed_price <= 0 or parsed_stamp is None:
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
        feed_class="aggregated crypto spot; provider timestamp checked",
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
) -> tuple[list[MarketSeries], str | None]:
    if not api_key:
        return [], "COINGECKO_API_KEY تنظیم نشده است."

    params = {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": 250,
        "page": 1,
        "sparkline": "false",
        "price_change_percentage": "24h,7d,30d",
    }
    headers = {"x-cg-demo-api-key": api_key}

    try:
        response = httpx.get(
            CG_URL, params=params, headers=headers, timeout=30
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, list):
            return [], "CoinGecko پاسخ با ساختار مورد انتظار برنگرداند."

        rows: list[MarketSeries] = []
        for item in payload:
            if not isinstance(item, dict):
                continue

            symbol = str(item.get("symbol") or "").upper()
            name = str(item.get("name") or "")
            if symbols and symbol not in symbols:
                continue

            checked = valid_crypto_row(
                symbol,
                name,
                item.get("current_price"),
                item.get("last_updated"),
                max_age_minutes,
            )
            if not checked:
                continue

            price, stamp = checked
            rows.append(crypto_series(
                symbol=symbol,
                name=name,
                provider="CoinGecko",
                stamp=stamp,
                price=price,
                market_cap=item.get("market_cap"),
                volume=item.get("total_volume"),
                fdv=item.get("fully_diluted_valuation"),
                change_24h=item.get("price_change_percentage_24h"),
                change_7d=item.get("price_change_percentage_7d_in_currency"),
                change_30d=item.get("price_change_percentage_30d_in_currency"),
                slug=str(item.get("id") or ""),
            ))
        return rows, None if rows else "CoinGecko داده معتبر و تازه‌ای برای Watchlist برنگرداند."

    except (httpx.HTTPError, ValueError, TypeError):
        return [], "اتصال CoinGecko ناموفق بود؛ نوع خطا در گزارش ثبت شد، نه اطلاعات محرمانه."


def fetch_coinmarketcap(
    api_key: str,
    symbols: list[str],
    max_age_minutes: int,
) -> tuple[list[MarketSeries], str | None]:
    if not api_key:
        return [], "COINMARKETCAP_API_KEY تنظیم نشده است."

    params = {
        "start": 1,
        "limit": 500,
        "convert": "USD",
    }
    headers = {
        "X-CMC_PRO_API_KEY": api_key,
        "Accept": "application/json",
    }

    try:
        response = httpx.get(
            CMC_URL, params=params, headers=headers, timeout=30
        )
        response.raise_for_status()
        payload = response.json()
        items = payload.get("data", []) if isinstance(payload, dict) else []
        if not isinstance(items, list):
            return [], "CoinMarketCap پاسخ با ساختار مورد انتظار برنگرداند."

        rows: list[MarketSeries] = []
        for item in items:
            if not isinstance(item, dict):
                continue

            symbol = str(item.get("symbol") or "").upper()
            name = str(item.get("name") or "")
            if symbols and symbol not in symbols:
                continue

            quote = item.get("quote")
            if isinstance(quote, list):
                quote = quote[0] if quote else {}
            if not isinstance(quote, dict):
                continue
            usd = quote.get("USD")
            if isinstance(usd, list):
                usd = usd[0] if usd else {}
            if not isinstance(usd, dict):
                continue

            stamp_value = usd.get("last_updated") or item.get("last_updated")
            checked = valid_crypto_row(
                symbol,
                name,
                usd.get("price"),
                stamp_value,
                max_age_minutes,
            )
            if not checked:
                continue

            price, stamp = checked
            rows.append(crypto_series(
                symbol=symbol,
                name=name,
                provider="CoinMarketCap",
                stamp=stamp,
                price=price,
                market_cap=usd.get("market_cap"),
                volume=usd.get("volume_24h"),
                fdv=usd.get("fully_diluted_market_cap"),
                change_24h=usd.get("percent_change_24h"),
                change_7d=usd.get("percent_change_7d"),
                change_30d=usd.get("percent_change_30d"),
                slug=str(item.get("slug") or ""),
            ))
        return rows, None if rows else "CoinMarketCap داده معتبر و تازه‌ای برای Watchlist برنگرداند."

    except (httpx.HTTPError, ValueError, TypeError):
        return [], "اتصال CoinMarketCap ناموفق بود؛ نوع خطا در گزارش ثبت شد، نه اطلاعات محرمانه."


def reconcile_crypto(
    rows: list[MarketSeries],
) -> tuple[list[MarketSeries], list[str]]:
    groups: dict[tuple[str, str], list[MarketSeries]] = {}
    for row in rows:
        identity = (row.symbol, normalized_name(row.name))
        groups.setdefault(identity, []).append(row)

    accepted: list[MarketSeries] = []
    conflicts: list[str] = []

    for (symbol, _), group in groups.items():
        providers = {item.provider for item in group}
        if len(providers) < 2:
            accepted.extend(group)
            continue

        prices = [item.observations[-1]["close"] for item in group if item.observations]
        if len(prices) < 2:
            accepted.extend(group)
            continue

        median = statistics.median(prices)
        deviation = ((max(prices) - min(prices)) / median * 100) if median else 999

        if deviation > 2.0:
            conflicts.append(
                f"{symbol}: اختلاف قیمت منابع {deviation:.2f}% بود؛ از رتبه‌بندی حذف شد."
            )
            continue

        chosen = max(group, key=lambda item: item.observed_at or "")
        chosen.key = f"crypto:asset:{symbol}:{normalized_name(chosen.name)}"
        chosen.provider = " + ".join(sorted(providers))
        chosen.caveat = (
            (chosen.caveat or "")
            + f" Cross-source price deviation: {deviation:.2f}%."
        )
        accepted.append(chosen)

    return accepted, conflicts


def fetch_crypto(
    symbols: list[str],
    max_age_minutes: int,
) -> tuple[list[MarketSeries], list[str]]:
    cg, cg_error = fetch_coingecko(
        os.getenv("COINGECKO_API_KEY", "").strip(),
        symbols,
        max_age_minutes,
    )
    cmc, cmc_error = fetch_coinmarketcap(
        os.getenv("COINMARKETCAP_API_KEY", "").strip(),
        symbols,
        max_age_minutes,
    )

    combined, conflicts = reconcile_crypto(cg + cmc)
    errors = [e for e in (cg_error, cmc_error) if e]
    errors.extend(conflicts)

    if not combined and not errors:
        errors.append("هیچ داده معتبر کریپتو دریافت نشد.")
    return combined, errors


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
                    "ETF proxy; not the underlying commodity spot or futures contract."
                    if proxy else
                    "Historical bars; not a live executable quote."
                ),
            ))
        except Exception as exc:
            errors.append(f"{symbol}: Cboe unavailable ({type(exc).__name__}).")

    return result, errors


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
                errors.append(f"{pair}: ECB در این اسکن فقط جفت‌های دارای EUR را پوشش می‌دهد.")
                continue

            response = obb.ecb.exchange_rates(
                provider="ecb",
                symbol=pair,
                start_date=start,
            )
            points = []
            for row in dataframe_rows(response):
                stamp = as_date(row.get("date") or row.get("index"))
                raw_value = row.get("value")
                if raw_value is None:
                    raw_value = row.get("close")
                close = as_float(raw_value)
                if stamp and close and close > 0:
                    points.append({"date": stamp, "close": close, "volume": None})
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
            errors.append(f"{pair}: ECB unavailable ({type(exc).__name__}).")

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
            lambda: obb.eia.natural_gas.prices.natural_gas_spot_and_futures_prices(
                provider="eia",
                series="henry_hub_natural_gas_spot_price",
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
                    points.append({"date": stamp, "close": close, "volume": None})
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
            errors.append(f"{title}: EIA unavailable ({type(exc).__name__}).")

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
                    points.append({"date": stamp, "close": value, "volume": None})
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
            errors.append(f"FRED {symbol}: unavailable ({type(exc).__name__}).")

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

        market_cap = extra.get("market_cap")
        volume = extra.get("volume_24h")
        fdv = extra.get("fdv")

        if len(present) >= 2:
            factors.append((clamp(50 + statistics.mean(present) * 2), .40))
        if len(present) == 3:
            positive = sum(v > 0 for v in present)
            alignment = {3: 100, 2: 65, 1: 35, 0: 10}[positive]
            factors.append((alignment, .30))
        if market_cap and volume and market_cap > 0:
            factors.append((clamp(volume / market_cap * 100 * 10), .20))
        if market_cap and fdv and market_cap > 0:
            ratio = fdv / market_cap
            dilution = 90 if ratio <= 1.1 else 70 if ratio <= 1.5 else 45 if ratio <= 2.5 else 20
            factors.append((dilution, .10))

        coverage = len(factors) / 4
        if coverage < .75:
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
            "why": "Preliminary momentum, alignment, turnover and FDV screen; not a calibrated trading signal.",
        }

    points = series.observations
    closes = [
        as_float(p.get("close"))
        for p in points
    ]
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

    annual_factor = (
        math.sqrt(252)
        if series.asset_class in {
            "us_equity_etf", "commodity_proxy", "commodity_energy"
        }
        else math.sqrt(52)
    )
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
        factors = [(trend, .35), (momentum, .25), (volatility_score, .20)]
        if volume_ratio is not None:
            factors.append((clamp(50 + (volume_ratio - 1) * 35), .20))
    else:
        factors = [(trend, .40), (momentum, .35), (volatility_score, .25)]

    score = round(sum(s * w for s, w in factors) / sum(w for _, w in factors))
    expected_factors = 4 if series.asset_class in {
        "us_equity_etf", "commodity_proxy"
    } else 3
    coverage = round(len(factors) / expected_factors * 100)

    return {
        "score": score,
        "coverage": min(100, coverage),
        "decision": "WATCH_ONLY" if score >= 55 else "NO_RANK",
        "why": f"20-period return {mom20:.1f}%; technical heuristic only." if mom20 is not None else "Historical observations available.",
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
        return delta < timedelta(0) or delta > timedelta(
            minutes=int(os.getenv("MAX_CRYPTO_AGE_MINUTES", "30"))
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
            s.key, s.symbol, s.asset_class, s.provider, s.data_as_of,
            timestamp, price, score.get("score"), score.get("coverage", 0),
            score.get("decision", "NO_RANK"), score.get("why", ""),
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
                    idea_id, checkpoint, timestamp, series.data_as_of,
                    current_price, (current_price / origin_price - 1) * 100,
                ))

    db.commit()


def telegram_report(
    series_list: list[MarketSeries],
    errors: list[str],
    scores: dict[str, dict[str, Any]],
) -> str:
    tehran = now_utc().astimezone(ZoneInfo("Asia/Tehran"))
    lines = [
        f"🌐 GRIOS | رادار فرصت‌ها | {tehran.strftime('%Y-%m-%d %H:%M')} تهران"
    ]

    labels = {
        "crypto": "کریپتو اسپات",
        "us_equity_etf": "سهام و ETF آمریکا",
        "commodity_proxy": "ETFهای نماینده کالا",
        "commodity_energy": "سری‌های انرژی EIA",
        "fx_reference": "نرخ مرجع ECB",
        "macro": "زمینه کلان FRED",
    }

    lines.append(
        "📡 پوشش: "
        + " | ".join(
            f"{label}: {sum(s.asset_class == key for s in series_list)}"
            for key, label in labels.items()
        )
    )

    ranked = []
    for s in series_list:
        score = scores.get(s.key, {})
        if stale(s):
            continue
        if score.get("score") is not None and score.get("decision") == "WATCH_ONLY":
            ranked.append((score["score"], s, score))

    ranked.sort(key=lambda x: x[0], reverse=True)

    if ranked:
        lines.append("\n🔎 نامزدهای پایش — امتیاز آزمایشی، نه سیگنال معامله")
        for index, (value, s, score) in enumerate(ranked[:7], 1):
            price = price_now(s)
            lines.append(
                f"\n{index}. {s.symbol} | امتیاز {value}/100 "
                f"| پوشش {score['coverage']}% | {s.asset_class}"
            )
            lines.append(
                f"   آخرین قیمت: {price:g} {s.currency} "
                f"| تاریخ داده: {s.data_as_of} | منبع: {s.provider}"
            )
            lines.append(f"   مبنا: {score['why']}")

            if s.asset_class == "crypto":
                extra = s.extra
                momentum = "/".join(
                    "—" if extra.get(k) is None else f"{extra[k]:+.1f}%"
                    for k in ("change_24h", "change_7d", "change_30d")
                )
                lines.append(f"   بازده ۲۴س/۷ر/۳۰ر: {momentum}")

                if extra.get("market_cap") and extra.get("volume_24h"):
                    turnover = extra["volume_24h"] / extra["market_cap"] * 100
                    lines.append(f"   گردش حجم/ارزش بازار: {turnover:.2f}%")

                if extra.get("market_cap") and extra.get("fdv"):
                    ratio = extra["fdv"] / extra["market_cap"]
                    lines.append(f"   FDV/ارزش بازار: {ratio:.2f}x")

            if s.caveat:
                lines.append(f"   محدودیت داده: {s.caveat}")

    else:
        lines.append("\n⏸️ داده تازه و کافی برای نامزد رتبه‌پذیر وجود ندارد.")

    fx = [s for s in series_list if s.asset_class == "fx_reference" and not stale(s)]
    if fx:
        lines.append(
            "\n💱 فارکس: فقط نرخ مرجع روزانه ECB؛ "
            "بدون bid/ask و spread، سیگنال خرید/فروش صادر نمی‌شود."
        )

    macro = [s for s in series_list if s.asset_class == "macro" and not stale(s)]
    if macro:
        parts = [
            f"{s.symbol} {price_now(s):g}{s.currency} ({s.data_as_of})"
            for s in macro if price_now(s) is not None
        ]
        values = {s.symbol: price_now(s) for s in macro}
        if values.get("DGS10") is not None and values.get("DGS2") is not None:
            parts.append(f"10Y-2Y: {values['DGS10'] - values['DGS2']:+.2f}pp")
        lines.append("\n🧭 زمینه کلان FRED: " + " | ".join(parts))

    if errors:
        lines.append("\n⚠️ وضعیت فیدها:")
        lines.extend(f"• {error}" for error in errors[:8])

    lines.append(
        "\n🧭 تصمیم CIO: فقط WATCH. این نسخه ابزار غربالگری اولیه است؛ "
        "جریان نهادی تأییدشده، کاتالیزور بنیادی و نسبت ریسک/بازده کامل هنوز متصل نیست."
    )
    lines.append(
        "امتیازها کالیبره یا به‌صورت تاریخی اعتبارسنجی نشده‌اند؛ "
        "هیچ سفارش یا تخصیص سرمایه‌ای صادر نمی‌شود."
    )

    return "\n".join(lines)[:3900]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="GRIOS research-only multi-source market scanner"
    )
    parser.add_argument("--watchlist", default=str(ROOT / "watchlist.json"))
    parser.add_argument("--out", default=os.getenv("REPORT_DIR", "reports"))
    parser.add_argument("--db", default=os.getenv("JOURNAL_PATH", "data/opportunities.sqlite3"))
    parser.add_argument("--skip-openbb", action="store_true")
    args = parser.parse_args()

    watchlist = load_watchlist(Path(args.watchlist))
    crypto_symbols = watchlist["crypto_symbols"]

    crypto, crypto_errors = fetch_crypto(
        crypto_symbols,
        int(os.getenv("MAX_CRYPTO_AGE_MINUTES", "30")),
    )
    series: list[MarketSeries] = list(crypto)
    errors: list[str] = list(crypto_errors)

    if not args.skip_openbb:
        try:
            obb = get_openbb()

            equities, equity_errors = fetch_equity(
                obb, watchlist["us_equities_etfs"]
            )
            proxies, proxy_errors = fetch_equity(
                obb, watchlist["commodity_etf_proxies"], proxy=True
            )
            fx, fx_errors = fetch_fx_reference(
                obb, watchlist["fx_reference_pairs"]
            )
            energy, energy_errors = fetch_energy(
                obb, bool(os.getenv("EIA_API_KEY", "").strip())
            )
            macro, macro_errors = fetch_macro(
                obb, bool(os.getenv("FRED_API_KEY", "").strip())
            )

            series.extend(equities + proxies + fx + energy + macro)
            errors.extend(
                equity_errors + proxy_errors + fx_errors
                + energy_errors + macro_errors
            )

        except ImportError:
            errors.append("OpenBB نصب یا قابل بارگذاری نیست.")
        except Exception as exc:
            errors.append(
                f"راه‌اندازی OpenBB ناموفق بود ({type(exc).__name__})."
            )

    scores = {item.key: market_score(item) for item in series}
    report = telegram_report(series, errors, scores)

    output_dir = Path(args.out)
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = now_utc().strftime("%Y%m%dT%H%M%SZ")

    report_path = output_dir / f"grios-{stamp}.txt"
    report_path.write_text(report + "\n", encoding="utf-8")
    (output_dir / "latest.txt").write_text(report + "\n", encoding="utf-8")

    db = ensure_db(Path(args.db))
    try:
        record_and_evaluate(db, series, scores)
    finally:
        db.close()

    print(report)
    print(f"\nSaved: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
