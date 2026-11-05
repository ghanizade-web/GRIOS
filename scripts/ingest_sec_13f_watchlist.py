from __future__ import annotations

import argparse
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from sec_13f_data_hub import GriosDataHubClient, Supabase13FClient
from sec_13f_ingestion import ingest_13f_report_period
from report_formatting import social_footer_lines
from sec_edgar_client import SecEdgarClient, normalize_cik


def load_watchlist(path: str | Path) -> list[dict[str, Any]]:
    source = Path(path)
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Unable to read SEC 13F watchlist JSON: {exc}") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("watchlist"), list):
        raise ValueError("Watchlist file must contain a top-level 'watchlist' array.")

    entries: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, raw in enumerate(payload["watchlist"]):
        if not isinstance(raw, dict):
            raise ValueError(f"Watchlist entry {index} must be an object.")
        raw_cik = raw.get("cik")
        if not isinstance(raw_cik, str) or not raw_cik.isdigit() or not 1 <= len(raw_cik) <= 10:
            raise ValueError(f"Watchlist entry {index} must have a 1-10 digit string CIK.")
        cik = normalize_cik(raw_cik)
        if cik in seen:
            raise ValueError(f"Duplicate CIK in SEC 13F watchlist: {cik}.")
        seen.add(cik)

        name = raw.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"Watchlist entry {index} must have a non-empty name.")
        enabled = raw.get("enabled", True)
        if not isinstance(enabled, bool):
            raise ValueError(f"Watchlist entry {index} enabled must be a boolean.")
        reference_url = raw.get("reference_url")
        if reference_url is not None:
            parsed = urlparse(reference_url) if isinstance(reference_url, str) else None
            if parsed is None or parsed.scheme != "https" or parsed.hostname not in {"sec.gov", "www.sec.gov"}:
                raise ValueError(f"Watchlist entry {index} reference_url must be an HTTPS SEC.gov URL.")

        entries.append({
            "cik": cik,
            "name": name.strip(),
            "enabled": enabled,
            "reference_url": reference_url,
        })
    if not any(item["enabled"] for item in entries):
        raise ValueError("SEC 13F watchlist has no enabled filers.")
    return entries



def _usd(value: Any) -> str:
    try:
        return f"${float(value):,.0f}"
    except (TypeError, ValueError):
        return "ناموجود"


def render_persian_filer_report(report: dict[str, Any], filer_name: str) -> str:
    holdings = report.get("holdings", [])
    total_value = sum(float(item.get("value_usd") or 0) for item in holdings)
    top_holdings = sorted(
        holdings,
        key=lambda item: float(item.get("value_usd") or 0),
        reverse=True,
    )[:5]
    lines = [
        "🏛️ گزارش مالکیت‌های افشاشده در فرم 13F",
        f"🏢 مدیر گزارش‌دهنده: {filer_name}",
        f"🗓 دوره گزارش: {report.get('report_period', 'نامشخص')}",
        f"📅 آخرین تاریخ ثبت در SEC: {report.get('latest_filed_at', 'نامشخص')}",
        "━━━━━━━━━━━━━━━━━━━━",
        f"📦 تعداد ردیف‌های مالکیت گزارش‌شده: {report.get('holdings_count', len(holdings))}",
        f"💰 مجموع ارزش ردیف‌های گزارش‌شده: {_usd(total_value)}",
        "🔎 پنج موقعیت بزرگ بر اساس ارزش گزارش‌شده:",
    ]
    if top_holdings:
        for index, item in enumerate(top_holdings, 1):
            option = f" | اختیار {item['put_call']}" if item.get("put_call") else ""
            lines.append(
                f"{index}. {item.get('issuer', 'نامشخص')} — "
                f"{_usd(item.get('value_usd'))}{option}"
            )
    else:
        lines.append("در داده دریافتی، ردیف مالکیت قابل‌نمایشی وجود ندارد.")
    filings = report.get("applied_filings", [])
    if filings:
        lines.extend(["━━━━━━━━━━━━━━━━━━━━", "📚 اسناد رسمی ثبت‌شده:"])
        lines.extend(str(item.get("source_url")) for item in filings if item.get("source_url"))
    lines.extend([
        "━━━━━━━━━━━━━━━━━━━━",
        "⚠️ فرم 13F افشای دوره‌ایِ دارایی‌های مشمول گزارش در پایان فصل است؛ تاریخ انجام معامله را نشان نمی‌دهد و ممکن است تا ۴۵ روز پس از پایان فصل منتشر شود.",
        "⚠️ این داده به‌تنهایی مالک ذی‌نفع، سرمایه اختصاصی مدیر، موقعیت فروش، معاملات جاری یا جریان لحظه‌ای سرمایه را اثبات نمی‌کند.",
        "🧭 این گزارش بازسازیِ سبد افشاشده عمومی است؛ نه دفتر معاملات و نه توصیه سرمایه‌گذاری.",
        "🔗 منبع رسمی: https://www.sec.gov/edgar/search/",
    ])
    lines.extend(social_footer_lines())
    return "\n".join(lines)


def render_persian_watchlist_summary(summary: dict[str, Any]) -> str:
    status_labels = {
        "SUCCESS": "پردازش فهرست با موفقیت انجام شد",
        "PARTIAL_FAILURE": "پردازش ناقص؛ برخی مدیران با خطا مواجه شدند",
    }
    lines = [
        "🏛️ گزارش پایش مدیران سرمایه — فرم SEC 13F",
        f"🗓 دوره گزارش: {summary.get('report_period', 'نامشخص')}",
        "━━━━━━━━━━━━━━━━━━━━",
        f"👥 تعداد مدیران در فهرست: {summary.get('filers_total', 0)}",
        f"✅ گزارش‌های دریافت و ثبت‌شده: {summary.get('filers_published', 0)}",
        f"⚠️ گزارش‌های ناموفق: {summary.get('filers_failed', 0)}",
        f"⏭️ موارد غیرفعال: {summary.get('filers_skipped', 0)}",
        f"📊 وضعیت کل: {status_labels.get(summary.get('status'), summary.get('status', 'نامشخص'))}",
        "━━━━━━━━━━━━━━━━━━━━",
    ]
    for item in summary.get("results", []):
        status = item.get("status")
        icon = "✅" if status == "PUBLISHED" else "⚠️" if status == "FAILED" else "⏭️"
        lines.append(f"{icon} {item.get('name', 'نامشخص')}")
        if status == "PUBLISHED":
            lines.append(
                f"   تعداد موقعیت‌ها: {item.get('holdings_count', 0)} | "
                f"تعداد اسناد: {item.get('filings_count', 0)}"
            )
            for index, holding in enumerate(item.get("top_holdings", []), 1):
                option = f" ({holding['put_call']})" if holding.get("put_call") else ""
                lines.append(
                    f"   {index}. {holding.get('issuer', 'نامشخص')}: "
                    f"{_usd(holding.get('value_usd'))}{option}"
                )
        elif status == "FAILED":
            lines.append(f"   علت فنی: {item.get('error_type', 'خطای نامشخص')}")
    lines.extend([
        "━━━━━━━━━━━━━━━━━━━━",
        "⚠️ داده 13F دوره‌ای و با تأخیر است. موقعیت گزارش‌شده، اثبات خریدوفروش اخیر یا ورود سرمایه لحظه‌ای نیست.",
        "🔗 مرجع رسمی SEC: https://www.sec.gov/edgar/search/",
    ])
    lines.extend(social_footer_lines())
    return "\n".join(lines)


def run_watchlist(
    report_period: str,
    *,
    watchlist_path: str | Path,
    output_dir: str | Path,
    registry_path: str | Path,
    summary_path: str | Path,
    summary_report_path: str | Path | None = None,
    environ: dict[str, str] | None = None,
) -> dict[str, Any]:
    try:
        period = datetime.strptime(report_period, "%Y-%m-%d").date().isoformat()
    except (TypeError, ValueError) as exc:
        raise ValueError("report_period must use YYYY-MM-DD.") from exc

    env = os.environ if environ is None else environ
    user_agent = env.get("SEC_USER_AGENT", "").strip()
    data_hub_url = env.get("GRIOS_DATA_HUB_URL", "").strip()
    token = env.get("GRIOS_INGEST_TOKEN", "").strip()
    supabase_url = env.get("SUPABASE_URL", "").strip()
    service_role_key = env.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    source_revision = env.get("GRIOS_SOURCE_REVISION", "").strip() or env.get("GITHUB_SHA", "").strip() or None
    if not user_agent:
        raise RuntimeError("Missing required GitHub Actions variable: SEC_USER_AGENT.")

    if bool(supabase_url) != bool(service_role_key):
        raise RuntimeError(
            "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be configured together."
        )
    if supabase_url and service_role_key:
        hub = Supabase13FClient(supabase_url, service_role_key)
        publisher_backend = "DIRECT_SUPABASE"
    else:
        missing = [
            name for name, value in (
                ("GRIOS_DATA_HUB_URL", data_hub_url),
                ("GRIOS_INGEST_TOKEN", token),
            ) if not value
        ]
        if missing:
            raise RuntimeError(
                "Missing SEC 13F publisher configuration: " + ", ".join(missing)
            )
        hub = GriosDataHubClient(data_hub_url, token)
        publisher_backend = "DATA_HUB_WORKER"

    entries = load_watchlist(watchlist_path)
    # One shared SEC client applies request pacing across every filer.
    sec = SecEdgarClient(user_agent=user_agent)
    reports_dir = Path(output_dir)
    reports_dir.mkdir(parents=True, exist_ok=True)
    results = []

    for entry in entries:
        if not entry["enabled"]:
            results.append({
                "cik": entry["cik"],
                "name": entry["name"],
                "status": "SKIPPED_DISABLED",
            })
            continue
        try:
            retrieved_at = datetime.now().astimezone().isoformat(timespec="seconds")
            report = ingest_13f_report_period(
                sec,
                entry["cik"],
                period,
                retrieved_at=retrieved_at,
                include_historical=True,
                database=str(registry_path),
                data_hub_client=hub,
                source_revision=source_revision,
            )
            artifact = reports_dir / f"{entry['cik']}_{period}.json"
            artifact.write_text(
                json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            human_report = render_persian_filer_report(report, entry["name"])
            text_artifact = reports_dir / f"{entry['cik']}_{period}.txt"
            text_artifact.write_text(human_report + "\n", encoding="utf-8")
            top_holdings = sorted(
                report.get("holdings", []),
                key=lambda item: float(item.get("value_usd") or 0),
                reverse=True,
            )[:5]
            results.append({
                "cik": entry["cik"],
                "name": entry["name"],
                "status": "PUBLISHED",
                "snapshot_id": report.get("data_hub_publish", {}).get("snapshot_id"),
                "holdings_count": report.get("holdings_count"),
                "filings_count": report.get("discovered_filing_count"),
                "top_holdings": [
                    {
                        "issuer": item.get("issuer"),
                        "value_usd": item.get("value_usd"),
                        "put_call": item.get("put_call"),
                    }
                    for item in top_holdings
                ],
                "artifact": str(artifact),
                "text_artifact": str(text_artifact),
            })
        except Exception as exc:  # continue the batch; report failures explicitly
            results.append({
                "cik": entry["cik"],
                "name": entry["name"],
                "status": "FAILED",
                "error_type": type(exc).__name__,
                "error": str(exc),
            })

    failed = sum(item["status"] == "FAILED" for item in results)
    published = sum(item["status"] == "PUBLISHED" for item in results)
    summary = {
        "schema_version": "1.0",
        "report_period": period,
        "watchlist_path": str(watchlist_path),
        "source_revision": source_revision,
        "publisher_backend": publisher_backend,
        "status": "SUCCESS" if failed == 0 else "PARTIAL_FAILURE",
        "filers_total": len(entries),
        "filers_published": published,
        "filers_failed": failed,
        "filers_skipped": sum(item["status"] == "SKIPPED_DISABLED" for item in results),
        "results": results,
    }
    destination = Path(summary_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    human_path = Path(summary_report_path) if summary_report_path else destination.with_suffix(".txt")
    human_path.parent.mkdir(parents=True, exist_ok=True)
    human_report = render_persian_watchlist_summary(summary)
    human_path.write_text(human_report + "\n", encoding="utf-8")
    (human_path.parent / "latest-sec-13f.txt").write_text(human_report + "\n", encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Ingest a configured SEC 13F institutional-manager watchlist."
    )
    parser.add_argument("--report-period", required=True, help="13F report period in YYYY-MM-DD.")
    parser.add_argument("--watchlist", default="config/sec_13f_watchlist.json")
    parser.add_argument("--output-dir", default="artifacts/sec-13f-watchlist/reports")
    parser.add_argument("--database", default="artifacts/sec-13f-watchlist/registry.sqlite3")
    parser.add_argument("--summary", default="artifacts/sec-13f-watchlist/summary.json")
    parser.add_argument("--summary-report", default="artifacts/sec-13f-watchlist/summary.txt")
    args = parser.parse_args()

    summary = run_watchlist(
        args.report_period,
        watchlist_path=args.watchlist,
        output_dir=args.output_dir,
        registry_path=args.database,
        summary_path=args.summary,
        summary_report_path=args.summary_report,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 1 if summary["filers_failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
