from __future__ import annotations

import argparse
import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from data_coverage import publish_market_series

API_ROOT = "https://api.eia.gov/v2/seriesid"
USER_AGENT = "GRIOS-Research/15.0"

EIA_SERIES = [
    {
        "series_id": "PET.WCESTUS1.W",
        "symbol": "EIA_CRUDE_STOCKS",
        "name_en": "U.S. Commercial Crude Oil Stocks (Excluding SPR)",
        "name_fa": "موجودی تجاری نفت خام آمریکا (بدون ذخایر راهبردی)",
        "source_url": "https://www.eia.gov/dnav/pet/pet_stoc_wstk_a_EPC0_SAX_mbbl_w.htm",
        "units": "thousand barrels",
    },
    {
        "series_id": "PET.WGTSTUS1.W",
        "symbol": "EIA_GASOLINE_STOCKS",
        "name_en": "U.S. Ending Stocks of Total Motor Gasoline",
        "name_fa": "موجودی بنزین موتور آمریکا",
        "source_url": "https://www.eia.gov/opendata/v1/embed.php?series_id=PET.WGTSTUS1.W&type=chart",
        "units": "thousand barrels",
    },
    {
        "series_id": "PET.WDISTUS1.W",
        "symbol": "EIA_DISTILLATE_STOCKS",
        "name_en": "U.S. Ending Stocks of Distillate Fuel Oil",
        "name_fa": "موجودی سوخت‌های تقطیری آمریکا",
        "source_url": "https://www.eia.gov/opendata/v1/embed.php?series_id=PET.WDISTUS1.W&type=chart",
        "units": "thousand barrels",
    },
]


def _finite_number(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("EIA data point has an invalid numeric value.") from exc
    if not math.isfinite(number):
        raise ValueError("EIA data point is not finite.")
    return number


def normalize_observations(rows: Any, *, limit: int = 260) -> list[dict[str, Any]]:
    if not isinstance(rows, list):
        raise ValueError("EIA series response must contain a data array.")
    normalized = []
    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("EIA data point must be an object.")
        period = str(row.get("period") or "")[:10]
        try:
            datetime.strptime(period, "%Y-%m-%d")
        except ValueError as exc:
            raise ValueError("EIA weekly period must use YYYY-MM-DD.") from exc
        if period in seen:
            continue
        seen.add(period)
        normalized.append({"date": period, "value": _finite_number(row.get("value"))})
    normalized.sort(key=lambda item: item["date"])
    return normalized[-limit:]


def historical_percentile(values: list[float]) -> float | None:
    if not values:
        return None
    current = values[-1]
    return round(100.0 * sum(value <= current for value in values) / len(values), 2)


def fetch_series(
    definition: dict[str, str],
    api_key: str,
    *,
    history_limit: int = 260,
    timeout: int = 25,
) -> dict[str, Any]:
    if not api_key.strip():
        raise ValueError("EIA_API_KEY is not configured.")
    if not 2 <= history_limit <= 520:
        raise ValueError("history_limit must be between 2 and 520 weekly observations.")
    series_id = definition["series_id"]
    url = f"{API_ROOT}/{series_id}/data/"
    params = [
        ("api_key", api_key),
        ("frequency", "weekly"),
        ("data[0]", "value"),
        ("sort[0][column]", "period"),
        ("sort[0][direction]", "desc"),
        ("length", str(history_limit)),
    ]
    response = httpx.get(
        url,
        params=params,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        timeout=timeout,
    )
    response.raise_for_status()
    payload = response.json()
    response_data = payload.get("response") if isinstance(payload, dict) else None
    rows = response_data.get("data") if isinstance(response_data, dict) else None
    observations = normalize_observations(rows, limit=history_limit)
    if len(observations) < 2:
        raise ValueError(f"EIA returned fewer than two weekly observations for {series_id}.")
    units = None
    if rows:
        units = rows[0].get("value-units")
    if units and str(units).casefold() not in {"thousand barrels", "thousand barrels "}:
        raise ValueError(f"Unexpected EIA unit for {series_id}.")
    values = [item["value"] for item in observations]
    latest = observations[-1]
    previous = observations[-2]
    weekly_change = latest["value"] - previous["value"]
    percentile = historical_percentile(values)
    observed_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return {
        "key": f"eia:weekly_inventory:{series_id}",
        "symbol": definition["symbol"],
        "name": definition["name_en"],
        "asset_class": "commodity_energy",
        "instrument": "weekly petroleum inventory",
        "provider": "EIA",
        "feed_class": "Weekly U.S. petroleum inventory; official EIA series",
        "currency": "thousand barrels",
        "observed_at": observed_at,
        "data_as_of": latest["date"],
        "caveat": (
            "Weekly stock level, not a real-time flow. The series does not provide market consensus, "
            "release-time metadata, or a causal price-direction signal."
        ),
        "observations": observations,
        "extra": {
            "series_id": series_id,
            "name_fa": definition["name_fa"],
            "latest_value": latest["value"],
            "previous_value": previous["value"],
            "weekly_change": weekly_change,
            "weekly_change_pct": (
                weekly_change / previous["value"] * 100 if previous["value"] else None
            ),
            "historical_percentile": percentile,
            "history_observations": len(observations),
            "source_url": definition["source_url"],
            "source_units": units or definition["units"],
            "publication_timestamp": None,
            "consensus": None,
            "surprise": None,
        },
    }


def build_persian_report(
    series: list[dict[str, Any]],
    *,
    generated_at: str,
    publish_result: dict[str, Any] | None = None,
    status: str = "SUCCESS",
) -> str:
    status_labels = {
        "SUCCESS": "داده‌های موجود دریافت شدند",
        "PARTIAL": "دریافت بخشی از سری‌ها ناموفق بود",
        "NOT_CONFIGURED": "کلید دسترسی EIA تنظیم نشده است",
        "FAILED": "دریافت داده با خطا مواجه شد",
    }
    lines = [
        "🛢️ گزارش هفتگی موجودی نفت و فرآورده‌های آمریکا",
        f"🕒 زمان دریافت داده: {generated_at}",
        f"📊 وضعیت: {status_labels.get(status, status)}",
        "━━━━━━━━━━━━━━━━━━━━",
    ]
    if series:
        for index, item in enumerate(series, 1):
            extra = item["extra"]
            change = extra.get("weekly_change")
            change_text = "ناموجود" if change is None else f"{change:+,.0f} هزار بشکه"
            change_pct = extra.get("weekly_change_pct")
            pct_text = "ناموجود" if change_pct is None else f"{change_pct:+.2f}٪"
            lines.extend([
                f"{index}) {extra.get('name_fa', item['symbol'])}",
                f"📦 سطح موجودی: {extra['latest_value']:,.0f} هزار بشکه",
                f"🔁 تغییر هفتگی: {change_text} ({pct_text})",
                f"📈 صدک تاریخی در تاریخچه دریافت‌شده: {extra['historical_percentile']}٪",
                f"🗓 تاریخ آخرین مشاهده: {item['data_as_of']}",
                f"🔗 منبع رسمی EIA: {extra['source_url']}",
                "──────────────",
            ])
    else:
        lines.append("در این اجرا داده معتبر موجودی دریافت نشد؛ از مقدار قبلی به‌عنوان داده تازه استفاده نشده است.")
    if publish_result is not None:
        lines.append(f"💾 وضعیت ذخیره‌سازی: {publish_result.get('status', 'نامشخص')}")
        lines.append(f"📥 تعداد رکورد پذیرفته‌شده: {publish_result.get('accepted', 0)}")
    lines.extend([
        "⚠️ این ارقام سطح موجودی هفتگی هستند؛ نه میزان خریدوفروش لحظه‌ای. ساعت انتشار، اجماع تحلیلگران و غافلگیری نسبت به انتظار بازار در این منبع موجود نیست.",
        "🧭 کاهش یا افزایش موجودی به‌تنهایی جهت قیمت نفت را تعیین نمی‌کند؛ تولید، واردات، پالایش، صادرات، تقاضا و وضعیت ذخایر باید هم‌زمان بررسی شوند.",
    ])
    return "\n".join(lines)


def run(
    api_key: str,
    *,
    history_limit: int = 260,
    output_json: str | Path = "reports/eia-petroleum-stocks-latest.json",
    output_text: str | Path = "reports/eia-petroleum-stocks-latest.txt",
    source_revision: str | None = None,
) -> dict[str, Any]:
    series = []
    failures = []
    if not api_key.strip():
        status = "NOT_CONFIGURED"
    else:
        for definition in EIA_SERIES:
            try:
                series.append(fetch_series(definition, api_key, history_limit=history_limit))
            except Exception as exc:
                failures.append({
                    "series_id": definition["series_id"],
                    "error_type": type(exc).__name__,
                })
        status = "SUCCESS" if not failures else ("PARTIAL" if series else "FAILED")

    publish_result = (
        publish_market_series(series, source_revision or os.getenv("GITHUB_SHA", "UNKNOWN"))
        if series else {"status": "NO_DATA", "accepted": 0, "error": None}
    )
    payload = {
        "schema_version": "1.0",
        "source": "U.S. Energy Information Administration",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "status": status,
        "series_count": len(series),
        "series": series,
        "failures": failures,
        "publish": publish_result,
        "limitations": [
            "Weekly inventory observations are stock levels, not transaction-level flows.",
            "Publication timestamp, market consensus, actual-versus-consensus surprise, and causal price impact are not supplied by these series.",
            "Historical percentile is calculated over the retrieved observations; it is not a seasonally adjusted percentile.",
        ],
    }
    json_path = Path(output_json)
    text_path = Path(output_text)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    text_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    text_path.write_text(
        build_persian_report(
            series,
            generated_at=payload["generated_at"],
            publish_result=publish_result,
            status=status,
        ) + "\n",
        encoding="utf-8",
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch weekly EIA U.S. petroleum inventories.")
    parser.add_argument("--history-limit", type=int, default=260)
    parser.add_argument("--output-json", default="reports/eia-petroleum-stocks-latest.json")
    parser.add_argument("--output-text", default="reports/eia-petroleum-stocks-latest.txt")
    args = parser.parse_args()
    payload = run(
        os.getenv("EIA_API_KEY", ""),
        history_limit=args.history_limit,
        output_json=args.output_json,
        output_text=args.output_text,
    )
    print(f"EIA_INVENTORY: {payload['status']} ({payload['series_count']} series)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
