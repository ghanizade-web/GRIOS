from __future__ import annotations

import json
import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from report_formatting import social_footer_lines

DIVIDER = "━━━━━━━━━━━━━━━━━━━━"
PERSIAN_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def _fa(value: Any) -> str:
    return str(value).translate(PERSIAN_DIGITS)


def _jalali(gregorian: date) -> tuple[int, int, int]:
    gy, gm, gd = gregorian.year, gregorian.month, gregorian.day
    month_days = (0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334)
    if gy > 1600:
        jy = 979
        gy -= 1600
    else:
        jy = 0
        gy -= 621
    gy2 = gy + 1 if gm > 2 else gy
    days = (365 * gy + (gy2 + 3) // 4 - (gy2 + 99) // 100 + (gy2 + 399) // 400 - 80 + gd + month_days[gm - 1])
    jy += 33 * (days // 12053)
    days %= 12053
    jy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        jy += (days - 1) // 365
        days = (days - 1) % 365
    if days < 186:
        jm, jd = 1 + days // 31, 1 + days % 31
    else:
        jm, jd = 7 + (days - 186) // 30, 1 + (days - 186) % 30
    return jy, jm, jd


def _as_float(value: Any) -> float | None:
    try:
        number = float(value)
        return number if number == number and abs(number) != float("inf") else None
    except (TypeError, ValueError):
        return None


def _fresh(item: Any, today: date | None = None) -> bool:
    today = today or date.today()
    asset_class = str(getattr(item, "asset_class", ""))
    if asset_class == "crypto":
        raw = getattr(item, "observed_at", None)
        try:
            stamp = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
            if stamp.tzinfo is None:
                return False
            return timedelta(0) <= datetime.now(timezone.utc) - stamp.astimezone(timezone.utc) <= timedelta(minutes=int(os.getenv("MAX_CRYPTO_AGE_MINUTES", "30")))
        except (TypeError, ValueError):
            return False
    raw = getattr(item, "data_as_of", None)
    try:
        observed = date.fromisoformat(str(raw)[:10])
    except (TypeError, ValueError):
        return False
    limits = {"us_equity_etf": int(os.getenv("MAX_EQUITY_AGE_DAYS", "4")), "commodity_proxy": int(os.getenv("MAX_EQUITY_AGE_DAYS", "4")), "commodity_energy": int(os.getenv("MAX_EIA_AGE_DAYS", "14")), "fx_reference": int(os.getenv("MAX_ECB_AGE_DAYS", "4")), "macro": int(os.getenv("MAX_FRED_AGE_DAYS", "10"))}
    age = (today - observed).days
    return 0 <= age <= limits.get(asset_class, 30)


def _points(item: Any) -> list[dict[str, Any]]:
    rows = getattr(item, "observations", []) or []
    return [row for row in rows if isinstance(row, dict) and _as_float(row.get("close")) is not None]


def _return(item: Any, periods: int = 1) -> float | None:
    if getattr(item, "asset_class", "") == "crypto":
        extra = getattr(item, "extra", {}) or {}
        key = {1: "change_24h", 5: "change_7d", 20: "change_30d"}.get(periods)
        return _as_float(extra.get(key)) if key else None
    rows = _points(item)
    if len(rows) <= periods:
        return None
    old, new = _as_float(rows[-(periods + 1)].get("close")), _as_float(rows[-1].get("close"))
    if old is None or new is None or old == 0:
        return None
    return (new / old - 1) * 100


def _trend(item: Any) -> str:
    closes = [_as_float(row.get("close")) for row in _points(item)]
    closes = [value for value in closes if value is not None]
    if len(closes) < 50:
        return "نامشخص"
    last, sma20, sma50 = closes[-1], sum(closes[-20:]) / 20, sum(closes[-50:]) / 50
    if last > sma20 > sma50:
        return "صعودی"
    if last < sma20 < sma50:
        return "نزولی"
    return "خنثی یا متناقض"


def _direction(value: float | None) -> str:
    if value is None:
        return "نامشخص"
    if value > 0.15:
        return "در حال تقویت"
    if value < -0.15:
        return "در حال تضعیف"
    return "تقریباً باثبات"


def _calendar_events(path: str | Path | None) -> tuple[list[dict[str, Any]], str | None]:
    if not path:
        return [], "تقویم رویداد در این اجرا به گزارش متصل نشده است."
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        events = payload.get("events", []) if isinstance(payload, dict) else []
        if not isinstance(events, list):
            return [], "ساختار تقویم رویداد معتبر نیست."
        normalized = [event for event in events if isinstance(event, dict)]
        if normalized:
            return normalized, None
        status = str(payload.get("status", "")) if isinstance(payload, dict) else ""
        if status == "NO_UPCOMING_EVENTS":
            return [], "در تقویم رسمی FRED رویداد آینده‌ای در بازه بررسی‌شده ثبت نشده است."
        if status == "PARTIAL":
            return [], "تقویم رسمی FRED ناقص است و نباید کامل تلقی شود."
        return [], "تقویم رسمی FRED در این اجرا رویداد قابل تأییدی برنگرداند."
    except (FileNotFoundError, OSError, ValueError):
        return [], "فایل تقویم رسمی FRED در دسترس نبود."


def _news_payload(path: str | Path | None) -> tuple[list[dict[str, Any]], str]:
    if not path:
        return [], "UNAVAILABLE"
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            return [], "UNAVAILABLE"
        retrieved = datetime.fromisoformat(str(payload.get("retrieved_at", "")).replace("Z", "+00:00"))
        if retrieved.tzinfo is None or datetime.now(timezone.utc) - retrieved.astimezone(timezone.utc) > timedelta(hours=30):
            return [], "STALE"
        items = payload.get("items", [])
        if not isinstance(items, list):
            return [], "UNAVAILABLE"
        valid = []
        cutoff = datetime.now(timezone.utc) - timedelta(hours=72)
        for item in items:
            if not isinstance(item, dict) or not item.get("title") or not item.get("url"):
                continue
            stamp = datetime.fromisoformat(str(item.get("published_at", "")).replace("Z", "+00:00"))
            if stamp.tzinfo is None or stamp.astimezone(timezone.utc) < cutoff:
                continue
            valid.append(item)
        return valid, str(payload.get("status", "PARTIAL"))
    except (OSError, ValueError, TypeError):
        return [], "UNAVAILABLE"


def _news_for(items: list[dict[str, Any]], topic: str) -> list[dict[str, Any]]:
    return [item for item in items if topic in (item.get("topics") or [])]


def _source_name(item: dict[str, Any]) -> str:
    name = str(item.get("publisher") or item.get("feed") or "منبع نامشخص").strip()
    aliases = (
        "Federal Reserve", "Wall Street Journal", "Financial Times", "Associated Press",
        "Bloomberg", "Reuters", "CNBC", "SEC", "EIA", "BIS", "The Block", "CoinDesk",
    )
    for alias in aliases:
        if name == alias or name.startswith(alias + " —"):
            return alias
    return name


def _safe_headline(item: dict[str, Any]) -> str | None:
    title = str(item.get("title", "")).strip()
    if not title or any(char.isdigit() for char in title) or any(char in title for char in "$€£%٪"):
        return None
    return title


def _story_refs(items: list[dict[str, Any]], limit: int = 6) -> list[str]:
    seen_sources: set[str] = set()
    output: list[str] = []
    for item in items:
        source = _source_name(item)
        url = str(item.get("url", "")).strip()
        topics = item.get("topics") or []
        topic_label = _topic_label(topics[0]) if topics else "بازارهای جهانی"
        if not url or source in seen_sources:
            continue
        seen_sources.add(source)
        safe_title = _safe_headline(item)
        label = safe_title or topic_label
        output.append(f"• {source} — {label}" + chr(10) + f"  {url}")
        if len(output) >= limit:
            break
    return output


def _cftc_payload(path: str | Path | None) -> list[dict[str, Any]]:
    if not path:
        return []
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        retrieved = datetime.fromisoformat(str(payload.get("retrieved_at", "")).replace("Z", "+00:00"))
        if retrieved.tzinfo is None or datetime.now(timezone.utc) - retrieved.astimezone(timezone.utc) > timedelta(hours=48):
            return []
        items = payload.get("items", [])
        output = []
        cutoff = date.today() - timedelta(days=14)
        for item in items if isinstance(items, list) else []:
            if not isinstance(item, dict) or not isinstance(item.get("categories"), dict):
                continue
            try:
                report_date = date.fromisoformat(str(item.get("data_as_of", ""))[:10])
            except ValueError:
                continue
            if report_date < cutoff or report_date > date.today():
                continue
            output.append(item)
        return output
    except (OSError, ValueError, TypeError):
        return []


def _cftc_position_phrase(category: dict[str, Any]) -> str:
    net = _as_float(category.get("net"))
    weekly = _as_float(category.get("weekly_net_change"))
    percentile = _as_float(category.get("historical_percentile"))
    if net is None or weekly is None:
        return "جهت موقعیت نامشخص"
    stance = "خالص خرید" if net > 0 else "خالص فروش" if net < 0 else "خنثی"
    if weekly > 0:
        change = "در حال تقویت" if net >= 0 else "فشار فروش کمتر شده"
    elif weekly < 0:
        change = "در حال کاهش" if net >= 0 else "فروش سنگین‌تر شده"
    else:
        change = "بدون تغییر مهم"
    extreme = "، در محدوده بالای تاریخی" if percentile is not None and percentile >= 90 else "، در محدوده پایین تاریخی" if percentile is not None and percentile <= 10 else ""
    return f"{stance}، {change}{extreme}"


def _cftc_item(items: list[dict[str, Any]], prefix: str, symbol: str) -> dict[str, Any] | None:
    return next((item for item in items if item.get("symbol") == symbol and str(item.get("asset_key", "")).startswith(prefix)), None)


def _cftc_summary(item: dict[str, Any], category_keys: tuple[str, ...]) -> str:
    categories = item.get("categories", {})
    parts = []
    for key in category_keys:
        category = categories.get(key)
        if isinstance(category, dict):
            label = str(category.get("label_fa") or key)
            parts.append(f"{label}: {_cftc_position_phrase(category)}")
    return "؛ ".join(parts) if parts else "داده موقعیت این گروه موجود نیست"


def _jalali_label(raw_date: str) -> str:
    try:
        y, m, d = _jalali(date.fromisoformat(raw_date[:10]))
        names = ("فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور", "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند")
        return f"{_fa(d)} {names[m - 1]} {_fa(y)}"
    except (ValueError, IndexError):
        return "تاریخ نامشخص"


def _market_narrative(topic: str, items: list[dict[str, Any]]) -> str:
    templates = {
        "geopolitics": "ریسک سیاسی وقتی به بازار منتقل می‌شود که عرضه انرژی، مسیر حمل‌ونقل یا تحریم‌ها را واقعاً تغییر دهد؛ زنجیره اثر می‌تواند از نفت و گاز به هزینه حمل، تورم و بازده اوراق برسد. تا پیش از تأیید عملیاتی، این فقط یک سناریوست.",
        "monetary_policy": "تصمیم و لحن بانک مرکزی ابتدا انتظارات نرخ را تغییر می‌دهد؛ سپس بازده اوراق و دلار و در نهایت ارزش‌گذاری سهام رشدی و طلا واکنش نشان می‌دهند. واکنش بازار اوراق از خود تیتر مهم‌تر است.",
        "ai_semiconductors": "فرصت AI زمانی واقعی است که هزینه دیتاسنتر به سفارش، درآمد و جریان نقدی تبدیل شود. تراشه، شبکه، برق و خنک‌سازی همگی در زنجیره‌اند؛ اما سرمایه‌گذاری بدون بازده اقتصادی می‌تواند به افت ارزش‌گذاری منجر شود.",
        "energy": "اختلال عرضه و محدودیت ظرفیت از انرژی حمایت می‌کند؛ رشد ضعیف اقتصاد و افزایش موجودی‌ها اثر معکوس دارند. جهت پایدار را با داده هفتگی موجودی و تولید EIA می‌سنجیم، نه فقط تیتر خبری.",
        "metals": "طلا بیش از همه به دلار، بازده واقعی و تقاضای پوشش ریسک حساس است؛ مس و فلزات صنعتی بیشتر از چشم‌انداز تولید و تقاضای چین اثر می‌گیرند؛ نقره میان این دو گروه قرار دارد. بنابراین رشد هم‌زمان همه فلزات را نباید بدون بررسی نرخ بهره و داده صنعتی یک داستان واحد دانست.",
        "crypto": "خبر مقررات یا ETF زمانی محرک پایدار است که تقاضای نقدی و مشارکت بازار آن را تأیید کند. رشد چند توکن به‌تنهایی ورود پول نهادی نیست؛ بدون داده معتبر ETF و صرافی‌ها چنین ادعایی نمی‌کنیم.",
        "fx": "ارزها حاصل رقابت رشد اقتصادی، نرخ بهره مورد انتظار و تقاضای نقدینگی‌اند. خبر بانک مرکزی زمانی اهمیت عملی پیدا می‌کند که اختلاف مسیر سیاست پولی کشورها را تغییر دهد؛ یک حرکت کوتاه‌مدت جفت‌ارز به‌تنهایی برای نتیجه‌گیری درباره روند کافی نیست.",
        "corporate_earnings": "گزارش سود زمانی برای سهم مهم است که کیفیت درآمد، حاشیه سود، جریان نقدی و راهنمای مدیریت با انتظارات بازار هم‌خوان باشد. رشد فروش به‌تنهایی کافی نیست؛ اگر هزینه سرمایه‌گذاری سریع‌تر از درآمد رشد کند، بازار ممکن است حتی به خبر ظاهراً مثبت واکنش منفی نشان دهد.",
        "global_growth": "داده‌های رشد، مسیر تقاضای کالاها، درآمد شرکت‌ها و انتظارات نرخ بهره را به هم وصل می‌کنند. ضعف تولید یا مصرف می‌تواند برای فلزات صنعتی و سهام چرخه‌ای منفی باشد، اما هم‌زمان احتمال کاهش فشار نرخ بهره را بالا ببرد؛ واکنش نهایی به این بستگی دارد که بازار بیشتر نگران رکود است یا از نرخ پایین‌تر استقبال می‌کند.",
        "regulation": "تغییر مقررات می‌تواند هزینه انطباق، دسترسی به بازار و مدل درآمدی شرکت‌ها را تغییر دهد. برای دارایی‌های دیجیتال و خدمات مالی، متن رسمی نهاد ناظر و زمان اجرا مهم‌تر از برداشت شبکه‌های اجتماعی است.",
    }
    return templates.get(topic, "خبرهای این حوزه باید با واکنش قیمت و داده‌های بنیادی همان بازار تطبیق داده شوند؛ تیتر به‌تنهایی سیگنال خرید یا فروش نیست.")


def _topic_label(topic: str) -> str:
    return {
        "geopolitics": "ژئوپلیتیک و سیاست تجاری", "monetary_policy": "بانک‌های مرکزی، تورم و نرخ بهره",
        "ai_semiconductors": "هوش مصنوعی و نیمه‌رساناها", "energy": "انرژی و زنجیره عرضه",
        "metals": "فلزات گران‌بها و صنعتی", "crypto": "دارایی‌های دیجیتال و مقررات کریپتو",
        "fx": "ارزها و دلار", "corporate_earnings": "سود شرکت‌ها و راهنمای مدیریت",
        "global_growth": "رشد اقتصاد جهانی", "regulation": "مقررات و سیاست‌گذاری",
    }.get(topic, topic)


def _trend_text(item: Any) -> str:
    if item is None:
        return "داده معتبر و تازه برای این بازار در دسترس نیست."
    trend = _trend(item)
    if trend == "صعودی":
        return "ساختار میان‌مدت رو به بالا است و فعلاً خریداران کنترل بهتری دارند."
    if trend == "نزولی":
        return "ساختار میان‌مدت نزولی است؛ خرید صرفاً به امید برگشت، ریسک بالایی دارد."
    if trend == "خنثی یا متناقض":
        return "روند میان‌مدت هنوز یکدست نیست و بازار به تأیید تازه نیاز دارد."
    return "تاریخچه معتبر برای تشخیص روند میان‌مدت کافی نیست."


def _section(title: str, paragraphs: list[str]) -> list[str]:
    clean = [part.strip() for part in paragraphs if part and part.strip()]
    return [DIVIDER, title, *clean] if clean else []


def render_daily_narrative_report(
    series_list: list[Any],
    errors: list[str],
    scores: dict[str, dict[str, Any]],
    universe_summary: str | None = None,
    performance: dict[str, Any] | None = None,
    macro_calendar_path: str | Path | None = "reports/macro-calendar-latest.json",
    news_intelligence_path: str | Path | None = "reports/news-intelligence-latest.json",
    cftc_context_path: str | Path | None = "reports/cftc-positioning-latest.json",
) -> str:
    now = datetime.now(ZoneInfo("Asia/Tehran"))
    by_key = {(str(item.asset_class), str(item.symbol).upper()): item for item in series_list if _fresh(item)}
    news, news_status = _news_payload(news_intelligence_path)
    cftc_items = _cftc_payload(cftc_context_path)
    jy, jm, jd = _jalali(now.date())
    months = ("فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور", "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند")
    weekdays = {"Monday": "دوشنبه", "Tuesday": "سه‌شنبه", "Wednesday": "چهارشنبه", "Thursday": "پنجشنبه", "Friday": "جمعه", "Saturday": "شنبه", "Sunday": "یکشنبه"}

    spy, qqq = by_key.get(("us_equity_etf", "SPY")), by_key.get(("us_equity_etf", "QQQ"))
    btc, eth = by_key.get(("crypto", "BTC")), by_key.get(("crypto", "ETH"))
    vix, ten, dollar = (by_key.get(("macro", key)) for key in ("VIXCLS", "DGS10", "DTWEXBGS"))
    equity_trends = [_trend(item) for item in (spy, qqq) if item is not None]
    btc_week, eth_week = _return(btc, 5), _return(eth, 5)
    vix_move = _return(vix, 5) if vix else None
    if equity_trends and all(x == "صعودی" for x in equity_trends) and btc_week is not None and btc_week > 0 and (vix_move is None or vix_move < 0):
        regime = "بهبود اشتهای ریسک"
        lead = "رفتار بازار با افزایش تمایل به دارایی‌های ریسکی سازگار است؛ اما کیفیت این بهبود را باید از گستردگی رشد و مشارکت بخش‌های مختلف سنجید."
    elif equity_trends and all(x == "نزولی" for x in equity_trends) and btc_week is not None and btc_week < 0 and vix_move is not None and vix_move > 0:
        regime = "احتیاط و کاهش اشتهای ریسک"
        lead = "ضعف هم‌زمان سهام و رمزارزها در کنار افزایش تقاضا برای پوشش ریسک، نشان می‌دهد سرمایه‌گذاران محتاط‌تر شده‌اند. در چنین فضایی، خرید عجولانه دارایی‌های پرنوسان توجیه ضعیف‌تری دارد."
    else:
        regime = "بازار دوگانه و بدون جهت واحد"
        lead = "بازارها هنوز پیام یکسانی نمی‌دهند؛ بخشی از دارایی‌ها می‌توانند مقاوم باشند، در حالی که بخش‌های دیگر زیر فشارند. در چنین وضعیتی انتخاب گزینشی از شرط‌بندی یک‌طرفه منطقی‌تر است."

    if not spy or not qqq or not btc or not vix:
        regime = "رژیم ریسک با اطمینان کافی قابل تشخیص نیست"
        lead = "برای تشخیص وضعیت غالب بازار، داده تازه و هم‌زمان از سهام گسترده، فناوری، بیت‌کوین و نوسان بازار کافی نیست؛ بنابراین جهت‌گیری کلان قطعی ارائه نمی‌شود."

    lines = [
        "🌍 **GRIOS | گزارش روزانه هوشمندی بازار**",
        f"📅 {weekdays[now.strftime('%A')]} { _fa(jd) } {months[jm - 1]} { _fa(jy) }",
        "*We Track Capital Before The Crowd.*",
        "",
        "🎯 **نمای کلان بازار | پیام اصلی امروز**",
        f"{lead} **برداشت کلان GRIOS: {regime}.**",
    ]

    # News-led catalyst synthesis: only fresh, attributed stories are eligible.
    priority_topics = ["geopolitics", "monetary_policy", "ai_semiconductors", "energy", "crypto", "global_growth", "corporate_earnings", "metals", "fx", "regulation"]
    present_topics = [topic for topic in priority_topics if _news_for(news, topic)]
    if present_topics:
        catalyst_paragraphs: list[str] = []
        for topic in present_topics[:5]:
            topic_items = _news_for(news, topic)
            tier1 = any(item.get("evidence_tier") == "TIER_1" for item in topic_items)
            label = "شواهد رسمی و خبری" if tier1 else "گزارش رسانه‌های مالی معتبر"
            catalyst_paragraphs.append(f"**{_topic_label(topic)}:** {label} این حوزه را وارد کانون توجه کرده‌اند. {_market_narrative(topic, topic_items)}")
            for story in topic_items[:1]:
                safe_title = _safe_headline(story)
                detail = f" — {safe_title}" if safe_title else ""
                catalyst_paragraphs.append(f"• خبر مرتبط از {_source_name(story)}{detail}.")
        lines.extend(_section("🧭 محرک‌های اصلی و زنجیره اثر آن‌ها", catalyst_paragraphs))
    else:
        status_note = "فیدهای خبری معتبر در این اجرا خبر تازه قابل استنادی برنگرداندند." if news_status in {"UNAVAILABLE", "STALE"} else "در خبرهای تازه جمع‌آوری‌شده، محرک غالبی با شواهد کافی تشخیص داده نشد."
        lines.extend(_section("🧭 محرک‌های خبری", [status_note, "برای جلوگیری از ساختن روایت، جهت بازار فقط بر اساس داده‌های تأییدشده و نه حدس درباره علت حرکت توضیح داده می‌شود."]))

    # Equities and AI.
    equity_items = [by_key.get(("us_equity_etf", symbol)) for symbol in ("SPY", "QQQ", "IWM", "DIA", "XLK", "XLF", "XLE", "XLI", "SOXX", "NVDA", "MSFT", "AMD", "AVGO", "AMZN", "GOOGL", "META", "TSM", "EFA", "EEM")]
    equity_items = [item for item in equity_items if item is not None]
    if equity_items:
        if spy and qqq and _trend(spy) == _trend(qqq):
            paragraphs = [f"شاخص گسترده و فناوری هر دو {_trend(spy)} هستند؛ بنابراین جهت کلی سهام آمریکا هنوز هم‌سو است."]
        else:
            paragraphs = [_trend_text(spy), _trend_text(qqq)]
        if spy and qqq and _return(spy, 1) is not None and _return(qqq, 1) is not None:
            spread = _return(qqq, 1) - _return(spy, 1)
            if spread < -0.25:
                paragraphs.append("فناوری و سهام رشدی از بازار گسترده عقب مانده‌اند؛ این رفتار می‌تواند با حساسیت بیشتر آن‌ها به نرخ تنزیل یا نگرانی درباره بازده سرمایه‌گذاری AI سازگار باشد. برای انتخاب علت، خبرهای سود و هزینه سرمایه‌گذاری شرکت‌ها تعیین‌کننده‌اند.")
            elif spread > 0.25:
                paragraphs.append("فناوری نسبت به بازار گسترده مقاوم‌تر است؛ با این حال برای تأیید رهبری پایدار، باید رشد سود و جریان نقدی شرکت‌ها هم آن را پشتیبانی کند.")
            else:
                paragraphs.append("فعلاً واگرایی مهمی میان فناوری و بازار گسترده دیده نمی‌شود؛ جهت بعدی به سود شرکت‌ها و مسیر نرخ بهره وابسته است.")
        paragraphs.append("در هوش مصنوعی، فرصت فقط در نام‌های پرسر‌و‌صدا نیست؛ شبکه، برق، خنک‌سازی و زیرساخت دیتاسنتر هم از رشد تقاضا اثر می‌گیرند. اما بدون اثبات رشد سفارش، حاشیه سود و بازده سرمایه‌گذاری، خبر AI به‌تنهایی دلیل خرید سهم نیست.")
        lines.extend(_section("📈 سهام جهانی و هوش مصنوعی", paragraphs))
    else:
        lines.extend(_section("📈 سهام جهانی و هوش مصنوعی", ["داده تازه کافی برای ارزیابی شاخص‌های سهام و رهبران فناوری در دسترس نیست؛ از رتبه‌بندی فرصت خرید خودداری می‌شود."]))

    # Sector leadership and global equity breadth.
    sector_symbols = (("SOXX", "نیمه‌رساناها"), ("XLK", "فناوری"), ("XLF", "مالی"), ("XLE", "انرژی"), ("XLI", "صنعت"), ("IWM", "شرکت‌های کوچک"))
    sector_items = [(symbol, label, by_key.get(("us_equity_etf", symbol))) for symbol, label in sector_symbols]
    sector_items = [(symbol, label, item) for symbol, label, item in sector_items if item is not None]
    if sector_items or by_key.get(("us_equity_etf", "EFA")) or by_key.get(("us_equity_etf", "EEM")):
        paragraphs = []
        for trend_label in ("صعودی", "نزولی", "خنثی یا متناقض", "نامشخص"):
            names = [label for _, label, item in sector_items if _trend(item) == trend_label]
            if names:
                paragraphs.append(f"**روند {trend_label}:** " + "، ".join(names) + ".")
        if by_key.get(("us_equity_etf", "EFA")) or by_key.get(("us_equity_etf", "EEM")):
            developed = by_key.get(("us_equity_etf", "EFA")); emerging = by_key.get(("us_equity_etf", "EEM"))
            if developed and emerging:
                paragraphs.append(f"بازارهای توسعه‌یافته در نماینده EFA {_trend(developed)} و بازارهای نوظهور در نماینده EEM {_trend(emerging)} هستند؛ اختلاف عملکرد این دو می‌تواند نشانه تغییر اشتهای ریسک جغرافیایی باشد.")
        lines.extend(_section("🌐 چرخش سرمایه میان بخش‌ها و مناطق", paragraphs))

    # Fixed income and credit ETFs: distinguish these from Treasury yields.
    bond_symbols = (("TLT", "اوراق خزانه بلندمدت"), ("IEF", "اوراق خزانه میان‌مدت"), ("SHY", "اوراق خزانه کوتاه‌مدت"), ("HYG", "اوراق شرکتی پربازده"), ("LQD", "اوراق شرکتی باکیفیت"), ("TIP", "اوراق محافظت‌شده در برابر تورم"))
    bond_items = [(symbol, label, by_key.get(("us_equity_etf", symbol))) for symbol, label in bond_symbols]
    bond_items = [(symbol, label, item) for symbol, label, item in bond_items if item is not None]
    if bond_items:
        paragraphs = []
        for trend_label in ("صعودی", "نزولی", "خنثی یا متناقض", "نامشخص"):
            names = [label for _, label, item in bond_items if _trend(item) == trend_label]
            if names:
                paragraphs.append(f"**روند {trend_label}:** " + "، ".join(names) + ".")
        high_yield = by_key.get(("us_equity_etf", "HYG")); treasury_long = by_key.get(("us_equity_etf", "TLT"))
        if high_yield and treasury_long:
            if _trend(high_yield) == "نزولی" and _trend(treasury_long) == "صعودی":
                paragraphs.append("ضعف اوراق شرکتی پربازده در کنار تقاضای بهتر برای خزانه‌داری می‌تواند با افزایش احتیاط اعتباری سازگار باشد؛ برای تأیید، داده مستقیم اسپرد اعتباری لازم است.")
            elif _trend(high_yield) == "صعودی" and _trend(treasury_long) == "صعودی":
                paragraphs.append("هم‌زمانی تقاضا برای اوراق خزانه و اوراق پربازده می‌تواند با کاهش فشار نرخ و بهبود تمایل به ریسک سازگار باشد؛ این برداشت باید با بازده و اسپرد اعتباری بررسی شود.")
        paragraphs.append("این‌ها صندوق‌های قابل معامله با پشتوانه اوراق‌اند؛ روندشان برای خواندن بازار مفید است، اما جایگزین بازده تا سررسید یا اسپرد اعتباری مستقیم نیستند.")
        lines.extend(_section("🏛 اوراق قرضه و بازار اعتبار", paragraphs))

    # Rates, dollar, bonds.
    macro_items = [item for item in (ten, by_key.get(("macro", "DGS2")), dollar, vix) if item is not None]
    if macro_items:
        paragraphs = []
        if ten:
            yield_move = _return(ten, 5)
            yield_text = "در حال افزایش است" if yield_move is not None and yield_move > 0.15 else "در حال کاهش است" if yield_move is not None and yield_move < -0.15 else "تقریباً باثبات است" if yield_move is not None else "جهت روشنی ندارد"
            paragraphs.append(f"بازده اوراق بلندمدت آمریکا در داده‌های تازه {yield_text}؛ این موضوع از مسیر هزینه تأمین مالی و نرخ تنزیل بر سهام و دارایی‌های بدون بازده اثر می‌گذارد.")
        if dollar:
            paragraphs.append(f"شاخص گسترده دلار { _direction(_return(dollar, 5)) } است؛ دلار قوی‌تر معمولاً شرایط مالی را برای کالاهای دلاری و بخشی از بازارهای نوظهور سخت‌تر می‌کند، اما این رابطه باید با رفتار واقعی هر بازار سنجیده شود.")
        if vix:
            vix_move = _return(vix, 5)
            vix_text = "نوسان و تقاضای پوشش ریسک رو به افزایش است" if vix_move is not None and vix_move > 0.15 else "فشار نوسان در حال فروکش کردن است" if vix_move is not None and vix_move < -0.15 else "نوسان تقریباً باثبات است" if vix_move is not None else "جهت نوسان مشخص نیست"
            paragraphs.append(f"در شاخص نوسان، {vix_text}؛ این شاخص را دماسنج اضطراب بازار می‌خوانیم، نه پیش‌بینی قطعی ریزش.")
        paragraphs.append("بازار اوراق، دلار و طلا را کنار هم می‌خوانیم: اگر بازده و دلار هم‌زمان بالا بروند، معمولاً فشار بیشتری بر طلا و سهام رشدی وارد می‌شود؛ اگر هر دو عقب بنشینند، فضا می‌تواند برای این دارایی‌ها مساعدتر شود.")
        lines.extend(_section("💵 دلار، نرخ بهره و اوراق قرضه", paragraphs))
    else:
        lines.extend(_section("💵 دلار، نرخ بهره و اوراق قرضه", ["داده معتبر و تازه از نرخ‌های مرجع و دلار در دسترس نیست؛ این بخش بدون نتیجه‌گیری جهت‌دار باقی می‌ماند."]))

    # FX.
    fx = [item for item in by_key.values() if getattr(item, "asset_class", "") == "fx_reference"]
    fx = sorted(fx, key=lambda item: str(item.symbol))
    if fx:
        paragraphs = ["نرخ‌های مرجع ارز، جهت نسبی یورو را نشان می‌دهند؛ این داده‌ها نرخ خریدوفروش لحظه‌ای، هزینه معامله یا عمق بازار را نشان نمی‌دهند."]
        for item in fx[:4]:
            paragraphs.append(f"**{str(item.symbol).upper()}:** {_direction(_return(item, 5))} در مشاهدات اخیر؛ برای معامله، اختلاف سیاست پولی و تأیید بازار نقدی باید بررسی شود.")
        lines.extend(_section("💱 بازار ارزهای جهانی", paragraphs))
    else:
        lines.extend(_section("💱 بازار ارزهای جهانی", ["پوشش مستقیم جفت‌ارزها در این اجرا محدود است؛ بنابراین سیگنال معاملاتی ارزی صادر نمی‌شود."]))

    # Energy and commodities.
    proxies = {symbol: by_key.get(("commodity_proxy", symbol)) for symbol in ("DBC", "GLD", "SLV", "USO", "UNG", "CPER", "DBA", "DBB")}
    eia = [item for item in by_key.values() if getattr(item, "asset_class", "") == "commodity_energy"]
    paragraphs = []
    if proxies["USO"]:
        paragraphs.append(f"**نفت:** {_trend_text(proxies['USO']).rstrip('؛. ')}؛ برای تشخیص حرکت پایدار، روند صندوق نفت را با موجودی و تولید هفتگی EIA و خبرهای عرضه تطبیق می‌دهیم.")
    if proxies["UNG"]:
        paragraphs.append(f"**گاز طبیعی:** {_trend_text(proxies['UNG']).rstrip('؛. ')}؛ این بازار به آب‌وهوا، ذخایر، تولید و تقاضای برق حساس است و با نفت الزاماً هم‌جهت نیست.")
    if eia:
        paragraphs.append("داده‌های رسمی موجودی و عرضه انرژی EIA برای بررسی سمت فیزیکی بازار استفاده می‌شوند؛ این داده‌ها هفتگی‌اند و نباید به‌عنوان جریان لحظه‌ای سرمایه تعبیر شوند.")
    if proxies["GLD"]:
        paragraphs.append(f"**طلا:** {_trend_text(proxies['GLD']).rstrip('؛. ')}؛ جهت آن را در کنار دلار، بازده اوراق و ریسک ژئوپلیتیک می‌سنجیم، نه فقط خبرهای پناهگاه امن.")
    if proxies["SLV"]:
        paragraphs.append(f"**نقره:** {_trend_text(proxies['SLV']).rstrip('؛. ')}؛ هم از فلزات گران‌بها اثر می‌گیرد و هم از تقاضای صنعتی.")
    if proxies["CPER"]:
        paragraphs.append(f"**مس و فلزات صنعتی:** {_trend_text(proxies['CPER']).rstrip('؛. ')}؛ این گروه برای سنجش چشم‌انداز تولید صنعتی و تقاضای چین مهم است.")
    if proxies["DBA"]:
        paragraphs.append(f"**کشاورزی:** {_trend_text(proxies['DBA']).rstrip('؛. ')}؛ آب‌وهوا، موجودی غلات، صادرات و هزینه کود می‌توانند محرک اصلی این گروه باشند.")
    if proxies["DBB"]:
        paragraphs.append(f"**فلزات پایه:** {_trend_text(proxies['DBB']).rstrip('؛. ')}؛ این نماینده در کنار مس برای سنجش چرخه صنعتی و تقاضای مواد اولیه استفاده می‌شود.")
    if not paragraphs:
        paragraphs.append("داده کافی از نماینده‌های بورسی کالا و انرژی در دسترس نیست؛ هیچ داده نقدی یا آتی جایگزین‌سازی نمی‌شود.")
    else:
        paragraphs.append("توجه: ابزارهای بورسی این بخش نماینده کالا هستند و ممکن است به‌دلیل ساختار صندوق، سررسید قراردادها و هزینه نگهداری با بازار نقدی تفاوت داشته باشند.")
    lines.extend(_section("🛢 نفت، گاز، طلا و فلزات صنعتی", paragraphs))

    # Crypto.
    crypto = [item for item in by_key.values() if getattr(item, "asset_class", "") == "crypto"]
    if crypto:
        positives = sum(1 for item in crypto if (_return(item, 1) or 0) > 0)
        breadth = positives / len(crypto) if crypto else 0
        if breadth >= 0.65:
            breadth_text = "رشد میان رمزارزهای بزرگ گسترده‌تر شده و مشارکت بازار بهتر است."
        elif breadth <= 0.35:
            breadth_text = "بخش بزرگی از رمزارزهای تحت رصد ضعیف‌اند؛ رشدهای منفرد را نباید بازگشت بازار دانست."
        else:
            breadth_text = "بازار رمزارزها دوگانه است و هنوز اجماع روشنی میان دارایی‌ها شکل نگرفته است."
        relative = "بیت‌کوین در هفته اخیر از اتریوم مقاوم‌تر بوده است." if btc_week is not None and eth_week is not None and btc_week > eth_week else "اتریوم در هفته اخیر از بیت‌کوین مقاوم‌تر بوده است." if btc_week is not None and eth_week is not None and eth_week > btc_week else "برای مقایسه نسبی بیت‌کوین و اتریوم، داده هم‌زمان کافی وجود ندارد."
        paragraphs = [breadth_text, relative, _trend_text(btc) if btc else "داده تازه بیت‌کوین در دسترس نیست.", "تا زمانی که تقاضای نقدی، جریان ETF و ساختار بازار تأیید نشود، از نسبت دادن حرکت بازار به ورود سرمایه نهادی خودداری می‌کنیم."]
        lines.extend(_section("₿ رمزارزها و دارایی‌های دیجیتال", paragraphs))
    else:
        lines.extend(_section("₿ رمزارزها و دارایی‌های دیجیتال", ["داده تازه و معتبر از بازار رمزارزها در این اجرا موجود نیست؛ از پیشنهاد خرید خودداری می‌شود."]))

    # Weekly institutional positioning from the latest validated CFTC Futures Only reports.
    if cftc_items:
        cftc_paragraphs = []
        gold = _cftc_item(cftc_items, "cftc:disaggregated_futures_only:", "GC")
        wti = _cftc_item(cftc_items, "cftc:disaggregated_futures_only:", "CL")
        gas = _cftc_item(cftc_items, "cftc:disaggregated_futures_only:", "NG")
        sp = _cftc_item(cftc_items, "cftc:tff_futures_only:", "ES")
        nasdaq = _cftc_item(cftc_items, "cftc:tff_futures_only:", "NQ")
        euro = _cftc_item(cftc_items, "cftc:tff_futures_only:", "6E")
        pound = _cftc_item(cftc_items, "cftc:tff_futures_only:", "6B")
        yen = _cftc_item(cftc_items, "cftc:tff_futures_only:", "6J")
        if sp:
            cftc_paragraphs.append(f"**S&P 500:** {_cftc_summary(sp, ('asset_manager', 'leveraged_funds'))}. اختلاف این دو گروه یعنی اجماع نهادی کامل نیست.")
        if nasdaq:
            cftc_paragraphs.append(f"**Nasdaq:** {_cftc_summary(nasdaq, ('asset_manager', 'leveraged_funds'))}.")
        if gold:
            cftc_paragraphs.append(f"**طلا:** {_cftc_summary(gold, ('managed_money', 'producer_merchant'))}. موقعیت تولیدکنندگان بیشتر ماهیت پوشش ریسک تجاری دارد.")
        if wti:
            cftc_paragraphs.append(f"**نفت WTI:** {_cftc_summary(wti, ('managed_money', 'producer_merchant'))}.")
        if gas:
            cftc_paragraphs.append(f"**گاز طبیعی:** {_cftc_summary(gas, ('managed_money', 'producer_merchant'))}.")
        fx_positions = []
        for label, item in (("یورو", euro), ("پوند", pound), ("ین", yen)):
            if item:
                fx_positions.append(f"{label}: {_cftc_summary(item, ('asset_manager', 'leveraged_funds'))}")
        if fx_positions:
            cftc_paragraphs.append("**ارزهای اصلی:** " + "؛ ".join(fx_positions) + ".")
        if gas:
            gas_managed = gas.get("categories", {}).get("managed_money", {})
            gas_pct = _as_float(gas_managed.get("historical_percentile"))
            if (_as_float(gas_managed.get("net")) or 0) < 0 and (_as_float(gas_managed.get("weekly_net_change")) or 0) < 0 and gas_pct is not None and gas_pct <= 10:
                cftc_paragraphs.append("**گاز طبیعی:** فروش شلوغ مدیران سرمایه، در صورت چرخش داده ذخایر EIA یا آب‌وهوا، می‌تواند به بازگشت سریع ناشی از بستن اجباری فروش‌ها منجر شود؛ این ریسک است، نه سیگنال خرید مستقل.")
        latest_date = max(str(item.get("data_as_of", "")) for item in cftc_items)
        cftc_paragraphs.append(f"آخرین داده قابل استفاده مربوط به گزارش هفتگی {_jalali_label(latest_date)} است؛ این داده‌ها فقط موقعیت قراردادهای آتی را پوشش می‌دهند؛ آپشن‌ها و جریان لحظه‌ای بازار نقدی در آن‌ها نیست.")
        lines.extend(_section("🏦 موقعیت‌گیری معامله‌گران حرفه‌ای | CFTC", cftc_paragraphs))
    else:
        lines.extend(_section("🏦 موقعیت‌گیری معامله‌گران حرفه‌ای", ["داده تازه و معتبر CFTC در این اجرا در دسترس نبود؛ از ادعای ورود یا خروج سرمایه نهادی خودداری می‌شود."]))
    lines.extend(_section("📄 پرتفوی مدیران بزرگ | SEC 13F", [
        "فرم‌های 13F با تأخیر و به‌صورت فصلی منتشر می‌شوند و فقط بخشی از موقعیت‌های قابل گزارش را نشان می‌دهند؛ برای این اجرا تصویر تأییدشده‌ای از پرتفوی‌های 13F در پایگاه داده ثبت نشده است. بنابراین نام صندوق‌ها یا خریدوفروش آن‌ها را حدس نمی‌زنیم."
    ]))

    lines.extend(_section("⚖️ سناریوهای پیش‌رو", [
        "🟢 **سناریوی صعودی:** اگر فشار نرخ بهره کاهش یابد، سود شرکت‌ها حفظ شود و رشد از چند بخش بازار تأیید بگیرد، شاخص‌های گسترده، فناوری باکیفیت و دارایی‌های ریسکی ظرفیت بهبود بیشتری خواهند داشت.",
        "🔴 **سناریوی نزولی:** اگر شوک انرژی یا تورم دوباره بازده اوراق و دلار را بالا ببرد، فشار بر سهام رشدی، فلزات گران‌بها و رمزارزها می‌تواند تشدید شود؛ در این حالت حفظ نقدینگی و کاهش ریسک اولویت دارد.",
        "⚪ **سناریوی پایه:** محتمل‌ترین رویکرد در بازارهای متناقض، انتخاب‌گری است؛ نه همه دارایی‌ها را باید خرید و نه هر اصلاحی را شروع بازار نزولی دانست.",
    ]))

    # Megatrends and opportunity screening.
    ai_items = _news_for(news, "ai_semiconductors")
    energy_items = _news_for(news, "energy")
    paragraphs = []
    if ai_items:
        paragraphs.append("**هوش مصنوعی و زیرساخت محاسباتی:** تقاضای محاسباتی می‌تواند به نیمه‌رسانا، شبکه، مراکز داده و برق منتقل شود؛ فرصت جذاب‌تر جایی است که رشد تقاضا به سفارش و جریان نقدی قابل مشاهده تبدیل شده باشد.")
    if energy_items:
        paragraphs.append("**برق و زیرساخت انرژی:** رشد دیتاسنترها و برقی‌سازی می‌تواند سرمایه‌گذاری در شبکه، تولید برق و تجهیزات را تقویت کند؛ محدودیت مجوز، اتصال به شبکه و هزینه سرمایه ریسک اصلی این مسیر است.")
    if _news_for(news, "metals") or _news_for(news, "global_growth"):
        paragraphs.append("**مواد اولیه و فلزات راهبردی:** فرصت میان‌مدت به توازن واقعی عرضه و تقاضا وابسته است؛ تیترهای مربوط به کمبود عرضه باید با تولید، موجودی و تقاضای صنعتی تأیید شوند.")
    if not paragraphs:
        paragraphs.append("در داده و خبرهای تأییدشده این اجرا، شواهد کافی برای اعلام شتاب تازه در یک مگاترند خاص وجود ندارد؛ موضوعات ساختاری فقط در فهرست رصد باقی می‌مانند.")
    lines.extend(_section("🧠 مگاترندها؛ فرصت‌های فراتر از نوسان روزانه", paragraphs))

    opportunities: list[str] = []
    risk_off = "احتیاط" in regime
    if spy and qqq and _trend(spy) == "صعودی" and _trend(qqq) == "صعودی" and not risk_off:
        opportunities.append("🟢 **شاخص‌های گسترده و سهام باکیفیت — قابل بررسی برای ورود پله‌ای پس از اصلاح:** ساختار میان‌مدت هر دو شاخص حمایتی است؛ شرط ادامه، حفظ روند سود شرکت‌ها و آرام ماندن نرخ‌های بازار است. خرید یک‌باره پس از رشد، مزیت روشنی ندارد.")
    elif spy or qqq:
        opportunities.append("🟡 **سهام آمریکا — در فهرست انتظار:** تا زمانی که شاخص‌ها و رهبری بازار هم‌جهت نشوند، ورود پله‌ای فقط با تأیید مجدد روند و کیفیت سود شرکت‌ها قابل دفاع است.")
    nq_position = _cftc_item(cftc_items, "cftc:tff_futures_only:", "NQ")
    if nq_position:
        nq_lf = nq_position.get("categories", {}).get("leveraged_funds", {})
        nq_percentile = _as_float(nq_lf.get("historical_percentile"))
        if nq_percentile is not None and nq_percentile >= 90 and (_as_float(nq_lf.get("net")) or 0) > 0:
            opportunities.append("🟡 **فناوری و Nasdaq — تعقیب قیمت توصیه نمی‌شود:** موقعیت خرید صندوق‌های اهرمی در بخش بالایی سابقه قرار دارد؛ برای ورود جدید، اصلاح سالم و حفظ تقاضای نقدی تأیید بهتری از ادامه شتاب کوتاه‌مدت است.")
    long_treasury = by_key.get(("us_equity_etf", "TLT")); intermediate_treasury = by_key.get(("us_equity_etf", "IEF")); high_yield = by_key.get(("us_equity_etf", "HYG")); investment_grade = by_key.get(("us_equity_etf", "LQD"))
    if long_treasury and intermediate_treasury:
        if _trend(long_treasury) == "صعودی" and _trend(intermediate_treasury) == "صعودی":
            if high_yield and _trend(high_yield) == "نزولی":
                opportunities.append("🟡 **اوراق خزانه — پوشش ریسک قابل بررسی:** تقاضا برای سررسیدهای بلندتر بهتر است، اما ضعف اوراق پربازده نشان می‌دهد ریسک اعتباری هنوز بالاست؛ این ترکیب بیشتر به پوشش ریسک می‌خورد تا شرط‌بندی روی رونق اقتصادی.")
            else:
                opportunities.append("🟢 **اوراق خزانه باکیفیت — قابل بررسی برای تنوع‌بخشی:** روند صندوق‌های سررسید کوتاه‌تر و بلندتر هم‌جهت است؛ پیش از ورود، مسیر تورم و بازده واقعی باید این حرکت را تأیید کند.")
        elif high_yield and _trend(high_yield) == "صعودی" and investment_grade and _trend(investment_grade) == "صعودی":
            opportunities.append("🟡 **اوراق شرکتی — زیر نظر:** بهبود هم‌زمان صندوق‌های اعتباری می‌تواند نشانه تحمل ریسک بهتر باشد؛ تأیید نهایی به اسپرد اعتباری و کیفیت ناشران نیاز دارد.")
        else:
            opportunities.append("🟡 **اوراق و اعتبار — انتظار برای جهت روشن‌تر:** روند سررسیدها و کیفیت اعتباری هنوز اجماع کافی نمی‌سازند؛ بازده تا سررسید و اسپرد را نباید از نمودار ETF حدس زد.")
    efa = by_key.get(("us_equity_etf", "EFA")); eem = by_key.get(("us_equity_etf", "EEM"))
    if efa and eem:
        if _trend(efa) == "صعودی" and _trend(eem) == "صعودی":
            opportunities.append("🟡 **سهام بین‌المللی — تنوع‌بخشی قابل بررسی:** بازارهای توسعه‌یافته و نوظهور هر دو ساختار حمایتی دارند؛ ریسک ارز و تفاوت چرخه اقتصادی کشورها همچنان باید در انتخاب صندوق لحاظ شود.")
        else:
            opportunities.append("⚪ **بازارهای بین‌المللی — انتخاب‌گری ضروری است:** اختلاف روند توسعه‌یافته و نوظهور نشان می‌دهد خرید یکپارچه بازار جهانی مزیت مشخصی ندارد.")

    if proxies["GLD"] and _trend(proxies["GLD"]) == "صعودی" and (dollar is None or (_return(dollar, 5) or 0) <= 0) and (ten is None or (_return(ten, 5) or 0) <= 0):
        opportunities.append("🟢 **طلا — پوشش ریسک و تنوع‌بخشی قابل بررسی:** روند نماینده طلا مثبت است و فشار دلار/بازده در داده‌های اخیر تشدید نشده؛ خرید پله‌ای فقط با حفظ این شرایط و کنترل ریسک خبرهای ژئوپلیتیک منطقی است.")
    elif proxies["GLD"]:
        opportunities.append("🟡 **طلا — نیازمند تأیید:** پیش از خرید، باید هم‌زمانی روند طلا با دلار و بازده اوراق روشن‌تر شود؛ صرفاً خبرهای نااطمینانی برای ورود کافی نیست.")
    if btc and btc_week is not None and btc_week > 0 and breadth >= 0.65 and not risk_off:
        opportunities.append("🟢 **بیت‌کوین و دارایی‌های بزرگ — زیر نظر برای خرید پله‌ای مشروط:** بهبود هفتگی با مشارکت گسترده‌تر همراه است؛ شرط اعتبار، تداوم تقاضای نقدی و حفظ ساختار بازار است. آلت‌کوین‌های کم‌عمق در این نتیجه قرار نمی‌گیرند.")
    elif btc:
        opportunities.append("🟡 **رمزارزها — فعلاً صبر برای تأیید:** تا وقتی مشارکت بازار و تقاضای نقدی بهبود نکند، افت قیمت به‌تنهایی دلیل ارزان‌شدن یا فرصت خرید نیست.")
    if proxies["CPER"] and _trend(proxies["CPER"]) == "صعودی":
        opportunities.append("🟡 **مس و فلزات صنعتی — فرصت چرخه‌ای برای بررسی:** روند نماینده مس مثبت است؛ تأیید بنیادی به داده تولید صنعتی، تقاضای چین و وضعیت موجودی‌ها وابسته است.")
    gas_position = _cftc_item(cftc_items, "cftc:disaggregated_futures_only:", "NG")
    if gas_position:
        gas_managed = gas_position.get("categories", {}).get("managed_money", {})
        gas_pct = _as_float(gas_managed.get("historical_percentile"))
        if (_as_float(gas_managed.get("net")) or 0) < 0 and (_as_float(gas_managed.get("weekly_net_change")) or 0) < 0 and gas_pct is not None and gas_pct <= 10:
            opportunities.append("🟡 **گاز طبیعی — فقط برای رصد بازگشت:** فروش خالص مدیران سرمایه به محدوده افراطی رسیده است؛ اگر موجودی EIA، آب‌وهوا و روند بازار هم‌زمان تغییر کنند، بستن اجباری فروش‌ها می‌تواند جهش سریع ایجاد کند. تا پیش از تأیید این محرک‌ها، خرید زودهنگام پرریسک است.")
    if proxies["USO"]:
        opportunities.append("🟡 **انرژی — معامله بر مبنای خبر پرریسک است:** فرصت فقط زمانی تقویت می‌شود که خبر عرضه با داده فیزیکی EIA و تداوم روند بازار هم‌جهت شود؛ در غیر این صورت نوسان خبری می‌تواند برگشت سریع داشته باشد.")
    if not opportunities:
        opportunities.append("⚪ **فعلاً فرصت خرید با شواهد کافی شناسایی نشد.** حفظ نقدینگی و انتظار برای هم‌جهتی روند، خبر و داده بنیادی از ورود اجباری بهتر است.")
    lines.extend(_section("💡 فرصت‌های سرمایه‌گذاری؛ چه چیزی ارزش بررسی دارد؟", opportunities + ["این موارد فهرست پژوهشی و مشروط‌اند، نه دستور خرید. این گزارش توصیه شخصی خرید/فروش صادر نمی‌کند؛ برای تصمیم شخصی به افق زمانی، تحمل ریسک، اندازه پرتفوی و ارزش‌گذاری به‌روز نیاز است."]))

    events, calendar_error = _calendar_events(macro_calendar_path)
    if events:
        upcoming = []
        for event in events:
            event_date = str(event.get("event_date") or "")[:10]
            raw_name = str(event.get("official_release_name") or event.get("release_name") or event.get("name") or "رویداد اقتصادی")
            name = raw_name
            if "Consumer Price Index" in raw_name:
                name = "شاخص قیمت مصرف‌کننده (CPI)"
            elif "Producer Price Index" in raw_name:
                name = "شاخص قیمت تولیدکننده (PPI)"
            elif "Retail and Food Services" in raw_name:
                name = "فروش خرده‌فروشی"
            elif "Industrial Production" in raw_name:
                name = "تولید صنعتی و ظرفیت تولید"
            if event_date:
                try:
                    date.fromisoformat(event_date)
                    upcoming.append((event_date, name))
                except ValueError:
                    continue
        upcoming.sort()
        paragraphs = [f"رویدادهای رسمی پیش‌رو که می‌توانند انتظارات بازار را تغییر دهند: {', '.join(name for _, name in upcoming[:6])}."]
        paragraphs.extend(f"• {_jalali_label(day)} — {name}" for day, name in upcoming[:6])
        paragraphs.append("پیش از انتشار، واکنش بازار به انتظارات و موقعیت‌گیری اهمیت دارد؛ پس از انتشار نیز فقط اختلاف با اجماع معتبر را غافلگیری واقعی می‌دانیم.")
        lines.extend(_section("🗓 رویدادهای اقتصادی پیش‌رو", paragraphs + ["اجماع بازار و رقم واقعی فقط در صورت دریافت از منبع معتبر گزارش می‌شود؛ در این اجرا هیچ عدد انتظاری ساخته نشده است."]))
    elif calendar_error:
        lines.extend(_section("🗓 تقویم اقتصادی", [calendar_error]))

    watch = [
        "آیا خبرهای ژئوپلیتیک به اختلال واقعی عرضه یا تغییر رسمی سیاست تبدیل می‌شوند؟",
        "آیا بازده اوراق و دلار حرکت بازار سهام و طلا را تأیید می‌کنند یا خلاف آن؟",
        "آیا رشد فناوری با سود و جریان نقدی پشتیبانی می‌شود یا فقط بر انتظارات متکی است؟",
        "آیا بهبود رمزارزها گسترده و مبتنی بر تقاضای نقدی است؟",
    ]
    lines.extend(_section("🔍 چه چیزی می‌تواند تحلیل امروز را تغییر دهد؟", [f"• {item}" for item in watch]))

    if news_status in {"UNAVAILABLE", "STALE"}:
        lines.extend(_section("⚠️ کیفیت شواهد خبری", ["دریافت خبر تازه از منابع منتخب در این اجرا کامل نبود؛ بنابراین تحلیل خبری محدود شده و روایت علت‌ومعلولی قطعی ارائه نشده است."]))
    if errors or not by_key:
        lines.extend(_section("⚠️ محدودیت پوشش داده", ["بخشی از داده‌های بازار در این اجرا در دسترس یا تازه نبود. در بازارهای فاقد داده معتبر، نتیجه‌گیری و پیشنهاد خرید صادر نشده است."]))

    lines.extend(_section("📌 جمع‌بندی GRIOS", [
        f"**تصویر غالب:** {regime}.",
        "تمرکز اصلی، تشخیص این است که خبرها چگونه از مسیر نرخ بهره، دلار، عرضه انرژی، سود شرکت‌ها و نقدینگی به بازارهای مختلف منتقل می‌شوند.",
        "بهترین فرصت لزوماً بازاری نیست که بیشترین رشد را داشته؛ بازاری است که محرک روشن، شواهد مستقل، روند تأییدشده و ریسک قابل‌کنترل داشته باشد.",
        "اگر شواهد با هم سازگار نباشند، تصمیم حرفه‌ای می‌تواند صبر باشد؛ نقدینگی نیز یک موقعیت سرمایه‌گذاری است.",
    ]))

    if news:
        refs = _story_refs(news, limit=5)
        if refs:
            lines.extend(_section("📰 منابع خبری بررسی‌شده", refs))
    if cftc_items:
        lines.extend(_section("📚 منبع موقعیت‌گیری", ["CFTC Commitments of Traders — Futures Only: https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm"]))
    lines.extend(social_footer_lines())
    return "\n".join(lines)
