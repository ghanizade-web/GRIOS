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
from report_formatting import social_footer_lines

API_ROOT = "https://api.eia.gov/v2/seriesid"
USER_AGENT = "GRIOS-Research/15.0"

EIA_SERIES = [
    {
        "series_id": "PET.WCESTUS1.W",
        "symbol": "EIA_CRUDE_STOCKS",
        "name_en": "U.S. Commercial Crude Oil Stocks (Excluding SPR)",
        "name_fa": "موجودی تجاری نفت خام آمریکا (بدون ذخایر راهبردی)",
        "source_url": "https://www.eia.gov/dnav/pet/hist/LeafHandler.ashx?n=PET&s=WCESTUS1&f=W",
        "units": "thousand barrels",
        "value_kind": "stock",
        "value_format": "integer",
    },
    {
        "series_id": "PET.WGTSTUS1.W",
        "symbol": "EIA_GASOLINE_STOCKS",
        "name_en": "U.S. Ending Stocks of Total Motor Gasoline",
        "name_fa": "موجودی بنزین موتور آمریکا",
        "source_url": "https://www.eia.gov/dnav/pet/hist/LeafHandler.ashx?n=PET&s=WGTSTUS1&f=W",
        "units": "thousand barrels",
        "value_kind": "stock",
        "value_format": "integer",
    },
    {
        "series_id": "PET.WDISTUS1.W",
        "symbol": "EIA_DISTILLATE_STOCKS",
        "name_en": "U.S. Ending Stocks of Distillate Fuel Oil",
        "name_fa": "موجودی سوخت‌های تقطیری آمریکا",
        "source_url": "https://www.eia.gov/dnav/pet/hist/LeafHandler.ashx?n=PET&s=WDISTUS1&f=W",
        "units": "thousand barrels",
        "value_kind": "stock",
        "value_format": "integer",
    },
    {
        "series_id": "PET.WCRFPUS2.W",
        "symbol": "EIA_CRUDE_PRODUCTION",
        "name_en": "U.S. Field Production of Crude Oil",
        "name_fa": "تولید داخلی نفت خام آمریکا",
        "source_url": "https://www.eia.gov/dnav/pet/hist/LeafHandler.ashx?n=PET&s=WCRFPUS2&f=W",
        "units": "thousand barrels per day",
        "value_kind": "supply_flow",
        "value_format": "integer",
    },
    {
        "series_id": "PET.WCRIMUS2.W",
        "symbol": "EIA_CRUDE_IMPORTS",
        "name_en": "U.S. Imports of Crude Oil",
        "name_fa": "واردات نفت خام آمریکا",
        "source_url": "https://www.eia.gov/dnav/pet/hist/LeafHandler.ashx?n=PET&s=WCRIMUS2&f=W",
        "units": "thousand barrels per day",
        "value_kind": "supply_flow",
        "value_format": "integer",
    },
    {
        "series_id": "PET.WCREXUS2.W",
        "symbol": "EIA_CRUDE_EXPORTS",
        "name_en": "U.S. Exports of Crude Oil",
        "name_fa": "صادرات نفت خام آمریکا",
        "source_url": "https://www.eia.gov/dnav/pet/hist/LeafHandler.ashx?n=PET&s=WCREXUS2&f=W",
        "units": "thousand barrels per day",
        "value_kind": "supply_flow",
        "value_format": "integer",
    },
    {
        "series_id": "PET.WCRRIUS2.W",
        "symbol": "EIA_REFINERY_CRUDE_INPUTS",
        "name_en": "U.S. Refiner Net Input of Crude Oil",
        "name_fa": "خوراک نفت خام ورودی به پالایشگاه‌های آمریکا",
        "source_url": "https://www.eia.gov/dnav/pet/hist/LeafHandler.ashx?n=PET&s=WCRRIUS2&f=W",
        "units": "thousand barrels per day",
        "value_kind": "demand_flow",
        "value_format": "integer",
    },
    {
        "series_id": "PET.WPULEUS3.W",
        "symbol": "EIA_REFINERY_UTILIZATION",
        "name_en": "U.S. Percent Utilization of Refinery Operable Capacity",
        "name_fa": "درصد بهره‌برداری از ظرفیت عملیاتی پالایشگاه‌های آمریکا",
        "source_url": "https://www.eia.gov/dnav/pet/hist/LeafHandler.ashx?n=PET&s=WPULEUS3&f=W",
        "units": "percent",
        "value_kind": "capacity_rate",
        "value_format": "decimal",
    },
    {
        "series_id": "PET.WRPUPUS2.W",
        "symbol": "EIA_TOTAL_PRODUCT_SUPPLIED",
        "name_en": "U.S. Product Supplied of Petroleum Products (Total)",
        "name_fa": "کل فرآورده‌های نفتی عرضه‌شده به بازار آمریکا",
        "source_url": "https://www.eia.gov/dnav/pet/hist/LeafHandler.ashx?n=PET&s=WRPUPUS2&f=W",
        "units": "thousand barrels per day",
        "value_kind": "demand_proxy",
        "value_format": "integer",
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


def _validate_units(actual: Any, expected: str, series_id: str) -> str:
    if actual is None or not str(actual).strip():
        return expected
    normalized_actual = " ".join(str(actual).casefold().split())
    normalized_expected = " ".join(expected.casefold().split())
    aliases = {
        "thousand barrels": {"thousand barrels", "thousand barrels "},
        "thousand barrels per day": {
            "thousand barrels per day",
            "thousand barrels per day ",
        },
        "percent": {"percent", "%"},
    }
    allowed = aliases.get(normalized_expected, {normalized_expected})
    if normalized_actual not in allowed:
        raise ValueError(f"Unexpected EIA unit for {series_id}.")
    return expected


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
    units = _validate_units(
        rows[0].get("value-units") if rows else None,
        definition["units"],
        series_id,
    )
    values = [item["value"] for item in observations]
    latest = observations[-1]
    previous = observations[-2]
    weekly_change = latest["value"] - previous["value"]
    percentile = historical_percentile(values)
    observed_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return {
        "key": f"eia:weekly_petroleum:{series_id}",
        "symbol": definition["symbol"],
        "name": definition["name_en"],
        "asset_class": "commodity_energy",
        "instrument": "weekly petroleum supply and disposition",
        "provider": "EIA",
        "feed_class": "Official EIA Weekly Petroleum Status Report series",
        "units": units,
        "value_kind": definition["value_kind"],
        "observed_at": observed_at,
        "data_as_of": latest["date"],
        "caveat": (
            "Weekly U.S. petroleum balance estimate, not a real-time transaction flow. "
            "Weekly production and export figures are estimates; EIA notes that production "
            "is estimated from monthly data and exports are not collected directly in the "
            "weekly survey. No market consensus or causal price-direction signal is supplied."
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
            "source_units": units,
            "value_kind": definition["value_kind"],
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
    kind_labels = {
        "stock": "موجودی",
        "supply_flow": "جریان عرضه",
        "demand_flow": "خوراک پالایشگاه",
        "capacity_rate": "نرخ بهره‌برداری",
        "demand_proxy": "شاخص تقاضای ضمنی",
    }
    lines = [
        "🛢️ گزارش هفتگی تراز عرضه و تقاضای نفت و فرآورده‌های آمریکا",
        f"🕒 زمان دریافت داده: {generated_at}",
        f"📊 وضعیت: {status_labels.get(status, status)}",
        f"📚 پوشش: {len(series)} از {len(EIA_SERIES)} سری",
        "━━━━━━━━━━━━━━━━━━━━",
    ]
    if series:
        for index, item in enumerate(series, 1):
            extra = item["extra"]
            change = extra.get("weekly_change")
            change_text = "ناموجود" if change is None else f"{change:+,.1f}"
            change_pct = extra.get("weekly_change_pct")
            pct_text = "ناموجود" if change_pct is None else f"{change_pct:+.2f}٪"
            value = extra["latest_value"]
            value_text = f"{value:,.1f}" if item.get("units") == "percent" else f"{value:,.0f}"
            lines.extend([
                f"{index}) {extra.get('name_fa', item['symbol'])}",
                f"🏷 نوع داده: {kind_labels.get(item.get('value_kind'), 'سری هفتگی')}",
                f"📦 آخرین مقدار: {value_text} {item.get('units', '')}",
                f"🔁 تغییر هفتگی: {change_text} ({pct_text})",
                f"📈 صدک تاریخی خام: {extra['historical_percentile']}٪",
                f"🗓 تاریخ مشاهده: {item['data_as_of']}",
                f"🔗 منبع رسمی EIA: {extra['source_url']}",
                "──────────────",
            ])
    else:
        lines.append("در این اجرا داده معتبر دریافت نشد؛ از مقادیر قبلی به‌عنوان داده تازه استفاده نشده است.")
    if publish_result is not None:
        lines.append(f"💾 وضعیت ذخیره‌سازی: {publish_result.get('status', 'نامشخص')}")
        lines.append(f"📥 تعداد رکورد پذیرفته‌شده: {publish_result.get('accepted', 0)}")
    lines.extend([
        "⚠️ صدک‌ها بر اساس تاریخچه دریافت‌شده و بدون تعدیل فصلی محاسبه شده‌اند؛ مقایسه خام بین فصل‌ها می‌تواند گمراه‌کننده باشد.",
        "⚠️ تولید و صادرات هفتگی برآوردی‌اند؛ واردات و خوراک پالایشگاه نیز باید در کنار تغییر موجودی و عرضه فرآورده‌ها تفسیر شوند.",
        "🧭 این داده‌ها اجماع تحلیلگران، غافلگیری نسبت به انتظار بازار یا اثر علّی بر قیمت را ارائه نمی‌کنند. افزایش یا کاهش یک سری به‌تنهایی سیگنال خریدوفروش نیست.",
    ])
    lines.extend(social_footer_lines())
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
        "schema_version": "1.1",
        "source": "U.S. Energy Information Administration",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "status": status,
        "series_count": len(series),
        "expected_series_count": len(EIA_SERIES),
        "series": series,
        "failures": failures,
        "publish": publish_result,
        "limitations": [
            "Weekly stock levels and supply/demand rates are distinct value types and units.",
            "Weekly U.S. production and export series are estimates, not direct weekly measurements.",
            "Historical percentile is calculated over retrieved raw observations and is not seasonally adjusted.",
            "Publication timestamp, market consensus, actual-versus-consensus surprise, and causal price impact are not supplied by these series.",
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


def exit_code_for_payload(payload: dict[str, Any], *, require_complete: bool = False) -> int:
    status = payload.get("status")
    count = payload.get("series_count", 0)
    expected = payload.get("expected_series_count", len(EIA_SERIES))
    if status in {"FAILED", "NOT_CONFIGURED"}:
        return 1
    if require_complete and (status != "SUCCESS" or count != expected):
        return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch weekly EIA U.S. petroleum supply and disposition.")
    parser.add_argument("--history-limit", type=int, default=260)
    parser.add_argument("--require-complete", action="store_true", help="Exit non-zero unless every configured EIA series is available.")
    parser.add_argument("--output-json", default="reports/eia-petroleum-stocks-latest.json")
    parser.add_argument("--output-text", default="reports/eia-petroleum-stocks-latest.txt")
    args = parser.parse_args()
    payload = run(
        os.getenv("EIA_API_KEY", ""),
        history_limit=args.history_limit,
        output_json=args.output_json,
        output_text=args.output_text,
    )
    print(f"EIA_PETROLEUM_BALANCE: {payload['status']} ({payload['series_count']}/{payload['expected_series_count']} series)")
    return exit_code_for_payload(payload, require_complete=args.require_complete)


if __name__ == "__main__":
    raise SystemExit(main())
