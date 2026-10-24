from __future__ import annotations

import argparse
import json
import math
import os
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


def load_watchlist(path: Path) -> dict[str, list[str]]:
    if not path.exists():
        return {"us_equities_etfs": [], "commodity_etf_proxies": [], "fx_reference_pairs": [], "crypto_symbols": []}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {key: [str(v).upper() for v in data.get(key, [])] for key in (
        "us_equities_etfs", "commodity_etf_proxies", "fx_reference_pairs", "crypto_symbols"
    )}


def get_openbb() -> Any:
    from openbb import obb  # type: ignore[import-not-found]

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


def as_float(value: Any) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


def as_date(value: Any) -> str | None:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()[:10]
    return str(value)[:10]


def fetch_crypto(url: str | None, max_age_minutes: int, symbols: list[str]) -> tuple[list[MarketSeries], str | None]:
    if not url:
        return [], "GRIOS_DATA_HUB_URL تنظیم نشده؛ کریپتو از Data Hub دریافت نشد."
    base = url.rstrip("/")
    endpoint = base if base.endswith("/v1/markets/latest") else f"{base}/v1/markets/latest"
    try:
        response = httpx.get(endpoint, params={"limit": 250}, timeout=20)
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, list):
            return [], "پاسخ Data Hub ساختار مورد انتظار را نداشت."
        rows: list[MarketSeries] = []
        for item in payload:
            stamp = item.get("observed_at")
            price = as_float(item.get("price_usd"))
            symbol = str(item.get("symbol") or "").upper()
            if not stamp or not price or not symbol:
                continue
            if symbols and symbol not in symbols:
                continue
            try:
                age = now_utc() - datetime.fromisoformat(stamp.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                continue
            if age < timedelta(0) or age > timedelta(minutes=max_age_minutes):
                continue
            rows.append(MarketSeries(
                key=f"crypto:{item.get('provider')}:{symbol}",
                symbol=symbol,
                name=str(item.get("name") or symbol),
                asset_class="crypto",
                instrument="spot token",
                provider=str(item.get("provider") or "GRIOS Data Hub"),
                feed_class="aggregated crypto spot; freshness from provider timestamp",
                currency="USD",
                observations=[{"date": stamp[:10], "close": price}],
                observed_at=stamp,
                data_as_of=stamp,
                caveat="بدون OHLCV تاریخچه‌ای، spread، خبر/کاتالیزور یا جریان منتسب؛ فقط پایش تکنیکال اولیه.",
                extra={
                    "market_cap": as_float(item.get("market_cap_usd")),
                    "volume_24h": as_float(item.get("volume_24h_usd")),
                    "fdv": as_float(item.get("fdv_usd")),
                    "change_24h": as_float(item.get("change_24h")),
                    "change_7d": as_float(item.get("change_7d")),
                    "change_30d": as_float(item.get("change_30d")),
                },
            ))
        rows, conflicts = reconcile_crypto(rows)
        return rows, "; ".join(conflicts) if conflicts else (None if rows else "داده کریپتو خالی یا از پنجره تازگی خارج بود؛ رتبه‌بندی سرکوب شد.")
    except (httpx.HTTPError, ValueError, TypeError) as exc:
        return [], f"اتصال GRIOS Data Hub ناموفق بود: {type(exc).__name__}."


def reconcile_crypto(rows: list[MarketSeries]) -> tuple[list[MarketSeries], list[str]]:
    groups: dict[tuple[str, str], list[MarketSeries]] = {}
    for row in rows:
        identity = (row.symbol, row.name.strip().casefold())
        groups.setdefault(identity, []).append(row)
    accepted: list[MarketSeries] = []
    conflicts: list[str] = []
    for (symbol, _), group in groups.items():
        if len(group) == 1 or len({item.provider for item in group}) < 2:
            accepted.append(group[0])
            accepted.extend(group[1:])
            continue
        prices = [price_now(item) for item in group]
        prices = [value for value in prices if value is not None]
        if len(prices) < 2:
            accepted.extend(group)
            continue
        median = statistics.median(prices)
        deviation_pct = (max(prices) - min(prices)) / median * 100 if median else math.inf
        providers = sorted({item.provider for item in group})
        if deviation_pct > 2.0:
            conflicts.append(f"اختلاف قیمت {symbol} بین {', '.join(providers)} برابر {deviation_pct:.1f}% بود؛ از رتبه خارج شد")
            continue
        chosen = max(group, key=lambda item: item.observed_at or "")
        chosen.key = f"crypto:cross-checked:{symbol}:{chosen.data_as_of}"
        chosen.provider = " + ".join(providers)
        chosen.caveat = (chosen.caveat or "") + f" تأیید متقاطع {len(providers)} فید؛ فاصله قیمت‌ها {deviation_pct:.2f}%."
        accepted.append(chosen)
    return accepted, conflicts


def fetch_equity(obb: Any, symbols: list[str], *, proxy: bool = False) -> tuple[list[MarketSeries], list[str]]:
    result: list[MarketSeries] = []
    errors: list[str] = []
    start = (date.today() - timedelta(days=220)).isoformat()
    end = date.today().isoformat()
    for symbol in symbols:
        try:
            response = obb.cboe.equity.historical(
                symbol=symbol, start_date=start, end_date=end, provider="cboe"
            )
            raw = dataframe_rows(response)
            points = []
            for row in raw:
                stamp = as_date(row.get("date") or row.get("index"))
                close = as_float(row.get("close"))
                if stamp and close:
                    points.append({"date": stamp, "close": close, "volume": as_float(row.get("volume"))})
            points.sort(key=lambda p: p["date"])
            if not points:
                errors.append(f"{symbol}: Cboe تاریخچه‌ای برنگرداند.")
                continue
            result.append(MarketSeries(
                key=f"{'commodity-proxy' if proxy else 'equity'}:cboe:{symbol}",
                symbol=symbol,
                name=symbol,
                asset_class="commodity_proxy" if proxy else "us_equity_etf",
                instrument="listed ETF proxy" if proxy else "US listed equity/ETF",
                provider="OpenBB Cboe",
                feed_class="Cboe market data; daily historical bars, potentially delayed",
                currency="USD",
                observations=points,
                observed_at=iso(),
                data_as_of=points[-1]["date"],
                caveat=("ETF proxy; not the underlying metal/energy spot or futures contract. Roll, tracking and issuer risks apply." if proxy else "Daily historical bars; not a live executable quote. Volume availability is source-dependent."),
            ))
        except Exception as exc:  # Provider failures are recorded without hiding the rest of the scan.
            errors.append(f"{symbol}: Cboe unavailable ({type(exc).__name__}).")
    return result, errors


def fetch_fx_reference(obb: Any, pairs: list[str]) -> tuple[list[MarketSeries], list[str]]:
    result: list[MarketSeries] = []
    errors: list[str] = []
    start = (date.today() - timedelta(days=220)).isoformat()
    for pair in pairs:
        try:
            if not pair.startswith("EUR"):
                errors.append(f"{pair}: ECB فقط نرخ‌های مرجع دارای یورو را پوشش می‌دهد؛ حذف شد.")
                continue
            response = obb.ecb.exchange_rates(
                provider="ecb", symbol=pair, start_date=start
            )
            raw = dataframe_rows(response)
            points = []
            for row in raw:
                stamp = as_date(row.get("date") or row.get("index"))
                close = as_float(row.get("close") or row.get("value"))
                if stamp and close:
                    points.append({"date": stamp, "close": close, "volume": None})
            points.sort(key=lambda p: p["date"])
            if not points:
                errors.append(f"{pair}: ECB سری نرخ مرجع نداد.")
                continue
            result.append(MarketSeries(
                key=f"fx-reference:ecb:{pair}", symbol=pair, name=pair,
                asset_class="fx_reference", instrument="ECB reference rate",
                provider="OpenBB ECB", feed_class="official daily reference rate, not tradable quote",
                currency=pair[-3:], observations=points, observed_at=iso(),
                data_as_of=points[-1]["date"],
                caveat="نرخ مرجع ECB است؛ spread، market depth، intraday prices، carry differential و executable bid/ask در دسترس نیستند؛ خرید/فروش رتبه‌بندی نمی‌شود.",
            ))
        except Exception as exc:
            errors.append(f"{pair}: ECB unavailable ({type(exc).__name__}).")
    return result, errors


def fetch_energy(obb: Any, eia_key_present: bool) -> tuple[list[MarketSeries], list[str]]:
    if not eia_key_present:
        return [], ["EIA_API_KEY تنظیم نشده؛ قیمت/بنیاد نفت و گاز از EIA دریافت نشد."]
    result: list[MarketSeries] = []
    errors: list[str] = []
    calls = [
        ("Brent spot", "brent_spot", lambda: obb.eia.data_browser(
            provider="eia", route="petroleum/pri/spt", frequency="daily",
            facets="product:EPCBRENT", data_type="value", limit=260,
        )),
        ("Henry Hub spot", "henry_hub_spot", lambda: obb.eia.natural_gas.prices.natural_gas_spot_and_futures_prices(
            provider="eia", series="henry_hub_natural_gas_spot_price", limit=260,
        )),
    ]
    for title, key, fetch in calls:
        try:
            raw = dataframe_rows(fetch())
            points = []
            for row in raw:
                stamp = as_date(row.get("date") or row.get("index"))
                close = as_float(row.get("value") or row.get("close"))
                if stamp and close:
                    points.append({"date": stamp, "close": close, "volume": None})
            points.sort(key=lambda p: p["date"])
            if not points:
                errors.append(f"{title}: EIA returned no usable observations.")
                continue
            result.append(MarketSeries(
                key=f"commodity:eia:{key}", symbol=key.upper(), name=title,
                asset_class="commodity_energy", instrument="spot price series",
                provider="OpenBB EIA", feed_class="official periodic/daily published observation; not real-time futures",
                currency="USD", observations=points, observed_at=iso(), data_as_of=points[-1]["date"],
                caveat="قیمت اسپات/سری منتشرشده است، نه مظنه لحظه‌ای قرارداد آتی. ذخایر، منحنی آتی و عرضه/تقاضا در این نسخه به score وارد نشده‌اند.",
            ))
        except Exception as exc:
            errors.append(f"{title}: EIA unavailable ({type(exc).__name__}).")
    return result, errors


def fetch_macro(obb: Any, fred_key_present: bool) -> tuple[list[MarketSeries], list[str]]:
    if not fred_key_present:
        return [], ["FRED_API_KEY تنظیم نشده؛ زمینهٔ کلان منتشر نشد."]
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
                symbol=symbol, provider="fred", start_date=start
            )
            raw = dataframe_rows(response)
            points = []
            for row in raw:
                stamp = as_date(row.get("date") or row.get("index"))
                value = as_float(row.get("value"))
                if stamp and value is not None:
                    points.append({"date": stamp, "close": value, "volume": None})
            points.sort(key=lambda point: point["date"])
            if not points:
                errors.append(f"FRED {symbol}: no observations.")
                continue
            result.append(MarketSeries(
                key=f"macro:fred:{symbol}", symbol=symbol, name=name,
                asset_class="macro", instrument="economic/market context series",
                provider="OpenBB FRED", feed_class="official published series; observation date is distinct from retrieval time",
                currency=unit, observations=points, observed_at=iso(), data_as_of=points[-1]["date"],
                caveat="زمینهٔ کلان با تاریخ انتشار/مشاهدهٔ خود سری؛ بدون استنباط جهت معامله از یک دادهٔ منفرد.",
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
        reason = "ECB reference rates are not executable market quotes." if series.asset_class == "fx_reference" else "Macro series provide context, not a standalone asset opportunity score."
        return {"score": None, "coverage": 0, "decision": "DATA_ONLY", "why": reason}
    if series.asset_class == "crypto":
        extra = series.extra
        changes = [extra.get(k) for k in ("change_24h", "change_7d", "change_30d")]
        present = [float(v) for v in changes if v is not None]
        market_cap, volume, fdv = extra.get("market_cap"), extra.get("volume_24h"), extra.get("fdv")
        factors: list[tuple[float, float]] = []
        if len(present) >= 2:
            momentum = clamp(50 + statistics.mean(present) * 2)
            factors.append((momentum, .40))
        if len(present) == 3:
            alignment = 100 if all(v > 0 for v in present) else 65 if sum(v > 0 for v in present) == 2 else 35 if sum(v > 0 for v in present) == 1 else 10
            factors.append((alignment, .30))
        if market_cap and volume and market_cap > 0:
            factors.append((clamp((volume / market_cap) * 100 * 10), .20))
        if market_cap and fdv and market_cap > 0:
            ratio = fdv / market_cap
            dilution = 90 if ratio <= 1.1 else 70 if ratio <= 1.5 else 45 if ratio <= 2.5 else 20
            factors.append((dilution, .10))
        coverage = len(factors) / 4
        if coverage < .75:
            return {"score": None, "coverage": round(coverage * 100), "decision": "INSUFFICIENT_DATA", "why": "At least three market-specific factors are required; missing data are not treated as neutral."}
        weight = sum(w for _, w in factors)
        return {"score": round(sum(s * w for s, w in factors) / weight), "coverage": round(coverage * 100), "decision": "WATCH_ONLY", "why": "Preliminary crypto screen: 24h/7d/30d momentum, cross-window alignment, volume/market-cap turnover and FDV/market-cap. No volatility, order-book spread, verified flow or catalyst feed."}

    points = series.observations
    closes = [as_float(p.get("close")) for p in points]
    closes = [v for v in closes if v is not None and v > 0]
    if len(closes) < 60:
        return {"score": None, "coverage": round(len(closes) / 60 * 100), "decision": "INSUFFICIENT_HISTORY", "why": "Fewer than 60 valid observations; no technical rank."}
    last = closes[-1]
    sma20, sma50 = statistics.mean(closes[-20:]), statistics.mean(closes[-50:])
    mom20, mom60 = pct_change(last, closes[-21]), pct_change(last, closes[-61]) if len(closes) > 60 else None
    trend_score = 100 if last > sma20 > sma50 else 75 if last > sma20 and last > sma50 else 50 if last > sma20 or last > sma50 else 20
    momentum_score = clamp(50 + (mom20 or 0) * 2)
    returns = [closes[i] / closes[i - 1] - 1 for i in range(1, len(closes)) if closes[i - 1]]
    factor = math.sqrt(252) if series.asset_class in {"us_equity_etf", "commodity_proxy"} else math.sqrt(52)
    vol = statistics.stdev(returns[-20:]) * factor * 100 if len(returns) >= 20 else None
    vol_score = clamp(100 - (vol or 0) * 1.5)
    last_volume = points[-1].get("volume") if points else None
    volumes = [as_float(p.get("volume")) for p in points[-21:-1]]
    volumes = [v for v in volumes if v is not None and v > 0]
    volume_ratio = last_volume / statistics.mean(volumes) if last_volume and volumes else None
    drawdown = pct_change(last, max(closes[-60:]))
    if series.asset_class in {"us_equity_etf", "commodity_proxy"}:
        factors = [(trend_score, .35), (momentum_score, .25), (vol_score, .20)]
        if volume_ratio is not None:
            factors.append((clamp(50 + (volume_ratio - 1) * 35), .20))
    else:
        # Price-series-only commodity observations are deliberately not treated as a supply/demand thesis.
        factors = [(trend_score, .40), (momentum_score, .35), (vol_score, .25)]
    score = round(sum(s * w for s, w in factors) / sum(w for _, w in factors))
    coverage = round((len(factors) / (4 if series.asset_class == "us_equity_etf" else 3)) * 100)
    decision = "WATCH_ONLY" if score >= 55 else "NO_RANK"
    reason = f"Daily/periodic series: 20-period return {mom20:.1f}%" if mom20 is not None else "Recent price history available."
    return {"score": score, "coverage": coverage, "decision": decision,
            "why": reason + "; technical heuristic only, not calibrated and not a trade instruction.",
            "latest_price": last, "momentum_20": mom20, "momentum_60": mom60, "trend_score": trend_score,
            "volatility_annualized_pct": vol, "drawdown_from_60_period_high_pct": drawdown,
            "volume_ratio_20": volume_ratio}


def stale(series: MarketSeries) -> bool:
    if not series.data_as_of:
        return True
    try:
        age = date.today() - date.fromisoformat(series.data_as_of[:10])
    except ValueError:
        return True
    if series.asset_class == "crypto":
        try:
            stamp = datetime.fromisoformat((series.observed_at or "").replace("Z", "+00:00"))
            return now_utc() - stamp > timedelta(minutes=int(os.getenv("MAX_CRYPTO_AGE_MINUTES", "15")))
        except (ValueError, TypeError):
            return True
    if series.asset_class == "us_equity_etf":
        return age > timedelta(days=int(os.getenv("MAX_EQUITY_AGE_DAYS", "4")))
    if series.asset_class == "commodity_energy":
        return age > timedelta(days=int(os.getenv("MAX_EIA_AGE_DAYS", "14")))
    if series.asset_class == "fx_reference":
        return age > timedelta(days=int(os.getenv("MAX_ECB_AGE_DAYS", "4")))
    if series.asset_class == "macro":
        return age > timedelta(days=int(os.getenv("MAX_FRED_AGE_DAYS", "10")))
    return False


def ensure_db(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path)
    db.execute("""CREATE TABLE IF NOT EXISTS ideas (
        id INTEGER PRIMARY KEY, asset_key TEXT NOT NULL, symbol TEXT NOT NULL,
        asset_class TEXT NOT NULL, source TEXT NOT NULL, data_as_of TEXT NOT NULL,
        recorded_at TEXT NOT NULL, price REAL NOT NULL, technical_score REAL,
        factor_coverage_pct INTEGER NOT NULL, decision TEXT NOT NULL, thesis TEXT NOT NULL,
        invalidation TEXT NOT NULL, UNIQUE(asset_key, data_as_of)
    )""")
    db.execute("""CREATE TABLE IF NOT EXISTS evaluations (
        id INTEGER PRIMARY KEY, idea_id INTEGER NOT NULL REFERENCES ideas(id),
        checkpoint_days INTEGER NOT NULL, evaluated_at TEXT NOT NULL,
        observed_at TEXT NOT NULL, price REAL NOT NULL, return_pct REAL NOT NULL,
        UNIQUE(idea_id, checkpoint_days)
    )""")
    db.commit()
    return db


def price_now(series: MarketSeries) -> float | None:
    if series.asset_class == "crypto":
        return as_float(series.observations[-1].get("close")) if series.observations else None
    return as_float(series.observations[-1].get("close")) if series.observations else None


def record_and_evaluate(db: sqlite3.Connection, series_list: list[MarketSeries], scores: dict[str, dict[str, Any]]) -> None:
    timestamp = iso()
    current = {s.key: (s, price_now(s)) for s in series_list}
    for s in series_list:
        price = price_now(s)
        score = scores.get(s.key, {})
        if price is not None and s.data_as_of:
            db.execute("""INSERT OR IGNORE INTO ideas
            (asset_key,symbol,asset_class,source,data_as_of,recorded_at,price,technical_score,factor_coverage_pct,decision,thesis,invalidation)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""", (
                s.key, s.symbol, s.asset_class, s.provider, s.data_as_of, timestamp,
                price, score.get("score"), score.get("coverage", 0), score.get("decision", "NO_RANK"),
                score.get("why", "No scored evidence."),
                "Reassess if the next observation contradicts the recorded thesis; no price stop is inferred.",
            ))
    pending = db.execute("SELECT id,asset_key,data_as_of,price FROM ideas").fetchall()
    for idea_id, key, origin, origin_price in pending:
        series_price = current.get(key)
        if not series_price or series_price[1] is None:
            continue
        s, current_price = series_price
        try:
            days = (date.fromisoformat(s.data_as_of[:10]) - date.fromisoformat(origin[:10])).days
        except (ValueError, TypeError):
            continue
        if days < 0:
            continue
        tolerance_days = {1: 1, 7: 2, 30: 4, 90: 10, 365: 21}
        for checkpoint, tolerance in tolerance_days.items():
            exists = db.execute("SELECT 1 FROM evaluations WHERE idea_id=? AND checkpoint_days=?", (idea_id, checkpoint)).fetchone()
            if not exists and checkpoint <= days <= checkpoint + tolerance:
                db.execute("INSERT OR IGNORE INTO evaluations(idea_id,checkpoint_days,evaluated_at,observed_at,price,return_pct) VALUES(?,?,?,?,?,?)",
                           (idea_id, checkpoint, timestamp, s.data_as_of, current_price, (current_price / origin_price - 1) * 100))
    db.commit()


def telegram_report(series_list: list[MarketSeries], errors: list[str], scores: dict[str, dict[str, Any]]) -> str:
    generated = now_utc()
    tehran = generated.astimezone(ZoneInfo("Asia/Tehran"))
    lines = [f"🌐 GRIOS | رادار فرصت‌ها | {tehran.strftime('%Y-%m-%d %H:%M')} تهران"]
    classes = {
        "crypto": "کریپتو اسپات",
        "us_equity_etf": "سهام و ETF آمریکا",
        "commodity_proxy": "ETFهای نمایندهٔ کالا (نه قرارداد کالا)",
        "commodity_energy": "سری‌های انرژی EIA",
        "fx_reference": "نرخ مرجع فارکس ECB",
        "macro": "زمینه کلان FRED",
    }
    lines.append("📡 پوشش: " + " | ".join(f"{label}: {sum(s.asset_class == key for s in series_list)}" for key, label in classes.items()))
    ranked = []
    for s in series_list:
        score = scores.get(s.key, {})
        if stale(s):
            continue
        if score.get("score") is not None and score.get("decision") == "WATCH_ONLY":
            ranked.append((score["score"], s, score))
    ranked.sort(key=lambda x: x[0], reverse=True)
    if ranked:
        lines.append("\n🔎 نامزدهای پایش تکنیکال — امتیاز آزمایشی، نه سیگنال خرید/فروش")
        for rank, (value, s, score) in enumerate(ranked[:5], 1):
            price = price_now(s)
            lines.append(f"\n{rank}. {s.symbol} | امتیاز آزمایشی {value}/100 | پوشش معیارها {score['coverage']}% | {s.asset_class}")
            lines.append(f"   قیمت/آخرین مشاهده: {price:g} {s.currency} | تاریخ داده: {s.data_as_of} | منبع: {s.provider} ({s.feed_class})")
            lines.append(f"   چرا: {score['why']}")
            if s.asset_class == "crypto":
                extra = s.extra
                momentum = "/".join("—" if extra.get(k) is None else f"{extra[k]:+.1f}%" for k in ("change_24h", "change_7d", "change_30d"))
                turnover = (extra["volume_24h"] / extra["market_cap"] * 100) if extra.get("volume_24h") and extra.get("market_cap") else None
                dilution = (extra["fdv"] / extra["market_cap"]) if extra.get("fdv") and extra.get("market_cap") else None
                details = [f"بازده ۲۴س/۷ر/۳۰ر: {momentum}"]
                if turnover is not None:
                    details.append(f"گردش حجم/ارزش بازار: {turnover:.1f}%")
                if dilution is not None:
                    details.append(f"FDV/ارزش بازار: {dilution:.2f}x")
                lines.append("   دادهٔ امتیاز: " + " | ".join(details))
            else:
                evidence = []
                if score.get("momentum_20") is not None:
                    evidence.append(f"بازده ۲۰دوره: {score['momentum_20']:+.1f}%")
                if score.get("momentum_60") is not None:
                    evidence.append(f"۶۰دوره: {score['momentum_60']:+.1f}%")
                if score.get("volatility_annualized_pct") is not None:
                    evidence.append(f"نوسان سالانه‌شده: {score['volatility_annualized_pct']:.1f}%")
                if score.get("drawdown_from_60_period_high_pct") is not None:
                    evidence.append(f"از سقف ۶۰دوره: {score['drawdown_from_60_period_high_pct']:.1f}%")
                if score.get("volume_ratio_20") is not None:
                    evidence.append(f"حجم/میانگین ۲۰دوره: {score['volume_ratio_20']:.2f}x")
                if evidence:
                    lines.append("   دادهٔ امتیاز: " + " | ".join(evidence))
            if s.asset_class == "crypto":
                invalidation = "بازبینی در صورت منفی‌شدن بازده ۷روزه یا ازبین‌رفتن هم‌جهتی ۲۴ساعت/۷روز/۳۰روز؛ تاریخچهٔ OHLCV نداریم."
            else:
                invalidation = "بازبینی در صورت بسته‌شدن زیر میانگین ۲۰ یا ۵۰ دوره؛ حد قیمت/هدف تعیین نشده."
            lines.append(f"   شرط ابطال/بازبینی: {invalidation}")
            if s.caveat:
                lines.append(f"   ریسک: {s.caveat}")
    else:
        lines.append("\n⏸️ نامزد رتبه‌پذیر تازه ندارم؛ دادهٔ معتبر/کافی در پنجرهٔ تازگی موجود نیست.")
    fx = [s for s in series_list if s.asset_class == "fx_reference" and not stale(s)]
    if fx:
        lines.append("\n💱 فارکس: فقط نرخ‌های مرجع روزانهٔ ECB؛ به‌دلیل نبود bid/ask، حجم، carry و quote قابل معامله، جهت Buy/Sell رتبه‌بندی نشد.")
    macro = [s for s in series_list if s.asset_class == "macro" and not stale(s)]
    if macro:
        macro_parts = [f"{s.symbol} {price_now(s):g}{s.currency} ({s.data_as_of})" for s in macro if price_now(s) is not None]
        by_symbol = {s.symbol: price_now(s) for s in macro}
        if by_symbol.get("DGS10") is not None and by_symbol.get("DGS2") is not None:
            macro_parts.append(f"10Y-2Y: {by_symbol['DGS10'] - by_symbol['DGS2']:+.2f}pp")
        lines.append("\n🧭 زمینهٔ کلان — FRED: " + " | ".join(macro_parts) + "؛ دادهٔ زمینه‌ای است، نه محرک قطعی بازار.")
    if errors:
        lines.append("\n⚠️ فیدهای ناقص: " + "؛ ".join(errors[:5]))
    lines.append("\n🧭 تصمیم CIO: فقط WATCH؛ خبر/کاتالیزور، دادهٔ بنیادی چندبازاری، جریان پولِ منتسب و نسبت ریسک/بازده هنوز متصل نیست. هیچ سفارش یا تخصیص سرمایه صادر نمی‌شود.")
    lines.append("این خروجی پژوهشی و مبتنی بر امتیاز تکنیکال آزمایشی است؛ بازدهی آن کالیبره/اعتبارسنجی نشده است.")
    # Telegram message size safety; report is intentionally kept compact.
    return "\n".join(lines)[:3900]


def main() -> int:
    parser = argparse.ArgumentParser(description="GRIOS/OpenBB research-only opportunity scanner")
    parser.add_argument("--watchlist", default=str(ROOT / "watchlist.json"))
    parser.add_argument("--out", default=os.getenv("REPORT_DIR", "reports"))
    parser.add_argument("--db", default=os.getenv("JOURNAL_PATH", "data/opportunities.sqlite3"))
    parser.add_argument("--skip-openbb", action="store_true", help="run only the existing GRIOS crypto Data Hub connector")
    args = parser.parse_args()
    watchlist = load_watchlist(Path(args.watchlist))
    series: list[MarketSeries] = []
    errors: list[str] = []
    crypto, crypto_error = fetch_crypto(os.getenv("GRIOS_DATA_HUB_URL"), int(os.getenv("MAX_CRYPTO_AGE_MINUTES", "15")), watchlist["crypto_symbols"])
    series.extend(crypto)
    if crypto_error:
        errors.append(crypto_error)

    if not args.skip_openbb:
        try:
            obb = get_openbb()
            equities, equity_errors = fetch_equity(obb, watchlist["us_equities_etfs"])
            proxies, proxy_errors = fetch_equity(obb, watchlist["commodity_etf_proxies"], proxy=True)
            fx, fx_errors = fetch_fx_reference(obb, watchlist["fx_reference_pairs"])
            energy, energy_errors = fetch_energy(obb, bool(os.getenv("EIA_API_KEY", "").strip()))
            macro, macro_errors = fetch_macro(obb, bool(os.getenv("FRED_API_KEY", "").strip()))
            series.extend(equities + proxies + fx + energy + macro)
            errors.extend(equity_errors + proxy_errors + fx_errors + energy_errors + macro_errors)
        except ImportError:
            errors.append("OpenBB V5 نصب نیست؛ فقط اتصال GRIOS Data Hub قابل استفاده است.")
        except Exception as exc:
            errors.append(f"راه‌اندازی OpenBB ناموفق بود ({type(exc).__name__}); فیدهای غیرکریپتو حذف شدند.")

    scores = {s.key: market_score(s) for s in series}
    output = telegram_report(series, errors, scores)
    output_dir = Path(args.out)
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = now_utc().strftime("%Y%m%dT%H%M%SZ")
    report_path = output_dir / f"grios-{stamp}.txt"
    report_path.write_text(output + "\n", encoding="utf-8")
    (output_dir / "latest.txt").write_text(output + "\n", encoding="utf-8")
    db = ensure_db(Path(args.db))
    record_and_evaluate(db, series, scores)
    db.close()
    print(output)
    print(f"\nSaved: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
