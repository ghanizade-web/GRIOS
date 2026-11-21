from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from daily_narrative_report import (  # noqa: E402
    _news_market_impact,
    _news_market_relevant,
    _source_name,
    _topic_label,
)

MARKET_ORDER = ("rates", "equities", "commodities", "crypto", "fx")
MARKET_LABELS = {
    "rates": "اوراق و نرخ بهره",
    "equities": "سهام",
    "commodities": "کالاها و انرژی",
    "crypto": "رمزارزها",
    "fx": "ارزها",
}
TOPIC_ORDER = (
    "monetary_policy", "geopolitics", "energy", "ai_semiconductors",
    "corporate_earnings", "crypto", "regulation", "metals", "fx", "global_growth",
)
TIER_SCORE = {"TIER_1": 3, "TIER_2": 2, "TIER_3": 1}


def _timestamp(item: dict) -> datetime | None:
    try:
        value = datetime.fromisoformat(str(item.get("published_at", "")).replace("Z", "+00:00"))
        if value.tzinfo is None:
            return None
        return value.astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def _market(item: dict) -> str | None:
    topics = set(item.get("topics") or [])
    preferred = []
    if "monetary_policy" in topics:
        preferred.append("rates")
    if topics & {"energy", "metals"}:
        preferred.append("commodities")
    if topics & {"ai_semiconductors", "corporate_earnings", "global_growth"}:
        preferred.append("equities")
    if topics & {"crypto", "regulation"}:
        preferred.append("crypto")
    if "fx" in topics:
        preferred.append("fx")
    if "geopolitics" in topics:
        preferred.extend(("commodities", "fx", "equities"))
    preferred.extend(MARKET_ORDER)
    for market in dict.fromkeys(preferred):
        if _news_market_relevant(item, market):
            return market
    return None


def _stories(payload: dict, now: datetime) -> list[tuple[dict, str, datetime]]:
    cutoff = now - timedelta(hours=72)
    unique: dict[str, tuple[dict, str, datetime]] = {}
    for item in payload.get("items", []):
        if not isinstance(item, dict):
            continue
        published = _timestamp(item)
        url = str(item.get("url") or "").strip()
        title = " ".join(str(item.get("title") or "").split())
        market = _market(item)
        if not published or published < cutoff or published > now + timedelta(hours=6):
            continue
        if not url.startswith("https://") or not title or not market:
            continue
        key = url.rstrip("/").lower()
        if key in unique:
            continue
        unique[key] = (item, market, published)
    candidates = list(unique.values())
    candidates.sort(
        key=lambda row: (
            TIER_SCORE.get(str(row[0].get("evidence_tier") or "TIER_3"), 0),
            min(len(row[0].get("topics") or []), 4),
            row[2].timestamp(),
        ),
        reverse=True,
    )
    return candidates


def _one_line(item: dict, market: str) -> str:
    topics = set(item.get("topics") or [])
    topic = next((value for value in TOPIC_ORDER if value in topics), None)
    label = _topic_label(topic) if topic else MARKET_LABELS[market]
    impact = _news_market_impact(item, market)
    impact = impact.replace("اثر بر فارکس: ", "").replace("اثر بر کامودیتی: ", "")
    impact = impact.replace("اثر بر فلزات: ", "").replace("اثر بر سهام: ", "")
    impact = impact.replace("اثر بر کریپتو: ", "").replace("اثر بر اوراق: ", "")
    impact = " ".join(impact.split()).split(" تأیید")[0].strip()
    line = f"📰 محرک روز ({label}): {impact}"
    if len(line) > 320:
        line = line[:317].rsplit(" ", 1)[0].rstrip("،؛:") + "…"
    return line


def build(report_path: Path, news_path: Path, output_dir: Path, report_date: str) -> tuple[Path, Path]:
    report_text = report_path.read_text(encoding="utf-8").strip()
    payload = json.loads(news_path.read_text(encoding="utf-8")) if news_path.is_file() else {}
    now = datetime.now(timezone.utc)
    stories = _stories(payload, now)
    if stories:
        social = _one_line(stories[0][0], stories[0][1])
    else:
        social = "🌍 در این اجرا خبر اثرگذارِ معتبر با داده کافی تأیید نشد؛ جهت تازه‌ای بدون شواهد اعلام نمی‌کنیم."

    archive = [
        f"# گزارش روزانه بازار — {report_date}",
        "",
        f"**خلاصه تلگرام:** {social}",
        "",
        "## تحلیل روز بازار",
        "",
        report_text,
        "",
        "## خبرهای اثرگذار و مسیر اثر بر دارایی‌ها",
        "",
    ]
    for index, (item, market, published) in enumerate(stories[:10], 1):
        title = " ".join(str(item.get("title") or "").split())
        url = str(item.get("url") or "").strip()
        publisher = _source_name(item)
        topics = [t for t in (item.get("topics") or []) if t in TOPIC_ORDER]
        topic_label = "، ".join(_topic_label(t) for t in topics) or MARKET_LABELS[market]
        impact = _news_market_impact(item, market)
        archive.extend([
            f"{index}. **{title}**",
            f"   - حوزه: {topic_label}؛ دارایی‌های در معرض اثر: {MARKET_LABELS[market]} و دارایی‌های مرتبط.",
            f"   - سازوکار اثر احتمالی: {impact}",
            f"   - منبع: [{publisher}]({url})؛ زمان انتشار: {published.isoformat()}",
            "",
        ])
    if len(stories) < 10:
        archive.extend([
            f"> در این اجرا {len(stories)} خبرِ تازه، دارای پیوند و قابل انتساب به بازار پیدا شد؛ برای رسیدن به ۱۰ مورد، خبر کم‌اهمیت یا بی‌سند اضافه نشد.",
            "",
        ])
    output_dir.mkdir(parents=True, exist_ok=True)
    archive_path = output_dir / f"{report_date}.md"
    social_path = output_dir / "telegram-summary.txt"
    archive_path.write_text("\n".join(archive).rstrip() + "\n", encoding="utf-8")
    social_path.write_text(social + "\n", encoding="utf-8")
    return archive_path, social_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", default="reports/latest.txt")
    parser.add_argument("--news", default="reports/news-intelligence-latest.json")
    parser.add_argument("--output-dir", default="reports/daily-market")
    parser.add_argument("--date", default=None)
    args = parser.parse_args()
    report_date = args.date or datetime.now(ZoneInfo("Asia/Tehran")).date().isoformat()
    archive_path, social_path = build(
        Path(args.report), Path(args.news), Path(args.output_dir), report_date
    )
    print(f"ARCHIVE: {archive_path}")
    print(f"TELEGRAM: {social_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
