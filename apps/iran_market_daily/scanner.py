from __future__ import annotations

import json
import math
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path
from statistics import mean, pstdev
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
API = "https://fundai.ir/api/data/v1"
TEHRAN = ZoneInfo("Asia/Tehran")


def load_env() -> None:
    path = ROOT / ".env"
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def request(path: str, token: str, params: dict[str, str] | None = None) -> dict:
    query = "?" + urllib.parse.urlencode(params) if params else ""
    req = urllib.request.Request(
        f"{API}{path}{query}",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json", "User-Agent": "GRIOS-Iran-Research/1.0"},
    )
    with urllib.request.urlopen(req, timeout=20) as response:
        payload = json.loads(response.read())
    if not isinstance(payload, dict) or "data" not in payload:
        raise ValueError("Unexpected FundAI response shape")
    return payload


def valid_rows(payload: dict) -> list[dict]:
    rows = payload.get("data")
    if not isinstance(rows, list):
        raise ValueError("Expected data array")
    return rows


def estimate_credits(symbol_count: int, sessions: int = 60) -> int:
    # FundAI docs: adjusted daily prices cost 6 credits per started block of 30 sessions.
    per_symbol = math.ceil(sessions / 30) * 6
    # Market money-flow endpoint costs 15 credits per started block of 30 sessions.
    return symbol_count * per_symbol + 15


def score_history(rows: list[dict], max_age_days: int) -> dict | None:
    ordered = sorted(rows, key=lambda row: str(row.get("date", "")))
    if len(ordered) < 60:
        return None
    latest = ordered[-1]
    session = latest.get("date")
    try:
        session_date = date.fromisoformat(session)
        age = (datetime.now(TEHRAN).date() - session_date).days
    except (TypeError, ValueError):
        return None
    if age < 0 or age > max_age_days or latest.get("trading_state") == "halted":
        return None
    closes = [float(row["close_rial"]) for row in ordered if row.get("close_rial") is not None]
    if len(closes) < 60 or any(not math.isfinite(x) or x <= 0 for x in closes):
        return None
    last = closes[-1]
    sma20, sma50 = mean(closes[-20:]), mean(closes[-50:])
    momentum20 = (last / closes[-21] - 1) * 100
    momentum60 = (last / closes[-60] - 1) * 100
    returns = [closes[i] / closes[i-1] - 1 for i in range(len(closes)-20, len(closes)) if closes[i-1] > 0]
    vol = pstdev(returns) * math.sqrt(252) * 100 if len(returns) >= 10 else None
    score = 0
    score += 35 if last > sma20 > sma50 else 20 if last > sma20 and last > sma50 else 10 if last > sma20 or last > sma50 else 0
    score += max(0, min(30, 15 + momentum20))
    score += max(0, min(20, 10 + momentum60 / 2))
    score += max(0, min(15, 15 - (vol or 0) / 5))
    return {
        "session": session, "date_jalali": latest.get("date_jalali"),
        "close_rial": last, "momentum20_pct": momentum20, "momentum60_pct": momentum60,
        "sma20_rial": sma20, "sma50_rial": sma50, "annualized_volatility_pct": vol,
        "individual_net_flow_rial": latest.get("individual_net_flow_rial"),
        "value_rial": latest.get("value_rial"), "score": round(score),
    }


def main() -> int:
    load_env()
    token = os.getenv("FUNDAI_API_KEY", "").strip()
    symbols = [s.strip() for s in os.getenv("IRAN_EQUITY_SYMBOLS", "").split(",") if s.strip()]
    max_credits = int(os.getenv("FUNDAI_MAX_DAILY_CREDITS", "0"))
    now = datetime.now(TEHRAN).isoformat(timespec="seconds")
    print(f"گزارش پایش سهام ایران | زمان اجرا: {now} Asia/Tehran")
    print("منبع نامزد: FundAI API؛ قیمت‌ها و ارزش معاملات به ریال. تحلیل پژوهشی است، نه توصیه شخصی خرید/فروش.")
    if not token:
        print("وضعیت: بدون سیگنال؛ FUNDAI_API_KEY در فایل محلی .env تنظیم نشده است.")
        return 2
    if not symbols:
        print("وضعیت: بدون سیگنال؛ فهرست نمادهای IRAN_EQUITY_SYMBOLS خالی است. پوشش کل بازار فعال نیست.")
        return 2
    estimate = estimate_credits(len(symbols))
    if max_credits < estimate:
        print(f"وضعیت: بدون فراخوانی پولی؛ سقف روزانه {max_credits} اعتبار است و برآورد این اجرا {estimate} اعتبار است.")
        return 2
    try:
        account = request("/me/", token)
        if account.get("data", {}).get("key", {}).get("sandbox"):
            print("وضعیت: کلید Sandbox است؛ داده نمونه برای سیگنال روزانه پذیرفته نمی‌شود.")
            return 2
        flow_payload = request("/market/money-flow/", token, {"limit": "1"})
        flow_rows = valid_rows(flow_payload)
        candidates = []
        errors = []
        for symbol in symbols:
            try:
                payload = request(f"/companies/{urllib.parse.quote(symbol, safe='')}/prices/", token, {"limit": "60", "adjusted": "true"})
                rows = valid_rows(payload)
                result = score_history(rows, int(os.getenv("IRAN_MAX_SESSION_AGE_DAYS", "5")))
                if result:
                    result.update({"symbol": symbol, "source_updated_at": payload.get("meta", {}).get("updated_at")})
                    candidates.append(result)
                else:
                    errors.append(f"{symbol}: تاریخچه کمتر از ۶۰ جلسه، کهنه، متوقف یا نامعتبر")
            except (urllib.error.URLError, TimeoutError, ValueError, KeyError, TypeError) as exc:
                errors.append(f"{symbol}: خطای منبع/داده ({type(exc).__name__})")
        candidates.sort(key=lambda row: row["score"], reverse=True)
        flow = flow_rows[0] if flow_rows else None
        print(f"آخرین به‌روزرسانی جریان بازار: {flow_payload.get('meta', {}).get('updated_at')}")
        if flow:
            print(f"عرض بازار: صعودی {flow.get('advancers')} | نزولی {flow.get('decliners')} | خالص جریان حقیقی {flow.get('individual_net_flow_rial')} ریال | جلسه {flow.get('date')} / {flow.get('date_jalali')}")
        qualified = [row for row in candidates if row["score"] >= 65]
        if not qualified:
            print("هیچ نامزد واجد آستانه پایش تکنیکال نیست؛ این مدل به تنهایی فرصت سرمایه‌گذاری را تأیید نمی‌کند.")
        for rank, row in enumerate(qualified[:5], 1):
            print(f"{rank}. {row['symbol']} | امتیاز آزمایشی {row['score']}/100 | پایانی {row['close_rial']:,.0f} ریال | ۲۰جلسه {row['momentum20_pct']:+.1f}% | ۶۰جلسه {row['momentum60_pct']:+.1f}% | داده {row['session']} ({row.get('date_jalali')}) | منبع‌به‌روزرسانی {row.get('source_updated_at')}")
            print("   شرط بازبینی: شکست روند SMA20/SMA50 یا تغییر معنادار جریان/عرض بازار؛ قیمت هدف تعیین نشده.")
        if errors:
            print("موارد کنارگذاشته‌شده: " + "; ".join(errors[:10]))
        print("محدودیت: امتیاز صرفاً غربال تکنیکال آزمایشی است؛ صورت‌های مالی، اطلاعیه‌های Codal، ارزش‌گذاری و بک‌تست در این نسخه وارد نشده‌اند.")
        return 0
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, ValueError, KeyError, TypeError) as exc:
        print(f"وضعیت: بدون سیگنال؛ فراخوانی FundAI موفق/قابل‌اعتبارسنجی نبود ({type(exc).__name__}).")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
