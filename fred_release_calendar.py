from __future__ import annotations

import argparse
import json
import os
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx

from report_formatting import social_footer_lines

API_ROOT = "https://api.stlouisfed.org/fred"
USER_AGENT = "GRIOS-Research/15.0"

# Official FRED release IDs are the stable match key; names are validated aliases.
RELEASE_CATALOG = {
    "Consumer Price Index": {
        "release_id": 10,
        "accepted_names": ["Consumer Price Index"],
        "label_fa": "شاخص قیمت مصرف‌کننده (CPI)",
        "category": "inflation",
    },
    "Employment Situation": {
        "release_id": 50,
        "accepted_names": ["Employment Situation"],
        "label_fa": "گزارش وضعیت اشتغال آمریکا",
        "category": "labor",
    },
    "Gross Domestic Product": {
        "release_id": 53,
        "accepted_names": ["Gross Domestic Product"],
        "label_fa": "تولید ناخالص داخلی (GDP)",
        "category": "growth",
    },
    "Personal Income and Outlays": {
        "release_id": 54,
        "accepted_names": ["Personal Income and Outlays"],
        "label_fa": "درآمد و مخارج شخصی (PCE)",
        "category": "inflation",
    },
    "Advance Monthly Sales for Retail and Food Services": {
        "release_id": 9,
        "accepted_names": ["Advance Monthly Sales for Retail and Food Services"],
        "label_fa": "فروش خرده‌فروشی",
        "category": "consumption",
    },
    "Industrial Production and Capacity Utilization": {
        "release_id": 13,
        "accepted_names": [
            "G.17 Industrial Production and Capacity Utilization",
            "Industrial Production and Capacity Utilization",
        ],
        "label_fa": "تولید صنعتی و ظرفیت تولید",
        "category": "production",
    },
    "Producer Price Index": {
        "release_id": 46,
        "accepted_names": ["Producer Price Index"],
        "label_fa": "شاخص قیمت تولیدکننده (PPI)",
        "category": "inflation",
    },
}


def _date(value: Any) -> date | None:
    try:
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        return None


def _safe_release_url(release: dict[str, Any]) -> str:
    link = str(release.get("link") or "").strip()
    if link.startswith("https://"):
        return link
    release_id = int(release["id"])
    return f"https://fred.stlouisfed.org/release?rid={release_id}"


def match_release_catalog(releases: Any) -> tuple[list[dict[str, Any]], list[str]]:
    if not isinstance(releases, list):
        raise ValueError("FRED releases response must contain an array.")
    matched = []
    missing = []
    by_id = {}
    for item in releases:
        if not isinstance(item, dict):
            continue
        try:
            release_id = int(item.get("id"))
        except (TypeError, ValueError):
            continue
        if release_id > 0:
            by_id[release_id] = item

    for catalog_name, definition in RELEASE_CATALOG.items():
        release_id = definition["release_id"]
        item = by_id.get(release_id)
        if not item:
            missing.append(catalog_name)
            continue
        actual_name = str(item.get("name") or "").strip()
        if actual_name not in set(definition["accepted_names"]):
            missing.append(catalog_name)
            continue
        matched.append({
            "release_id": release_id,
            "release_name": actual_name,
            "label_fa": definition["label_fa"],
            "category": definition["category"],
            "source_url": _safe_release_url(item),
        })
    return matched, missing


def normalize_release_dates(
    release: dict[str, Any],
    dates: Any,
    *,
    today: date,
    horizon_days: int,
) -> list[dict[str, Any]]:
    if not isinstance(dates, list):
        raise ValueError("FRED release dates response must contain an array.")
    end_date = today + timedelta(days=horizon_days)
    events = []
    seen: set[str] = set()
    for item in dates:
        if not isinstance(item, dict):
            continue
        event_date = _date(item.get("date"))
        if event_date is None or not today <= event_date <= end_date:
            continue
        if item.get("release_id") not in (None, "", release["release_id"], str(release["release_id"])):
            continue
        event_id = f"FRED:{release['release_id']}:{event_date.isoformat()}"
        if event_id in seen:
            continue
        seen.add(event_id)
        events.append({
            "event_id": event_id,
            "release_id": release["release_id"],
            "official_release_name": release["release_name"],
            "title_fa": release["label_fa"],
            "category": release["category"],
            "event_date": event_date.isoformat(),
            "event_time": None,
            "timezone": None,
            "verification_status": "FRED_RELEASE_CALENDAR",
            "impact_score": None,
            "consensus": None,
            "actual": None,
            "source": "FRED",
            "source_url": release["source_url"],
            "caveat": (
                "FRED publishes the source-provided release date. This endpoint does not supply a release time, "
                "market consensus, actual result, or impact score."
            ),
        })
    return sorted(events, key=lambda item: (item["event_date"], item["release_id"]))


def build_calendar_payload(
    releases: list[dict[str, Any]],
    dates_by_release: dict[int, Any],
    *,
    today: date,
    horizon_days: int,
    missing_releases: list[str] | None = None,
) -> dict[str, Any]:
    events = []
    for release in releases:
        events.extend(normalize_release_dates(
            release,
            dates_by_release.get(release["release_id"], []),
            today=today,
            horizon_days=horizon_days,
        ))
    events.sort(key=lambda item: (item["event_date"], item["release_id"]))
    missing = missing_releases or []
    return {
        "schema_version": "1.0",
        "source": "FRED release calendar",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "calendar_start": today.isoformat(),
        "calendar_end": (today + timedelta(days=horizon_days)).isoformat(),
        "status": "PARTIAL" if missing else ("UPCOMING_EVENTS" if events else "NO_UPCOMING_EVENTS"),
        "release_catalog_matched": len(releases),
        "release_catalog_missing": missing,
        "event_count": len(events),
        "events": events,
        "limitations": [
            "The FRED release calendar carries source-published dates; it does not guarantee data availability on FRED at that time.",
            "The selected endpoint does not provide release time, market consensus, actual result, revision surprise, or event-impact score.",
            "No directional market interpretation is generated from a calendar date alone.",
        ],
    }


def fetch_calendar(
    api_key: str,
    *,
    horizon_days: int = 14,
    today: date | None = None,
    timeout: int = 20,
) -> dict[str, Any]:
    if not api_key.strip():
        raise ValueError("FRED_API_KEY is not configured.")
    if not 1 <= horizon_days <= 90:
        raise ValueError("horizon_days must be between 1 and 90.")
    today = today or datetime.now(timezone.utc).date()
    common = {"api_key": api_key, "file_type": "json"}
    response = httpx.get(
        f"{API_ROOT}/releases",
        params=common,
        headers={"User-Agent": USER_AGENT},
        timeout=timeout,
    )
    response.raise_for_status()
    release_payload = response.json()
    releases, missing = match_release_catalog(release_payload.get("releases") if isinstance(release_payload, dict) else None)

    dates_by_release: dict[int, Any] = {}
    for release in releases:
        response = httpx.get(
            f"{API_ROOT}/release/dates",
            params={
                **common,
                "release_id": release["release_id"],
                "include_release_dates_with_no_data": "true",
                "sort_order": "asc",
                "limit": 10000,
            },
            headers={"User-Agent": USER_AGENT},
            timeout=timeout,
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("FRED release-date response is invalid.")
        dates_by_release[release["release_id"]] = payload.get("release_dates", [])
    return build_calendar_payload(
        releases,
        dates_by_release,
        today=today,
        horizon_days=horizon_days,
        missing_releases=missing,
    )


def render_persian_report(payload: dict[str, Any]) -> str:
    status_labels = {
        "UPCOMING_EVENTS": "رویدادهای پیش‌رو شناسایی شدند",
        "NO_UPCOMING_EVENTS": "در بازه انتخاب‌شده رویداد آینده‌ای در فید پیدا نشد",
        "PARTIAL": "تقویم ناقص است؛ برخی انتشارها در کاتالوگ FRED پیدا نشدند",
        "NOT_CONFIGURED": "کلید دسترسی FRED تنظیم نشده است",
        "FAILED": "دریافت تقویم با خطا مواجه شد",
    }
    lines = [
        "🗓️ تقویم رویدادهای اقتصاد کلان — GRIOS",
        f"📆 بازه بررسی: {payload.get('calendar_start', 'نامشخص')} تا {payload.get('calendar_end', 'نامشخص')}",
        f"📊 وضعیت: {status_labels.get(payload.get('status'), payload.get('status', 'نامشخص'))}",
        f"🔢 تعداد رویدادهای ثبت‌شده: {payload.get('event_count', 0)}",
        "━━━━━━━━━━━━━━━━━━━━",
    ]
    events = payload.get("events", [])
    if events:
        for index, event in enumerate(events, 1):
            lines.extend([
                f"{index}) 📌 {event['title_fa']}",
                f"🗓️ تاریخ اعلام‌شده: {event['event_date']}",
                "⏰ ساعت انتشار: در داده FRED مشخص نشده است",
                "📉 اجماع بازار و نتیجه واقعی: در این فید موجود نیست",
                f"🔗 منبع: {event['source_url']}",
                "──────────────",
            ])
    else:
        lines.append("در بازه انتخاب‌شده، تاریخ رویداد قابل‌نمایشی از فید دریافت نشد.")
    if payload.get("release_catalog_missing"):
        lines.extend([
            "⚠️ موارد پیدا‌نشده در کاتالوگ:",
            *[f"• {name}" for name in payload["release_catalog_missing"]],
        ])
    lines.extend([
        "⚠️ این تقویم فقط تاریخ‌های منتشرشده توسط منابع را بازتاب می‌دهد؛ ساعت انتشار، اجماع، مقدار واقعی و میزان اثرگذاری را حدس نمی‌زند.",
        "🧭 رویداد مهم لزوماً به معنی جهت مشخص بازار نیست. تحلیل واکنش بازار باید پس از دریافت داده واقعی و مقایسه با انتظارات انجام شود.",
        "🔗 مرجع: https://fred.stlouisfed.org/",
    ])
    lines.extend(social_footer_lines())
    return "\n".join(lines)


def write_outputs(payload: dict[str, Any], json_path: str | Path, text_path: str | Path) -> None:
    json_destination = Path(json_path)
    text_destination = Path(text_path)
    json_destination.parent.mkdir(parents=True, exist_ok=True)
    text_destination.parent.mkdir(parents=True, exist_ok=True)
    json_destination.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    text_destination.write_text(render_persian_report(payload) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a source-backed FRED macro release calendar.")
    parser.add_argument("--days", type=int, default=14)
    parser.add_argument("--output-json", default="reports/macro-calendar-latest.json")
    parser.add_argument("--output-text", default="reports/macro-calendar-latest.txt")
    args = parser.parse_args()
    api_key = os.getenv("FRED_API_KEY", "").strip()
    try:
        payload = fetch_calendar(api_key, horizon_days=args.days)
    except Exception as exc:
        status = "NOT_CONFIGURED" if not api_key else "FAILED"
        payload = {
            "schema_version": "1.0",
            "source": "FRED release calendar",
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "calendar_start": datetime.now(timezone.utc).date().isoformat(),
            "calendar_end": (datetime.now(timezone.utc).date() + timedelta(days=max(1, min(args.days, 90)))).isoformat(),
            "status": status,
            "event_count": 0,
            "events": [],
            "error_type": type(exc).__name__,
            "limitations": ["The calendar could not be retrieved; no event absence is inferred."],
        }
    write_outputs(payload, args.output_json, args.output_text)
    print(f"FRED_CALENDAR: {payload['status']} ({payload.get('event_count', 0)} event(s))")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
