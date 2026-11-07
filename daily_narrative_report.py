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


def _number(value: float | None, decimals: int = 2) -> str:
    if value is None:
        return "ناموجود"
    return _fa(f"{value:,.{decimals}f}")


def _pct(value: float | None) -> str:
    if value is None:
        return "تغییر قابل محاسبه نیست"
    return f"{_fa(f'{value:+.2f}')}٪"


def _date_label(value: str | None) -> str:
    return _fa(value[:10]) if value else "نامشخص"


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
    days = (365 * gy + (gy2 + 3) // 4 - (gy2 + 99) // 100
            + (gy2 + 399) // 400 - 80 + gd + month_days[gm - 1])
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


def _fresh(item: Any, today: date | None = None) -> bool:
    today = today or date.today()
    symbol = str(getattr(item, "symbol", "")).upper()
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
    limits = {
        "us_equity_etf": int(os.getenv("MAX_EQUITY_AGE_DAYS", "4")),
        "commodity_proxy": int(os.getenv("MAX_EQUITY_AGE_DAYS", "4")),
        "commodity_energy": int(os.getenv("MAX_EIA_AGE_DAYS", "14")),
        "fx_reference": int(os.getenv("MAX_ECB_AGE_DAYS", "4")),
        "macro": int(os.getenv("MAX_FRED_AGE_DAYS", "10")),
    }
    age = (today - observed).days
    return 0 <= age <= limits.get(asset_class, 30)


def _points(item: Any) -> list[dict[str, Any]]:
    rows = getattr(item, "observations", []) or []
    return [row for row in rows if isinstance(row, dict) and _as_float(row.get("close")) is not None]


def _as_float(value: Any) -> float | None:
    try:
        number = float(value)
        return number if number == number and abs(number) != float("inf") else None
    except (TypeError, ValueError):
        return None


def _return(item: Any, periods: int = 1) -> float | None:
    if getattr(item, "asset_class", "") == "crypto":
        extra = getattr(item, "extra", {}) or {}
        key = {1: "change_24h", 5: "change_7d", 20: "change_30d"}.get(periods)
        return _as_float(extra.get(key)) if key else None
    rows = _points(item)
    if len(rows) <= periods:
        return None
    old = _as_float(rows[-(periods + 1)].get("close"))
    new = _as_float(rows[-1].get("close"))
    if old is None or new is None or old == 0:
        return None
    return (new / old - 1) * 100


def _last(item: Any) -> float | None:
    if getattr(item, "asset_class", "") == "crypto":
        rows = _points(item)
        return _as_float(rows[-1].get("close")) if rows else None
    rows = _points(item)
    return _as_float(rows[-1].get("close")) if rows else None


def _index(series: list[Any]) -> dict[tuple[str, str], Any]:
    result: dict[tuple[str, str], Any] = {}
    for item in series:
        if _fresh(item):
            result[(str(item.asset_class), str(item.symbol).upper())] = item
    return result


def _line(item: Any, *, crypto: bool = False) -> str:
    symbol = str(item.symbol).upper()
    label = getattr(item, "name", None) or symbol
    daily = _return(item, 1)
    weekly = _return(item, 5)
    last = _last(item)
    price = f"قیمت {_number(last, 4 if last is not None and abs(last) < 1 else 2)} {getattr(item, 'currency', 'USD')}" if last is not None else "قیمت ناموجود"
    source = str(getattr(item, "provider", None) or "منبع نامشخص")
    if crypto:
        return f"• {symbol}: {_pct(daily)} در ۲۴ ساعت؛ {_pct(weekly)} در ۷ روز؛ {price}؛ منبع: {source}"
    return f"• {label} ({symbol}): {_pct(daily)} در آخرین جلسه؛ {_pct(weekly)} در ۵ جلسه؛ {price}؛ داده تا {_date_label(getattr(item, 'data_as_of', None))}؛ منبع: {source}"


def _trend(item: Any) -> str | None:
    rows = _points(item)
    closes = [_as_float(row.get("close")) for row in rows]
    closes = [x for x in closes if x is not None]
    if len(closes) < 50:
        return None
    last = closes[-1]
    sma20 = sum(closes[-20:]) / 20
    sma50 = sum(closes[-50:]) / 50
    if last > sma20 > sma50:
        return "روند میان‌مدت صعودی است؛ قیمت بالای میانگین‌های ۲۰ و ۵۰ جلسه‌ای قرار دارد."
    if last < sma20 < sma50:
        return "روند میان‌مدت نزولی است؛ قیمت پایین میانگین‌های ۲۰ و ۵۰ جلسه‌ای قرار دارد."
    return "ساختار میان‌مدت یکدست نیست؛ قیمت و میانگین‌های ۲۰ و ۵۰ جلسه‌ای هم‌جهت کامل نیستند."


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
            return [], "در تقویم رسمی FRED برای بازه بررسی‌شده رویداد آینده‌ای ثبت نشده است."
        if status == "PARTIAL":
            return [], "تقویم رسمی FRED ناقص است؛ فهرست رویدادها کامل تلقی نمی‌شود."
        return [], "تقویم رسمی FRED در این اجرا رویداد قابل تأییدی برنگرداند."
    except FileNotFoundError:
        return [], "فایل تقویم رسمی FRED در دسترس نبود."
    except (OSError, ValueError):
        return [], "خواندن تقویم رسمی FRED ناموفق بود."


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
) -> str:
    now = datetime.now(ZoneInfo("Asia/Tehran"))
    by_key = _index(series_list)
    fresh = [item for item in series_list if _fresh(item)]
    jalali_year, jalali_month, jalali_day = _jalali(now.date())
    jalali_months = ("فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور", "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند")
    weekdays = {"Monday": "دوشنبه", "Tuesday": "سه‌شنبه", "Wednesday": "چهارشنبه", "Thursday": "پنجشنبه", "Friday": "جمعه", "Saturday": "شنبه", "Sunday": "یکشنبه"}
    lines = [
        "🌍 GRIOS | گزارش روزانه هوشمندی بازار",
        f"📅 {weekdays[now.strftime('%A')]} { _fa(jalali_day) } {jalali_months[jalali_month - 1]} { _fa(jalali_year) } | {_fa(now.strftime('%H:%M'))} به وقت تهران",
        "We Track Capital Before The Crowd.",
        "سرمایه را پیش از آنکه به چشم عموم برسد، دنبال می‌کنیم.",
    ]

    # Cross-asset regime: a descriptive price-state label, never a causal claim.
    spy = by_key.get(("us_equity_etf", "SPY"))
    qqq = by_key.get(("us_equity_etf", "QQQ"))
    btc = by_key.get(("crypto", "BTC"))
    vix = by_key.get(("macro", "VIXCLS"))
    equity_moves = [_return(x, 1) for x in (spy, qqq) if x is not None and _return(x, 1) is not None]
    btc_move = _return(btc, 1) if btc is not None else None
    vix_move = _return(vix, 5) if vix is not None else None
    if len(equity_moves) == 2 and btc_move is not None and vix_move is not None:
        equity_mean = sum(equity_moves) / len(equity_moves)
        if equity_mean < 0 and btc_move < 0 and vix_move > 0:
            regime = "احتیاط و کاهش اشتهای ریسک"
            interpretation = "سهام آمریکا و بیت‌کوین هم‌زمان ضعیف‌اند و VIX در افق اخیر بالا رفته است؛ این هم‌جهتی با افزایش تقاضا برای پوشش ریسک سازگار است."
        elif equity_mean > 0 and btc_move > 0 and vix_move < 0:
            regime = "بهبود اشتهای ریسک"
            interpretation = "سهام آمریکا و بیت‌کوین هم‌زمان مثبت‌اند و VIX در افق اخیر کاهش یافته است؛ رفتار قیمت‌ها با بهبود اشتهای ریسک سازگار است."
        else:
            regime = "بازار دوگانه و فاقد جهت واحد"
            interpretation = "بازارها پیام یکسانی نمی‌دهند؛ تأیید جهت باید از هم‌زمانی سهام، نوسان و رمزارزها به دست آید."
    else:
        regime = "رژیم ریسک با اطمینان کافی قابل تشخیص نیست"
        interpretation = "برای جمع‌بندی اشتهای ریسک، داده تازه و هم‌زمان از شاخص سهام، VIX و بیت‌کوین کافی نیست."
    lines.extend(_section("🎯 نمای کلان بازار", [
        f"**ارزیابی وضعیت:** {regime}.",
        interpretation,
        "این طبقه‌بندی فقط از رفتار قیمت‌ها و نوسان استخراج شده است؛ علت خبری یا جریان سرمایه را اثبات نمی‌کند.",
    ]))

    equities = [by_key.get(("us_equity_etf", symbol)) for symbol in ("SPY", "QQQ", "NVDA", "MSFT")]
    equities = [item for item in equities if item is not None]
    if equities:
        q_spread = None
        if spy is not None and qqq is not None and _return(spy, 1) is not None and _return(qqq, 1) is not None:
            q_spread = _return(qqq, 1) - _return(spy, 1)
        if q_spread is not None and q_spread < -0.25:
            read = "فناوری نسبت به بازار گسترده‌تر ضعیف‌تر عمل کرده است؛ این واگرایی می‌تواند نشانه تمرکز فشار فروش در سهام رشدی باشد."
        elif q_spread is not None and q_spread > 0.25:
            read = "شاخص فناوری نسبت به بازار گسترده‌تر مقاوم‌تر بوده است؛ رهبری رشد فعلاً در سهام رشدی متمرکزتر است."
        else:
            read = "عملکرد فناوری و بازار گسترده اختلاف معناداری در داده فعلی نشان نمی‌دهد."
        trend = _trend(qqq) if qqq is not None else None
        lines.extend(_section("📉 سهام آمریکا و فناوری", [
            "بازار سهام را با مقایسه شاخص گسترده و فناوری می‌سنجیم؛ سپس عملکرد نمادهای منتخب را برای تشخیص تمرکز حرکت بررسی می‌کنیم.",
            *[_line(item) for item in equities],
            read,
            trend or "تاریخچه کافی برای ارزیابی میانگین‌های ۲۰ و ۵۰ جلسه‌ای در دسترس نیست.",
            "**سناریوی صعودی:** بازگشت هم‌زمان SPY و QQQ به بالای میانگین ۲۰ جلسه‌ای و حفظ برتری نسبی فناوری. **سناریوی نزولی:** ضعف هم‌زمان دو شاخص و تشدید عقب‌ماندگی QQQ نسبت به SPY.",
        ]))

    crypto = [item for item in fresh if getattr(item, "asset_class", "") == "crypto"]
    if crypto:
        positives = sum(1 for item in crypto if (_return(item, 1) or 0) > 0)
        negatives = sum(1 for item in crypto if (_return(item, 1) or 0) < 0)
        btc_line = _line(btc, crypto=True) if btc is not None else "• بیت‌کوین: داده تازه در دسترس نیست."
        eth = by_key.get(("crypto", "ETH"))
        eth_line = _line(eth, crypto=True) if eth is not None else "• اتریوم: داده تازه در دسترس نیست."
        breadth = f"از { _fa(len(crypto)) } دارایی واجد شرایط، { _fa(positives) } مورد در ۲۴ ساعت مثبت و { _fa(negatives) } مورد منفی بوده‌اند."
        if btc is not None and eth is not None and _return(btc, 1) is not None and _return(eth, 1) is not None:
            relative = "اتریوم از بیت‌کوین بهتر عمل کرده است." if _return(eth, 1) > _return(btc, 1) else "بیت‌کوین از اتریوم بهتر عمل کرده است." if _return(eth, 1) < _return(btc, 1) else "عملکرد بیت‌کوین و اتریوم تقریباً هم‌جهت است."
        else:
            relative = "برای مقایسه نسبی BTC و ETH داده هم‌زمان کافی وجود ندارد."
        lines.extend(_section("₿ رمزارزها | سنجش عمق حرکت", [
            btc_line, eth_line, breadth, relative,
            "**برداشت GRIOS:** مثبت بودن چند نماد به‌تنهایی نشانه ورود سرمایه نهادی نیست؛ برای تأیید چرخش ریسک باید به تداوم breadth و داده مستقل ETF، حجم یا موقعیت‌های باز دسترسی داشت.",
            "**سناریوی صعودی:** حفظ بازده مثبت بیت‌کوین همراه با گسترش مشارکت آلت‌کوین‌ها. **سناریوی نزولی:** منفی شدن BTC و ETH و افزایش تعداد دارایی‌های نزولی.",
        ]))

    commodities = [by_key.get(("commodity_proxy", symbol)) for symbol in ("DBC", "GLD", "SLV", "USO", "UNG", "CPER")]
    commodities = [item for item in commodities if item is not None]
    energy = [item for item in fresh if getattr(item, "asset_class", "") == "commodity_energy"]
    if commodities or energy:
        paragraphs = ["صندوق‌های کالایی فقط نماینده قابل معامله‌اند و لزوماً با قیمت نقدی یا قرارداد آتی کالای پایه یکسان حرکت نمی‌کنند."]
        paragraphs.extend(_line(item) for item in commodities[:5])
        paragraphs.extend(_line(item) for item in energy[:3])
        gold = by_key.get(("commodity_proxy", "GLD"))
        oil = by_key.get(("commodity_proxy", "USO"))
        if gold is not None and oil is not None:
            gold_move, oil_move = _return(gold, 1), _return(oil, 1)
            if gold_move is not None and oil_move is not None and gold_move * oil_move < 0:
                paragraphs.append("طلا و نماینده نفت در جهت مخالف حرکت کرده‌اند؛ این واگرایی نشان می‌دهد بازار کالا یک روایت واحد ندارد و باید محرک هر گروه جداگانه بررسی شود.")
            else:
                paragraphs.append("طلا و نماینده نفت در داده موجود هم‌جهت‌اند؛ برای نسبت دادن این حرکت به تورم یا ریسک ژئوپلیتیک، شواهد خبری مستقل لازم است.")
        paragraphs.append("**سناریوها:** تداوم حرکت فقط با تأیید قیمت‌های بعدی و داده عرضه/تقاضا معتبرتر می‌شود؛ ETF proxy به‌تنهایی جایگزین بازار نقدی و آتی نیست.")
        lines.extend(_section("🛢 کالاها و انرژی", paragraphs))

    macro = {symbol: by_key.get(("macro", symbol)) for symbol in ("DGS10", "DGS2", "DTWEXBGS", "VIXCLS")}
    macro_items = [item for item in macro.values() if item is not None]
    if macro_items:
        paragraphs = []
        for symbol, label in (("DGS10", "بازده اوراق ۱۰ساله آمریکا"), ("DGS2", "بازده اوراق ۲ساله آمریکا"), ("DTWEXBGS", "شاخص گسترده دلار"), ("VIXCLS", "شاخص نوسان VIX")):
            item = macro.get(symbol)
            if item is not None:
                move = _return(item, 5)
                paragraphs.append(f"• {label}: {_number(_last(item), 3)}؛ تغییر ۵ مشاهده اخیر: {_pct(move)}؛ داده تا {_date_label(item.data_as_of)}")
        ten, two, dollar = macro.get("DGS10"), macro.get("DGS2"), macro.get("DTWEXBGS")
        if ten is not None and two is not None:
            spread = (_last(ten) or 0) - (_last(two) or 0)
            paragraphs.append(f"اختلاف بازده ۱۰ساله و ۲ساله: {_number(spread, 3)} واحد درصد. این فاصله به‌تنهایی پیش‌بینی رکود یا جهت دلار نیست.")
        if ten is not None and dollar is not None:
            y_move, d_move = _return(ten, 5), _return(dollar, 5)
            if y_move is not None and d_move is not None and y_move > 0 and d_move > 0:
                paragraphs.append("بازده اوراق و شاخص دلار در افق اخیر هم‌زمان افزایش یافته‌اند؛ این ترکیب می‌تواند برای دارایی‌های بدون بازده و بازارهای حساس به دلار یک مانع باشد، اما واکنش هر دارایی باید جداگانه تأیید شود.")
            elif y_move is not None and d_move is not None and y_move < 0 and d_move < 0:
                paragraphs.append("بازده اوراق و شاخص دلار هم‌زمان کاهش یافته‌اند؛ این وضعیت می‌تواند فشار نرخ و ارز را از بخشی از دارایی‌های ریسکی و فلزات گران‌بها کم کند، مشروط به تأیید قیمت.")
            else:
                paragraphs.append("بازده اوراق و دلار هم‌جهتی روشنی ندارند؛ بنابراین یک روایت ساده مبتنی بر نرخ بهره برای توضیح همه بازارها کافی نیست.")
        paragraphs.append("**نکته کلیدی:** بازده اسمی با بازده واقعی یکسان نیست؛ بدون داده تورم انتظاری، درباره نرخ واقعی نتیجه‌گیری نمی‌کنیم.")
        lines.extend(_section("💵 دلار، اوراق و شرایط مالی", paragraphs))

    fx = [item for item in fresh if getattr(item, "asset_class", "") == "fx_reference"]
    if fx:
        paragraphs = ["این بخش از نرخ‌های مرجع روزانه ECB استفاده می‌کند؛ نرخ اجرایی بازار، Bid/Ask و عمق نقدینگی نیست."]
        for item in fx[:4]:
            move = _return(item, 5)
            pair = str(item.symbol).upper()
            direction = "افزایش این نرخ یعنی تقویت یورو در برابر ارز مقابل" if pair.startswith("EUR") else "جهت جفت‌ارز بر اساس ارز پایه تفسیر می‌شود"
            paragraphs.append(f"• {pair}: {_number(_last(item), 4)}؛ تغییر ۵ مشاهده اخیر: {_pct(move)}. {direction}.")
        lines.extend(_section("💱 بازار ارز", paragraphs))

    events, calendar_error = _calendar_events(macro_calendar_path)
    if events:
        today = date.today()
        upcoming = []
        for event in events:
            event_date = str(event.get("event_date") or "")[:10]
            name = str(event.get("official_release_name") or event.get("release_name") or event.get("name") or "رویداد اقتصادی")
            if event_date:
                upcoming.append((event_date, name))
        upcoming.sort()
        paragraphs = [f"در تقویم رسمی FRED، { _fa(len(upcoming)) } رویداد در بازه گزارش ثبت شده است."]
        paragraphs.extend(f"• {_date_label(day)} — {name}" for day, name in upcoming[:8])
        paragraphs.append("تقویم فقط تاریخ انتشار را تأیید می‌کند؛ ساعت، اجماع بازار، رقم واقعی و میزان غافلگیری از این منبع استنباط نمی‌شود.")
        lines.extend(_section("🗓 رویدادهای اقتصادی پیش‌رو", paragraphs))
    elif calendar_error:
        lines.extend(_section("🗓 تقویم اقتصادی", [calendar_error, "رویدادهای بدون منبع معتبر یا زمان تأییدشده وارد تحلیل جهت‌دار نمی‌شوند."]))

    # Watchlist ranking is based on observed absolute returns, not the experimental score.
    movers = []
    for item in fresh:
        move = _return(item, 1)
        if move is not None and getattr(item, "asset_class", "") in {"us_equity_etf", "commodity_proxy", "crypto"}:
            movers.append((abs(move), move, item))
    movers.sort(key=lambda row: row[0], reverse=True)
    if movers:
        lines.extend(_section("🔎 نقاطی که امروز ارزش رصد دارند", [
            f"• {item.symbol}: {_pct(move)}؛ فقط به‌دلیل بزرگی حرکت قیمت در داده تازه انتخاب شده است." for _, move, item in movers[:3]
        ] + ["این فهرست اولویت رصد است، نه رتبه‌بندی فرصت خرید یا فروش."]))

    if errors:
        lines.extend(_section("⚠️ محدودیت پوشش امروز", [
            f"در { _fa(len(errors)) } مورد از دریافت داده محدودیت وجود داشت؛ بنابراین همه بازارها پوشش یکسان ندارند.",
            "جزئیات فنی خطاها در فایل JSON و گزارش آرشیوی نگهداری می‌شود تا متن تلگرام به فهرست خطا تبدیل نشود.",
        ]))
    elif not fresh:
        lines.extend(_section("⚠️ محدودیت پوشش امروز", ["داده تازه کافی برای تحلیل بین‌بازاری در دسترس نیست؛ از ساختن سناریوی جهت‌دار خودداری می‌شود."]))

    lines.extend(_section("📌 جمع‌بندی اجرایی GRIOS", [
        f"وضعیت غالب قیمت‌ها: **{regime}**.",
        "تمرکز رصد بعدی باید بر تأیید یا رد هم‌جهتی سهام، دلار، بازده اوراق، نوسان و بیت‌کوین باشد؛ یک حرکت منفرد برای تغییر دیدگاه کلان کافی نیست.",
        "در این نسخه، داده‌های ETF flow، لیکوئیدیشن، سفارشات بازار و خبرهای لحظه‌ای به‌صورت کامل در اسکن روزانه ادغام نشده‌اند؛ بنابراین درباره آن‌ها ادعای عددی یا علت قطعی مطرح نمی‌شود.",
        "این گزارش پژوهشی و سناریومحور است؛ توصیه شخصی خرید/فروش، سفارش معاملاتی یا تخصیص سرمایه صادر نمی‌کند.",
    ]))
    lines.extend(social_footer_lines())
    return "\n".join(lines)
