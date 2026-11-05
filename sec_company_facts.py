from __future__ import annotations

import argparse
import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

from data_coverage import publish_market_series
from report_formatting import social_footer_lines
from sec_edgar_client import SEC_DATA_BASE, SecEdgarClient, normalize_cik

METRICS = {
    "revenue": {
        "label_fa": "درآمد",
        "tags": [
            "RevenueFromContractWithCustomerExcludingAssessedTax",
            "Revenues",
            "SalesRevenueNet",
        ],
        "units": ["USD"],
    },
    "operating_income": {
        "label_fa": "سود عملیاتی",
        "tags": ["OperatingIncomeLoss"],
        "units": ["USD"],
    },
    "net_income": {
        "label_fa": "سود خالص",
        "tags": ["NetIncomeLoss"],
        "units": ["USD"],
    },
    "total_assets": {
        "label_fa": "مجموع دارایی‌ها",
        "tags": ["Assets"],
        "units": ["USD"],
    },
    "cash_and_equivalents": {
        "label_fa": "وجه نقد و معادل نقد",
        "tags": ["CashAndCashEquivalentsAtCarryingValue"],
        "units": ["USD"],
    },
    "current_long_term_debt": {
        "label_fa": "بخش جاری بدهی بلندمدت",
        "tags": ["LongTermDebtCurrent"],
        "units": ["USD"],
    },
    "noncurrent_long_term_debt": {
        "label_fa": "بدهی بلندمدت غیرجاری",
        "tags": ["LongTermDebtNoncurrent"],
        "units": ["USD"],
    },
    "operating_cash_flow": {
        "label_fa": "جریان نقد عملیاتی",
        "tags": ["NetCashProvidedByUsedInOperatingActivities"],
        "units": ["USD"],
    },
    "diluted_eps": {
        "label_fa": "سود هر سهم رقیق‌شده",
        "tags": ["EarningsPerShareDiluted"],
        "units": ["USD/shares"],
    },
}


def select_latest_period_filing(submissions: dict[str, Any]) -> dict[str, str]:
    recent = submissions.get("filings", {}).get("recent")
    if not isinstance(recent, dict):
        raise ValueError("SEC submissions response is missing recent filing arrays.")
    required = ("form", "filingDate", "reportDate", "accessionNumber")
    lengths = {len(recent.get(key, [])) for key in required if isinstance(recent.get(key), list)}
    if len(lengths) != 1 or any(not isinstance(recent.get(key), list) for key in required):
        raise ValueError("SEC submissions filing arrays are missing or misaligned.")
    candidates = []
    for index, form in enumerate(recent["form"]):
        if form not in {"10-K", "10-Q"}:
            continue
        filing_date = str(recent["filingDate"][index] or "")
        report_date = str(recent["reportDate"][index] or "")
        accession = str(recent["accessionNumber"][index] or "")
        if not filing_date or not report_date or not accession:
            continue
        candidates.append({
            "form": form,
            "filing_date": filing_date,
            "report_date": report_date,
            "accession_number": accession,
        })
    if not candidates:
        raise ValueError("No recent original 10-K or 10-Q filing found.")
    return max(candidates, key=lambda item: (item["filing_date"], item["report_date"]))


def _valid_fact_value(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def extract_report_facts(
    companyfacts: dict[str, Any],
    filing: dict[str, str],
) -> list[dict[str, Any]]:
    us_gaap = companyfacts.get("facts", {}).get("us-gaap", {})
    if not isinstance(us_gaap, dict):
        raise ValueError("SEC company facts response is missing us-gaap facts.")
    extracted = []
    accession = filing["accession_number"]
    report_date = filing["report_date"]
    for metric_key, definition in METRICS.items():
        selected = []
        selected_tag = None
        for tag in definition["tags"]:
            tag_data = us_gaap.get(tag)
            units = tag_data.get("units", {}) if isinstance(tag_data, dict) else {}
            if not isinstance(units, dict):
                continue
            candidates = []
            for unit in definition["units"]:
                for item in units.get(unit, []):
                    if not isinstance(item, dict):
                        continue
                    if item.get("accn") != accession:
                        continue
                    if item.get("form") != filing["form"]:
                        continue
                    if item.get("end") != report_date:
                        continue
                    value = _valid_fact_value(item.get("val"))
                    if value is None:
                        continue
                    candidates.append({
                        "metric": metric_key,
                        "label_fa": definition["label_fa"],
                        "xbrl_tag": tag,
                        "value": value,
                        "unit": unit,
                        "period_start": item.get("start"),
                        "period_end": item.get("end"),
                        "filed_at": item.get("filed"),
                        "form": item.get("form"),
                        "accession_number": accession,
                    })
            if candidates:
                selected = candidates
                selected_tag = tag
                break
        if selected:
            seen = set()
            for item in sorted(
                selected,
                key=lambda value: (value["period_start"] or "", value["unit"], value["value"]),
            ):
                identity = (item["period_start"], item["period_end"], item["unit"], item["value"])
                if identity in seen:
                    continue
                seen.add(identity)
                extracted.append(item)
    return extracted


def build_company_series(
    company: dict[str, str],
    submissions: dict[str, Any],
    companyfacts: dict[str, Any],
    *,
    observed_at: str | None = None,
) -> dict[str, Any]:
    cik = normalize_cik(company["cik"])
    filing = select_latest_period_filing(submissions)
    facts = extract_report_facts(companyfacts, filing)
    accession_compact = filing["accession_number"].replace("-", "")
    source_url = (
        f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/"
        f"{accession_compact}/"
    )
    return {
        "key": f"sec:companyfacts:{cik}",
        "symbol": company["symbol"].upper(),
        "name": str(submissions.get("name") or company.get("name") or company["symbol"]),
        "asset_class": "fundamentals",
        "instrument": "SEC Company Facts",
        "provider": "SEC",
        "feed_class": "Latest original 10-K or 10-Q XBRL facts",
        "currency": "USD",
        "observed_at": observed_at or datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "data_as_of": filing["report_date"],
        "caveat": (
            "Values are facts from the latest original 10-K/10-Q filing. Duration facts retain their reported start/end dates "
            "and may represent quarter-to-date, year-to-date, or annual periods; no TTM or standalone-quarter value is inferred."
        ),
        "observations": facts,
        "extra": {
            "cik": cik,
            "form": filing["form"],
            "report_date": filing["report_date"],
            "filing_date": filing["filing_date"],
            "accession_number": filing["accession_number"],
            "filing_url": source_url,
            "metric_count": len(facts),
            "available_metrics": sorted({item["metric"] for item in facts}),
            "limitations": [
                "Only the latest original 10-K or 10-Q accession is selected; amendments are not substituted automatically.",
                "XBRL fact periods are preserved; year-to-date values are not relabeled as standalone quarters.",
                "No analyst consensus, guidance, valuation multiple or forecast is inferred.",
            ],
        },
    }


def _format_value(value: float, unit: str) -> str:
    if unit == "USD/shares":
        return f"${value:,.2f} به‌ازای هر سهم"
    absolute = abs(value)
    if absolute >= 1_000_000_000:
        return f"${value / 1_000_000_000:,.2f} میلیارد"
    if absolute >= 1_000_000:
        return f"${value / 1_000_000:,.2f} میلیون"
    return f"${value:,.0f}"


def render_persian_report(
    series: list[dict[str, Any]],
    *,
    generated_at: str,
    failures: list[dict[str, str]] | None = None,
    publish_result: dict[str, Any] | None = None,
) -> str:
    lines = [
        "🏢 گزارش بنیادی شرکت‌ها — داده‌های رسمی SEC",
        f"🕒 زمان دریافت: {generated_at}",
        f"📊 تعداد شرکت‌های دارای گزارش: {len(series)}",
        "━━━━━━━━━━━━━━━━━━━━",
    ]
    for index, item in enumerate(series, 1):
        extra = item["extra"]
        lines.extend([
            f"{index}) {item['symbol']} — {item['name']}",
            f"📄 فرم: {extra['form']} | دوره گزارش: {extra['report_date']}",
            f"📅 تاریخ ثبت در SEC: {extra['filing_date']}",
        ])
        facts = item.get("observations", [])
        if not facts:
            lines.append("اطلاعات XBRL منتخب در پرونده اخیر قابل استخراج نبود.")
        else:
            for fact in facts:
                period = (
                    f"از {fact['period_start']} تا {fact['period_end']}"
                    if fact.get("period_start") else f"در تاریخ {fact['period_end']}"
                )
                lines.append(
                    f"• {fact['label_fa']} ({period}): {_format_value(fact['value'], fact['unit'])}"
                )
        lines.extend([
            f"🔗 سند رسمی: {extra['filing_url']}",
            "──────────────",
        ])
    if failures:
        lines.extend(["⚠️ شرکت‌های ناموفق"])
        lines.extend(f"• {item['symbol']}: {item['error_type']}" for item in failures)
    if publish_result is not None:
        lines.extend([
            f"💾 وضعیت ذخیره‌سازی: {publish_result.get('status', 'نامشخص')}",
            f"📥 رکوردهای پذیرفته‌شده: {publish_result.get('accepted', 0)}",
        ])
    lines.extend([
        "⚠️ ارقام عین افشای XBRL هستند. بازه شروع و پایان هر رقم حفظ شده است؛ مقدار YTD یا سالانه به‌عنوان درآمد فصلی مستقل معرفی نمی‌شود.",
        "⚠️ این گزارش داده بنیادی تاریخی است؛ اجماع تحلیلگران، راهنمایی مدیریت، ارزش منصفانه و نسبت‌های ارزش‌گذاری در آن محاسبه نشده‌اند.",
        "🔗 مرجع رسمی SEC: https://www.sec.gov/edgar/search/",
    ])
    lines.extend(social_footer_lines())
    return "\n".join(lines)


def run(
    watchlist_path: str | Path,
    *,
    user_agent: str,
    output_json: str | Path = "reports/sec-company-facts-latest.json",
    output_text: str | Path = "reports/sec-company-facts-latest.txt",
    source_revision: str | None = None,
) -> dict[str, Any]:
    if not user_agent.strip() or "@" not in user_agent:
        raise ValueError("SEC_USER_AGENT must include a descriptive application name and contact email.")
    config = json.loads(Path(watchlist_path).read_text(encoding="utf-8"))
    companies = config.get("companies") if isinstance(config, dict) else None
    if not isinstance(companies, list) or not companies:
        raise ValueError("SEC company facts watchlist must contain a non-empty companies array.")
    client = SecEdgarClient(user_agent=user_agent, min_request_interval=0.15)
    series = []
    failures = []
    for company in companies:
        try:
            cik = normalize_cik(company["cik"])
            submissions = client.get_submissions(cik)
            companyfacts_url = urljoin(SEC_DATA_BASE, f"api/xbrl/companyfacts/CIK{cik}.json")
            companyfacts = client._get_json(companyfacts_url)
            series.append(build_company_series(company, submissions, companyfacts))
        except Exception as exc:
            failures.append({
                "symbol": str(company.get("symbol") or company.get("cik") or "UNKNOWN"),
                "error_type": type(exc).__name__,
            })
    status = "SUCCESS" if not failures else ("PARTIAL" if series else "FAILED")
    publish_result = (
        publish_market_series(series, source_revision or os.getenv("GRIOS_SOURCE_REVISION") or os.getenv("GITHUB_SHA", "UNKNOWN"))
        if series else {"status": "NO_DATA", "accepted": 0, "error": None}
    )
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    payload = {
        "schema_version": "1.0",
        "source": "SEC EDGAR Company Facts",
        "generated_at": generated_at,
        "status": status,
        "company_count": len(companies),
        "series_count": len(series),
        "series": series,
        "failures": failures,
        "publish": publish_result,
        "limitations": [
            "Only original 10-K and 10-Q filings are selected; amendments are not automatically substituted.",
            "XBRL duration periods are preserved exactly; quarter-to-date, year-to-date and annual values are not conflated.",
            "No analyst consensus, management guidance, valuation multiple or forecast is inferred.",
        ],
    }
    json_path = Path(output_json)
    text_path = Path(output_text)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    text_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    text_path.write_text(
        render_persian_report(series, generated_at=generated_at, failures=failures, publish_result=publish_result) + "\n",
        encoding="utf-8",
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch SEC Company Facts for the configured issuer watchlist.")
    parser.add_argument("--watchlist", default="config/sec_company_facts_watchlist.json")
    parser.add_argument("--output-json", default="reports/sec-company-facts-latest.json")
    parser.add_argument("--output-text", default="reports/sec-company-facts-latest.txt")
    args = parser.parse_args()
    payload = run(
        args.watchlist,
        user_agent=os.getenv("SEC_USER_AGENT", ""),
        output_json=args.output_json,
        output_text=args.output_text,
    )
    print(f"SEC_COMPANY_FACTS: {payload['status']} ({payload['series_count']} companies)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
