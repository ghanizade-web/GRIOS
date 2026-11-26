from __future__ import annotations
import argparse, json, re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse

SOCIAL = [
    "اینستاگرام: https://www.instagram.com/dr.ghanizade",
    "ایکس: https://x.com/DrGhanizadeh",
    "لینکدین: https://www.linkedin.com/in/drghanizade",
    "فارکستر: https://farcaster.xyz/drghanizade",
    "گیت‌هاب: https://github.com/ghanizade-web",
]
ELIGIBLE = {"crypto", "fx", "commodity"}
REQUIRED = {"instrument","asset_class","direction","price","price_type","provider","timestamp","catalyst","catalyst_published_at","catalyst_date","transmission","trigger","invalidation","horizon","risk","evidence_grade","sources"}
THEMES = {
 "critical_materials": ("copper","lithium","uranium","rare earth","gallium","germanium","antimony","tungsten","platinum","palladium","rhodium","graphite","nickel","cobalt","critical mineral"),
 "ai_compute": ("artificial intelligence","data center","datacenter","hyperscaler","gpu","semiconductor","chip","high-bandwidth memory","hbm","advanced packaging","optical interconnect"),
 "power_energy": ("nuclear","small modular reactor","smr","power grid","transformer","switchgear","electricity demand","energy storage","lng","natural gas"),
 "defense_aerospace": ("defense","defence","aerospace","drone","unmanned","missile","satellite","space infrastructure"),
 "robotics_autonomy": ("robotics","robot","autonomous","automation","self-driving"),
 "industrial_capex": ("capex","capital expenditure","procurement","purchase order","supply agreement","offtake","long-term contract","factory","mine development","processing plant","production capacity","construction contract","government award"),
 "institutional_capital": ("institutional investor","asset manager","sovereign wealth","13f","fund flow","etf flow","portfolio holding","stake","acquisition","investment","funding round"),
}
CAPITAL_WORDS = ("capex","capital expenditure","procurement","purchase order","supply agreement","offtake","contract","acquisition","investment","funding","financing","stake","award","factory","mine development","production capacity","order book","expand","expansion","loan","loans","credit facility","facility","construction","build","new plant","capacity expansion")

def read_json(path):
    try:
        value=json.loads(Path(path).read_text(encoding="utf-8"))
        return value if isinstance(value,dict) else {}
    except (OSError,json.JSONDecodeError):
        return {}

def parse_time(value):
    try:
        parsed=datetime.fromisoformat(str(value).replace("Z","+00:00"))
        return parsed.astimezone(timezone.utc) if parsed.tzinfo else None
    except (TypeError,ValueError):
        return None

def https(value):
    try:
        p=urlparse(str(value)); return p.scheme=="https" and bool(p.netloc)
    except ValueError:
        return False

def validate_candidate(item, now=None):
    if not isinstance(item,dict): return False,"candidate_not_object"
    missing=REQUIRED-set(item)
    if missing: return False,"missing:"+",".join(sorted(missing))
    asset_class=str(item["asset_class"]).lower()
    if asset_class not in ELIGIBLE: return False,"ineligible_asset_class"
    direction=str(item["direction"]).upper()
    if direction not in {"LONG","SHORT","WATCH"}: return False,"invalid_direction"
    try:
        if float(item["price"])<=0: return False,"invalid_price"
    except (TypeError,ValueError): return False,"invalid_price"
    now=(now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    quote_time=parse_time(item["timestamp"])
    if quote_time is None: return False,"timestamp_must_be_timezone_aware"
    if quote_time>now+timedelta(minutes=5): return False,"future_quote_timestamp"
    quote_max_age=timedelta(minutes=30) if asset_class=="crypto" else timedelta(hours=24)
    if now-quote_time>quote_max_age: return False,"stale_quote"
    catalyst_time=parse_time(item["catalyst_published_at"])
    if catalyst_time is None: return False,"catalyst_timestamp_must_be_timezone_aware"
    if catalyst_time>now+timedelta(minutes=10): return False,"future_catalyst_timestamp"
    if now-catalyst_time>timedelta(hours=72): return False,"stale_catalyst"
    try: date.fromisoformat(str(item["catalyst_date"]))
    except ValueError: return False,"invalid_catalyst_date"
    grade=str(item["evidence_grade"]).upper()
    if grade not in {"A","B","C"}: return False,"invalid_evidence_grade"
    if grade=="C" and direction!="WATCH": return False,"grade_c_must_be_watch"
    if not isinstance(item["sources"],list) or not item["sources"] or not all(https(x) for x in item["sources"]): return False,"sources_must_be_https"
    for key in ("instrument","price_type","provider","catalyst","transmission","trigger","invalidation","horizon","risk"):
        if not str(item.get(key,"")).strip(): return False,"empty:"+key
    return True,"valid"

def build_trading_brief(candidate_path, report_date, now=None):
    candidate_path=Path(candidate_path)
    input_present=candidate_path.is_file()
    payload=read_json(candidate_path)
    raw=payload.get("candidates",[]) if payload else []
    if not isinstance(raw,list): raw=[]
    accepted=[]; rejected=[]
    for item in raw:
        ok,reason=validate_candidate(item,now=now)
        (accepted if ok else rejected).append(item if ok else {"instrument":item.get("instrument") if isinstance(item,dict) else None,"reason":reason})
    lines=[f"GRIOS v15 — گزارش روزانه فرصت‌های معاملاتی | {report_date}",
           "محدوده مجاز معاملات: رمزارزها، جفت‌ارزها و کالاها. سهام و ETFهای سهامی از فهرست نامزدهای معامله حذف شده‌اند.",""]
    if not accepted:
        lines.append("**هیچ معاملهٔ تأییدشده‌ای برای انتشار وجود ندارد.**")
        if not input_present:
            lines += ["فایل نامزدهای معاملاتی ساختاریافته از اسکنر هنوز تولید نشده است؛ بنابراین خروجی فعلی صرفاً وضعیت عدم تأیید را ثبت می‌کند.",
                      "تا زمان اتصال اسکنر به قرارداد کامل کاتالیزور، قیمت زمان‌دار، مسیر اثر، محرک، ابطال و منبع، هیچ ورود یا جهت معاملاتی پیشنهاد نمی‌شود.",""]
        else:
            lines += ["هیچ نامزدی تمام کنترل‌های محرک تازه، قیمت زمان‌دار، مسیر اثر، شرط فعال‌سازی، شرط ابطال، ریسک، درجهٔ شواهد و منبع را نگذرانده است.",
                      "از دادهٔ ناقص، نقطهٔ ورود، حد ضرر، هدف یا جهت معاملاتی استنباط نمی‌شود.",""]
    else:
        lines.append(f"تعداد نامزدهای واجد شرایط: {len(accepted)}. هدف ۱۰ موردی سهمیهٔ تولید فرصت ساختگی نیست.")
        for n,x in enumerate(accepted[:20],1):
            lines += [f"{n}. **{x['instrument']} — {str(x['direction']).upper()}**",
                      f"قیمت: {x['price']} | نوع مظنه: {x['price_type']} | ارائه‌دهنده: {x['provider']} | زمان: {x['timestamp']}",
                      f"کاتالیزور ({x['catalyst_date']}): {x['catalyst']}",
                      f"زمان انتشار محرک: {x['catalyst_published_at']}",
                      f"مسیر اثر: {x['transmission']}",
                      f"محرک فعال‌سازی: {x['trigger']}",
                      f"شرط ابطال: {x['invalidation']}",
                      f"افق / ریسک / درجهٔ شواهد: {x['horizon']} / {x['risk']} / {str(x['evidence_grade']).upper()}",
                      "منابع: " + " | ".join(x["sources"]),""] 
    if len(accepted)<10:
        lines.append(f"یادداشت پوشش: {len(accepted)} نامزد واجد شرایط؛ کمتر از هدف ۱۰ موردی. هیچ ایدهٔ ضعیف یا تکراری اضافه نشده است.")
    if rejected: lines.append(f"تعداد رکوردهای ردشده: {len(rejected)}؛ علت‌ها در فایل ممیزی ثبت شده‌اند.")
    lines += ["","پیوندهای شبکه‌های اجتماعی:",*SOCIAL]
    audit={"schema_version":"1.2","report_type":"catalyst_driven_trading_brief","report_date":report_date,
           "candidate_input_present":input_present,
           "candidate_input_status":"PRESENT" if input_present else "UPSTREAM_NOT_INTEGRATED",
           "accepted_count":len(accepted),"accepted_candidates":accepted,"rejected":rejected,
           "status":"NO_CONFIRMED_TRADE" if not accepted else "VALIDATED_CANDIDATES"}
    return "\n".join(lines)+"\n",audit

def _fresh_items(payload, now):
    retrieved=parse_time(payload.get("retrieved_at"))
    if retrieved is None or now-retrieved>timedelta(hours=30) or retrieved>now+timedelta(minutes=10): return []
    items=payload.get("items",[]); cutoff=now-timedelta(hours=72); out=[]; seen_urls=set()
    if not isinstance(items,list): return []
    for item in items:
        if not isinstance(item,dict) or not https(item.get("url")) or not str(item.get("title","")).strip(): continue
        published=parse_time(item.get("published_at"))
        if published is None or published<cutoff or published>now+timedelta(hours=6): continue
        if item.get("evidence_tier") not in {"TIER_1","TIER_2","TIER_3"}: continue
        url=str(item["url"]).strip()
        if url in seen_urls: continue
        text=f"{item.get('title','')} {item.get('summary','')}".casefold()
        themes=[name for name,terms in THEMES.items() if any(term in text for term in terms)]
        if not themes: continue
        seen_urls.add(url)
        capital=any(term in text for term in CAPITAL_WORDS)
        out.append({**item,"_published":published,"_themes":themes,"_capital":capital})
    out.sort(key=lambda x:(x["_capital"],x.get("evidence_tier")=="TIER_1",x["_published"]),reverse=True)
    return out

def _load_13f(directory, watchlist_path=None):
    reports=[]
    watchlist=read_json(watchlist_path) if watchlist_path else {}
    manager_names={str(item.get("cik","")).zfill(10):item.get("name") for item in watchlist.get("watchlist",[]) if isinstance(item,dict) and item.get("cik") and item.get("name")}
    for path in sorted(Path(directory).glob("*.json")) if Path(directory).is_dir() else []:
        p=read_json(path)
        if not p or not p.get("report_period"): continue
        filings=p.get("applied_filings",[]); holdings=p.get("holdings",[])
        urls=[x.get("source_url") for x in filings if isinstance(x,dict) and https(x.get("source_url"))] if isinstance(filings,list) else []
        holdings=[x for x in holdings if isinstance(x,dict)] if isinstance(holdings,list) else []
        holdings.sort(key=lambda x:float(x.get("value_usd") or 0),reverse=True)
        cik=str(p.get("filer_cik") or path.stem.split("_")[0]).zfill(10)
        reports.append({"filer_cik":cik,"manager":p.get("filer_name") or p.get("manager_name") or p.get("name") or manager_names.get(cik) or path.stem,"report_period":p["report_period"],"filed_at":p.get("latest_filed_at"),"holdings_count":p.get("holdings_count",len(holdings)),"top_holdings":[{"issuer":x.get("issuer"),"value_usd":x.get("value_usd")} for x in holdings[:3]],"source_urls":urls})
    return reports

def build_capital_flows_report(news_path,sec13f_dir,report_date,now=None,sec13f_watchlist=None,sec13f_summary=None):
    now=(now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    news=read_json(news_path)
    stories=_fresh_items(news,now)
    reports=_load_13f(sec13f_dir,sec13f_watchlist)
    sec_status=read_json(sec13f_summary) if sec13f_summary else {}
    sec_state=sec_status.get("status","UNAVAILABLE")
    sec_reason=sec_status.get("reason")
    lines=[f"GRIOS v15 — گزارش جریان سرمایه راهبردی و مگاترندها | {report_date}","",
           "هدف: ردیابی سرمایهٔ نهادی، مواد راهبردی، تقاضای صنعتی، خریدهای بزرگ، CapEx و گلوگاه‌های زنجیرهٔ تأمین.",
           "برای جلوگیری از تحریف، عنوان و گزیدهٔ خبرها به زبان اصلی منبع درج شده‌اند؛ ارزیابی و طبقه‌بندی GRIOS فارسی است.",
           "اصل راستی‌آزمایی: تیتر خبر اثبات خرید تکمیل‌شده نیست. اعلام، امضا، تعهد، اجرا و تکمیل معامله وضعیت‌های متفاوت‌اند. مبلغ نامشخص، نامشخص باقی می‌ماند.","",
           "۱) افشاهای نهادی در SEC Form 13F"]
    if reports:
        for r in reports:
            lines.append(f"- مدیر گزارش‌دهنده: {r['manager']} | شناسهٔ SEC: {r.get('filer_cik','نامشخص')} | دورهٔ گزارش: {r['report_period']} | تاریخ آخرین ثبت: {r.get('filed_at') or 'ارائه نشده'} | تعداد موقعیت‌ها: {r['holdings_count']}.")
            for h in r["top_holdings"]:
                value=f"USD {float(h['value_usd']):,.0f}" if h.get("value_usd") is not None else "ارزش ارائه نشده"
                lines.append(f"  موقعیت افشاشده: {h.get('issuer') or 'نام ناشر ارائه نشده'} — {value}.")
    elif sec_state=="NOT_CONFIGURED":
        lines.append(f"- گردآوری 13F در این اجرا انجام نشد؛ پیکربندی SEC یا Supabase ناقص است. جزئیات وضعیت: {sec_reason or 'علت دقیق در فایل وضعیت ثبت نشده'}.")
    elif sec_state in {"FAILED_OR_NOT_RUN","PARTIAL_FAILURE"}:
        lines.append(f"- گردآوری 13F کامل نشد؛ وضعیت اجرا: {sec_state}. جزئیات: {sec_reason or 'در فایل وضعیت بررسی شود'}.")
    else:
        lines.append("- در این اجرا تصویر مالکیت SEC 13F در دسترس نبود؛ بنابراین ادعایی دربارهٔ انباشت نهادی مطرح نمی‌شود.")
    lines += ["محدودیت 13F: تصویر فصلی و با تأخیر از مالکیت‌هاست؛ تاریخ معامله را مشخص نمی‌کند و خرید فعلی، موقعیت فروش، مالکیت ذی‌نفع یا سرمایه‌گذاری اختصاصی مدیر را اثبات نمی‌کند. ممکن است دارایی صندوق‌های متعلق به مشتریان را نشان دهد.","",
              "۲) تقاضای راهبردی، محدودیت عرضه و نشانه‌های CapEx / خرید / قرارداد"]
    selected=stories[:15]
    if selected:
        for n,x in enumerate(selected,1):
            label=("نشانهٔ گزارش‌شدهٔ سرمایه‌گذاری، تأمین مالی، خرید یا توسعهٔ ظرفیت؛ اجرای معامله مستقلاً احراز نشده"
                  if x["_capital"] else "نشانهٔ ساختاری صنعت یا فناوری؛ از آن معامله یا تخصیص سرمایه استنباط نمی‌شود")
            labels={"critical_materials":"مواد راهبردی","ai_compute":"هوش مصنوعی و زیرساخت محاسباتی",
                    "power_energy":"انرژی و زیرساخت برق","defense_aerospace":"دفاع و هوافضا",
                    "robotics_autonomy":"رباتیک و خودران","industrial_capex":"CapEx و ظرفیت صنعتی",
                    "institutional_capital":"سرمایهٔ نهادی"}
            themes=", ".join(labels.get(t,t) for t in x["_themes"])
            lines += [f"{n}. **عنوان اصلی منبع: {x['title']}**",
                      f"ناشر: {x.get('publisher') or x.get('domain') or 'ناشر ارائه نشده'} | زمان انتشار: {x['_published'].isoformat()} | درجهٔ منبع: {x.get('evidence_tier','UNRATED')}",
                      f"طبقه‌بندی GRIOS: {label} | موضوع: {themes}",
                      f"پیوند منبع: {x['url']}",
                      f"گزیدهٔ اصلی منبع: {x.get('summary') or 'گزیده‌ای ارائه نشده؛ فقط عنوان در دسترس است.'}",
                      ""] 
    else:
        lines.append("- در بازهٔ ۷۲ ساعته، نشانهٔ تازه و منبع‌دار دربارهٔ مواد راهبردی، CapEx صنعتی یا فناوری از فیلتر شواهد عبور نکرد. این موضوع اثبات نمی‌کند که هیچ فعالیتی رخ نداده است.")
    lines += ["۳) فهرست پایش مواد راهبردی",
              "مس، لیتیوم، اورانیوم، عناصر خاکی کمیاب، گالیوم، ژرمانیوم، آنتیموان، تنگستن، پلاتین، پالادیوم، رودیوم، گرافیت، نیکل و کبالت.",
              "رادیوم از رودیوم متفاوت است؛ رادیوم فقط در صورت وجود شواهد رسمی و تخصصی جداگانه پایش می‌شود و نباید در فهرست رودیوم ادغام شود.","",
              "۴) شکاف‌های پژوهش و تبدیل شواهد به فرصت",
              "این اجرا از فیدهای RSS پیکربندی‌شده و هر تصویر مالکیت SEC 13F موجود استفاده می‌کند. پوشش کامل قراردادهای خصوصی، سفارش‌های خرید، همهٔ صندوق‌های ثروت ملی، تمام جریان‌های ETF یا همهٔ اسناد شرکت‌ها ادعا نمی‌شود.",
              "برای تبدیل یک نشانه به فرصت سرمایه‌گذاری، سند یا قرارداد اصلی، وضعیت اجرا، مبلغ، دورهٔ گزارش و طرف‌های معامله را بررسی کنید؛ سپس زنجیرهٔ ارزش، ظرفیت عرضه، جایگزین‌پذیری، ارزش‌گذاری، نقدشوندگی، ریسک ژئوپلیتیک و شرط ابطال فرضیه را بسنجید.",
              "نبود داده یا خبر، اثبات نبود فعالیت نیست. هیچ شرکتی صرفاً به‌دلیل تطابق واژه‌ای به‌عنوان ذی‌نفع معرفی نمی‌شود.","",
              "پیوندهای شبکه‌های اجتماعی:",*SOCIAL]
    evidence={"schema_version":"1.1","report_type":"strategic_capital_flows_megatrends","report_date":report_date,
              "news_status":news.get("status","UNAVAILABLE"),"news_retrieved_at":news.get("retrieved_at"),
              "news_window_hours":news.get("window_hours",72),"feed_health":news.get("feed_health"),
              "selected_news":[{k:v for k,v in x.items() if not k.startswith("_")} for x in selected],
              "sec_13f_collection_status":sec_state,"sec_13f_collection_reason":sec_reason,
              "sec_13f_reports":reports,
              "limitations":["13F is a delayed quarterly holdings disclosure, not real-time flow.",
                             "RSS headline/excerpt is not full-text research or proof of execution.",
                             "Absence of a signal is not evidence of absence.",
                             "Beneficiary and valuation claims require issuer-level evidence."]}
    return "\n".join(lines)+"\n",evidence

def main():
    p=argparse.ArgumentParser(description="Build two evidence-gated GRIOS daily reports.")
    p.add_argument("--news",default="reports/news-intelligence-latest.json")
    p.add_argument("--trading-candidates",default="reports/trading-candidates-latest.json")
    p.add_argument("--sec13f-dir",default="reports/sec-13f-watchlist/reports")
    p.add_argument("--sec13f-watchlist",default="config/sec_13f_watchlist.json")
    p.add_argument("--sec13f-summary",default="reports/sec-13f-watchlist/summary.json")
    p.add_argument("--output-dir",default="reports")
    p.add_argument("--date",default=None)
    a=p.parse_args(); day=a.date or datetime.now(timezone.utc).date().isoformat(); out=Path(a.output_dir); out.mkdir(parents=True,exist_ok=True)
    trading,ta=build_trading_brief(Path(a.trading_candidates),day)
    capital,ce=build_capital_flows_report(Path(a.news),Path(a.sec13f_dir),day,sec13f_watchlist=Path(a.sec13f_watchlist),sec13f_summary=Path(a.sec13f_summary))
    (out/"trading-brief-latest.txt").write_text(trading,encoding="utf-8")
    (out/"capital-flows-latest.txt").write_text(capital,encoding="utf-8")
    (out/"trading-brief-audit.json").write_text(json.dumps(ta,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (out/"capital-flows-evidence.json").write_text(json.dumps(ce,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"TRADING_BRIEF_CANDIDATES={ta['accepted_count']}")
    print(f"TRADING_BRIEF_STATUS={ta['status']}")
    print(f"CAPITAL_FLOW_SIGNALS={len(ce['selected_news'])}")
    print(f"SEC_13F_REPORTS={len(ce['sec_13f_reports'])}")
    return 0

if __name__=="__main__": raise SystemExit(main())
