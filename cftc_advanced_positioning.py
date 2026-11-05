from __future__ import annotations

import argparse
import json
import math
import os
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from data_coverage import publish_market_series
from report_formatting import social_footer_lines

API_ROOT = "https://publicreporting.cftc.gov/resource"
DATASETS = {
    "DISAGGREGATED": {
        "dataset_id": "72hh-3qpy",
        "report_type": "Disaggregated Futures Only",
        "source_url": "https://publicreporting.cftc.gov/Commitments-of-Traders/Disaggregated-Futures-Only/72hh-3qpy",
        "fields": [
            "id", "market_and_exchange_names", "report_date_as_yyyy_mm_dd",
            "cftc_contract_market_code", "open_interest_all",
            "prod_merc_positions_long", "prod_merc_positions_short",
            "swap_positions_long_all", "swap__positions_short_all",
            "m_money_positions_long_all", "m_money_positions_short_all",
            "other_rept_positions_long", "other_rept_positions_short",
            "nonrept_positions_long_all", "nonrept_positions_short_all",
        ],
        "categories": {
            "producer_merchant": {
                "label_fa": "تولیدکنندگان و بازرگانان",
                "long": "prod_merc_positions_long",
                "short": "prod_merc_positions_short",
            },
            "swap_dealer": {
                "label_fa": "معامله‌گران سوآپ",
                "long": "swap_positions_long_all",
                "short": "swap__positions_short_all",
            },
            "managed_money": {
                "label_fa": "مدیریت‌کنندگان سرمایه و صندوق‌های سفته‌باز",
                "long": "m_money_positions_long_all",
                "short": "m_money_positions_short_all",
            },
            "other_reportables": {
                "label_fa": "سایر معامله‌گران بزرگ گزارش‌شونده",
                "long": "other_rept_positions_long",
                "short": "other_rept_positions_short",
            },
            "nonreportable": {
                "label_fa": "موقعیت‌های غیرگزارش‌شونده",
                "long": "nonrept_positions_long_all",
                "short": "nonrept_positions_short_all",
            },
        },
    },
    "TFF": {
        "dataset_id": "gpe5-46if",
        "report_type": "Traders in Financial Futures — Futures Only",
        "source_url": "https://publicreporting.cftc.gov/Commitments-of-Traders/TFF-Futures-Only/gpe5-46if",
        "fields": [
            "id", "market_and_exchange_names", "report_date_as_yyyy_mm_dd",
            "cftc_contract_market_code", "open_interest_all",
            "dealer_positions_long_all", "dealer_positions_short_all",
            "asset_mgr_positions_long", "asset_mgr_positions_short",
            "lev_money_positions_long", "lev_money_positions_short",
            "other_rept_positions_long", "other_rept_positions_short",
            "nonrept_positions_long_all", "nonrept_positions_short_all",
        ],
        "categories": {
            "dealer_intermediary": {
                "label_fa": "معامله‌گران و واسطه‌های مالی (Dealer)",
                "long": "dealer_positions_long_all",
                "short": "dealer_positions_short_all",
            },
            "asset_manager": {
                "label_fa": "مدیران دارایی و نهادهای سرمایه‌گذاری",
                "long": "asset_mgr_positions_long",
                "short": "asset_mgr_positions_short",
            },
            "leveraged_funds": {
                "label_fa": "صندوق‌های اهرمی و سفته‌بازان حرفه‌ای",
                "long": "lev_money_positions_long",
                "short": "lev_money_positions_short",
            },
            "other_reportables": {
                "label_fa": "سایر معامله‌گران بزرگ گزارش‌شونده",
                "long": "other_rept_positions_long",
                "short": "other_rept_positions_short",
            },
            "nonreportable": {
                "label_fa": "موقعیت‌های غیرگزارش‌شونده",
                "long": "nonrept_positions_long_all",
                "short": "nonrept_positions_short_all",
            },
        },
    },
}


def _number(value: Any, field: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid numeric CFTC field: {field}") from exc
    if not math.isfinite(number) or number < 0:
        raise ValueError(f"Invalid numeric CFTC field: {field}")
    return number


def positioning_stats(values: list[float]) -> dict[str, float | None]:
    if not values:
        return {"percentile": None, "z_score": None}
    current = values[-1]
    percentile = 100.0 * sum(value <= current for value in values) / len(values)
    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values) / len(values)
    stddev = math.sqrt(variance)
    z_score = (current - mean) / stddev if stddev else 0.0
    return {"percentile": round(percentile, 2), "z_score": round(z_score, 4)}


def normalize_rows(
    rows: Any,
    *,
    contract_code: str,
    report_type: str,
) -> list[dict[str, Any]]:
    if report_type not in DATASETS:
        raise ValueError("Unsupported CFTC report type.")
    if not isinstance(rows, list):
        raise ValueError("CFTC response must be a JSON array.")
    categories = DATASETS[report_type]["categories"]
    normalized = []
    seen_dates: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("CFTC row must be an object.")
        if str(row.get("cftc_contract_market_code") or "").strip() != contract_code:
            raise ValueError("CFTC response contains a different contract market code.")
        report_date = str(row.get("report_date_as_yyyy_mm_dd") or "")[:10]
        try:
            datetime.strptime(report_date, "%Y-%m-%d")
        except ValueError as exc:
            raise ValueError("CFTC row has an invalid report date.") from exc
        if report_date in seen_dates:
            continue
        seen_dates.add(report_date)
        item: dict[str, Any] = {
            "report_date": report_date,
            "market": str(row.get("market_and_exchange_names") or ""),
            "contract_market_code": contract_code,
            "open_interest": _number(row.get("open_interest_all"), "open_interest_all"),
            "categories": {},
        }
        for category, fields in categories.items():
            long_value = _number(row.get(fields["long"]), fields["long"])
            short_value = _number(row.get(fields["short"]), fields["short"])
            item["categories"][category] = {
                "long": long_value,
                "short": short_value,
                "net": long_value - short_value,
            }
        normalized.append(item)
    return sorted(normalized, key=lambda item: item["report_date"])


def fetch_contract(
    contract: dict[str, str],
    *,
    history_limit: int = 260,
    timeout: int = 30,
) -> list[dict[str, Any]]:
    report_type = str(contract.get("report_type") or "").upper()
    if report_type not in DATASETS:
        raise ValueError("Watchlist report_type must be DISAGGREGATED or TFF.")
    code = str(contract.get("contract_market_code") or "").strip()
    market_label = str(contract.get("market") or "").strip()
    if not code or not code.isalnum() or len(code) > 12 or not market_label:
        raise ValueError("Each CFTC item requires market and alphanumeric contract_market_code.")
    if not 2 <= history_limit <= 520:
        raise ValueError("history_limit must be between 2 and 520 weekly observations.")
    dataset = DATASETS[report_type]
    query = {
        "$select": ",".join(dataset["fields"]),
        "$where": f"cftc_contract_market_code='{code}'",
        "$order": "report_date_as_yyyy_mm_dd DESC",
        "$limit": str(history_limit),
    }
    url = f"{API_ROOT}/{dataset['dataset_id']}.json?{urllib.parse.urlencode(query)}"
    request = urllib.request.Request(
        url,
        headers={"Accept": "application/json", "User-Agent": "GRIOS-Research/15.0"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
    rows = normalize_rows(payload, contract_code=code, report_type=report_type)
    if not rows:
        raise ValueError(f"No CFTC {report_type} observations for {market_label} ({code}).")
    return rows[-history_limit:]


def build_market_series(
    contract: dict[str, str],
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    report_type = str(contract["report_type"]).upper()
    dataset = DATASETS[report_type]
    latest = rows[-1]
    previous = rows[-2] if len(rows) > 1 else None
    category_summaries = {}
    observations = []
    for category, definition in dataset["categories"].items():
        values = [row["categories"][category]["net"] for row in rows]
        current = latest["categories"][category]
        prior = previous["categories"][category] if previous else None
        stats = positioning_stats(values)
        category_summaries[category] = {
            "label_fa": definition["label_fa"],
            "long": current["long"],
            "short": current["short"],
            "net": current["net"],
            "weekly_net_change": current["net"] - prior["net"] if prior else None,
            "net_as_pct_open_interest": (
                round(current["net"] / latest["open_interest"] * 100, 2) if latest["open_interest"] else None
            ),
            "historical_percentile": stats["percentile"],
            "historical_z_score": stats["z_score"],
            "lookback_observations": len(rows),
        }
    for row in rows:
        point = {"date": row["report_date"], "open_interest": row["open_interest"]}
        point.update({
            f"{category}_net": values["net"]
            for category, values in row["categories"].items()
        })
        observations.append(point)

    observed_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    code = str(contract["contract_market_code"])
    return {
        "key": f"cftc:{report_type.lower()}_futures_only:{code}",
        "symbol": str(contract.get("symbol") or code).upper(),
        "name": latest["market"] or contract["market"],
        "asset_class": "futures_positioning",
        "instrument": dataset["report_type"],
        "provider": "CFTC",
        "feed_class": "Weekly regulatory positioning disclosure; Tuesday report date",
        "currency": "contracts",
        "observed_at": observed_at,
        "data_as_of": latest["report_date"],
        "caveat": (
            "Weekly CFTC positions are exposures reported as of Tuesday, not transaction records or real-time capital flows. "
            "Trader classifications are CFTC categories, not named funds or beneficial owners."
        ),
        "observations": observations,
        "extra": {
            "report_type": dataset["report_type"],
            "report_date": latest["report_date"],
            "publication_date": None,
            "contract_market_code": code,
            "open_interest": latest["open_interest"],
            "categories": category_summaries,
            "lookback_observations": len(rows),
            "source_url": dataset["source_url"],
            "methodology": "Net position = long minus short; historical percentile and z-score use retrieved weekly futures-only observations.",
        },
    }


def render_persian_report(
    series: list[dict[str, Any]],
    *,
    generated_at: str,
    publish_result: dict[str, Any],
    failures: list[dict[str, str]] | None = None,
) -> str:
    lines = [
        "🏦 گزارش هفتگی طبقه‌بندی معامله‌گران بزرگ — CFTC",
        f"🕒 زمان دریافت: {generated_at}",
        f"📦 تعداد قراردادهای پایش‌شده: {len(series)}",
        "━━━━━━━━━━━━━━━━━━━━",
        "📌 داده‌ها مربوط به موقعیت‌های روز سه‌شنبه هستند و معمولاً جمعه منتشر می‌شوند.",
    ]
    for index, item in enumerate(series, 1):
        lines.extend([
            "━━━━━━━━━━━━━━━━━━━━",
            f"{index}) {item['name']} ({item['symbol']})",
            f"🗓 تاریخ موقعیت‌ها: {item['data_as_of']}",
            f"📦 موقعیت باز کل: {item['extra']['open_interest']:,.0f} قرارداد",
        ])
        for category in item["extra"]["categories"].values():
            change = category["weekly_net_change"]
            change_text = "ناموجود" if change is None else f"{change:+,.0f}"
            percentile = category["historical_percentile"]
            percentile_text = "ناموجود" if percentile is None else f"{percentile:.1f}٪"
            lines.extend([
                f"• {category['label_fa']}",
                f"  خالص موقعیت: {category['net']:+,.0f} | تغییر هفتگی: {change_text}",
                f"  سهم خالص از موقعیت باز: {category['net_as_pct_open_interest']:+.2f}٪"
                if category["net_as_pct_open_interest"] is not None else "  سهم از موقعیت باز: ناموجود",
                f"  صدک تاریخی خالص موقعیت: {percentile_text} | Z-Score: {category['historical_z_score']}",
            ])
    if failures:
        lines.extend(["━━━━━━━━━━━━━━━━━━━━", "⚠️ قراردادهای ناموفق"])
        lines.extend(f"• {item['symbol']}: {item['error_type']}" for item in failures)
    lines.extend([
        "━━━━━━━━━━━━━━━━━━━━",
        f"💾 وضعیت ذخیره‌سازی: {publish_result.get('status', 'نامشخص')}",
        f"📥 رکوردهای پذیرفته‌شده: {publish_result.get('accepted', 0)}",
        "⚠️ این طبقه‌بندی‌ها نماینده گروه‌های معامله‌گر هستند، نه نام صندوق‌ها یا هویت سرمایه‌گذاران.",
        "⚠️ موقعیت خالص، افشای هفتگی قراردادهای آتی است؛ نه خریدوفروش لحظه‌ای، نه جریان قطعی ورود سرمایه و نه موقعیت بازار نقدی یا خارج از بورس.",
        "⚖️ فقط گزارش‌های Futures Only استفاده شده‌اند؛ داده Futures-and-Options با آن‌ها مخلوط نشده است.",
        "🔗 منبع رسمی: https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm",
    ])
    lines.extend(social_footer_lines())
    return "\n".join(lines)


def run(
    watchlist_path: str | Path,
    *,
    history_limit: int = 260,
    output_json: str | Path = "reports/cftc-advanced-positioning-latest.json",
    output_text: str | Path = "reports/cftc-advanced-positioning-latest.txt",
    source_revision: str | None = None,
) -> dict[str, Any]:
    config = json.loads(Path(watchlist_path).read_text(encoding="utf-8"))
    contracts = config.get("contracts") if isinstance(config, dict) else None
    if not isinstance(contracts, list) or not contracts:
        raise ValueError("CFTC advanced watchlist must contain a non-empty contracts array.")
    series = []
    failures = []
    for contract in contracts:
        try:
            rows = fetch_contract(contract, history_limit=history_limit)
            series.append(build_market_series(contract, rows))
        except Exception as exc:
            failures.append({
                "symbol": str(contract.get("symbol") or contract.get("contract_market_code") or "UNKNOWN"),
                "error_type": type(exc).__name__,
            })
    status = "SUCCESS" if not failures else ("PARTIAL" if series else "FAILED")
    publish_result = (
        publish_market_series(series, source_revision or os.getenv("GITHUB_SHA", "UNKNOWN"))
        if series else {"status": "NO_DATA", "accepted": 0, "error": None}
    )
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    payload = {
        "schema_version": "1.0",
        "source": "CFTC Public Reporting Environment",
        "generated_at": generated_at,
        "status": status,
        "contract_count": len(contracts),
        "series_count": len(series),
        "series": series,
        "failures": failures,
        "publish": publish_result,
        "limitations": [
            "Positions are weekly Tuesday exposures published in the Friday COT release, not transaction-level flows.",
            "CFTC classifications describe trader categories; they do not disclose named funds or beneficial owners.",
            "This adapter uses Futures Only datasets; Futures-and-Options Combined reports are not mixed in.",
            "Historical percentiles and z-scores are descriptive statistics over the retrieved history, not predictive probabilities.",
        ],
    }
    json_path = Path(output_json)
    text_path = Path(output_text)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    text_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    text_path.write_text(
        render_persian_report(series, generated_at=generated_at, publish_result=publish_result, failures=failures) + "\n",
        encoding="utf-8",
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch CFTC Disaggregated and TFF Futures Only positioning.")
    parser.add_argument("--watchlist", default="config/cftc_advanced_watchlist.json")
    parser.add_argument("--history-limit", type=int, default=260)
    parser.add_argument("--output-json", default="reports/cftc-advanced-positioning-latest.json")
    parser.add_argument("--output-text", default="reports/cftc-advanced-positioning-latest.txt")
    args = parser.parse_args()
    payload = run(
        args.watchlist,
        history_limit=args.history_limit,
        output_json=args.output_json,
        output_text=args.output_text,
    )
    print(f"CFTC_ADVANCED: {payload['status']} ({payload['series_count']} series)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
