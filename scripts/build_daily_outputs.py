from __future__ import annotations
import argparse, json, re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse

SOCIAL = [
    "Instagram: https://www.instagram.com/dr.ghanizade",
    "X: https://x.com/DrGhanizadeh",
    "LinkedIn: https://www.linkedin.com/in/drghanizade",
    "Farcaster: https://farcaster.xyz/drghanizade",
    "GitHub: https://github.com/ghanizade-web",
]
ELIGIBLE = {"crypto", "fx", "commodity"}
REQUIRED = {"instrument","asset_class","direction","price","price_type","provider","timestamp","catalyst","catalyst_date","transmission","trigger","invalidation","horizon","risk","evidence_grade","sources"}
THEMES = {
 "critical_materials": ("copper","lithium","uranium","rare earth","gallium","germanium","antimony","tungsten","platinum","palladium","rhodium","graphite","nickel","cobalt","critical mineral"),
 "ai_compute": ("artificial intelligence","data center","datacenter","hyperscaler","gpu","semiconductor","chip","high-bandwidth memory","hbm","advanced packaging","optical interconnect"),
 "power_energy": ("nuclear","small modular reactor","smr","power grid","transformer","switchgear","electricity demand","energy storage","lng","natural gas"),
 "defense_aerospace": ("defense","defence","aerospace","drone","unmanned","missile","satellite","space infrastructure"),
 "robotics_autonomy": ("robotics","robot","autonomous","automation","self-driving"),
 "industrial_capex": ("capex","capital expenditure","procurement","purchase order","supply agreement","offtake","long-term contract","factory","mine development","processing plant","production capacity","construction contract","government award"),
 "institutional_capital": ("institutional investor","asset manager","sovereign wealth","13f","fund flow","etf flow","portfolio holding","stake","acquisition","investment","funding round"),
}
CAPITAL_WORDS = ("capex","capital expenditure","procurement","purchase order","supply agreement","offtake","contract","acquisition","investment","funding","financing","stake","award","factory","mine development","production capacity","order book")

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

def validate_candidate(item):
    if not isinstance(item,dict): return False,"candidate_not_object"
    missing=REQUIRED-set(item)
    if missing: return False,"missing:"+",".join(sorted(missing))
    if str(item["asset_class"]).lower() not in ELIGIBLE: return False,"ineligible_asset_class"
    direction=str(item["direction"]).upper()
    if direction not in {"LONG","SHORT","WATCH"}: return False,"invalid_direction"
    try:
        if float(item["price"])<=0: return False,"invalid_price"
    except (TypeError,ValueError): return False,"invalid_price"
    if parse_time(item["timestamp"]) is None: return False,"timestamp_must_be_timezone_aware"
    try: date.fromisoformat(str(item["catalyst_date"]))
    except ValueError: return False,"invalid_catalyst_date"
    grade=str(item["evidence_grade"]).upper()
    if grade not in {"A","B","C"}: return False,"invalid_evidence_grade"
    if grade=="C" and direction!="WATCH": return False,"grade_c_must_be_watch"
    if not isinstance(item["sources"],list) or not item["sources"] or not all(https(x) for x in item["sources"]): return False,"sources_must_be_https"
    for key in ("instrument","price_type","provider","catalyst","transmission","trigger","invalidation","horizon","risk"):
        if not str(item.get(key,"")).strip(): return False,"empty:"+key
    return True,"valid"

def build_trading_brief(candidate_path, report_date):
    payload=read_json(candidate_path); raw=payload.get("candidates",[]) if payload else []
    if not isinstance(raw,list): raw=[]
    accepted=[]; rejected=[]
    for item in raw:
        ok,reason=validate_candidate(item)
        (accepted if ok else rejected).append(item if ok else {"instrument":item.get("instrument") if isinstance(item,dict) else None,"reason":reason})
    lines=[f"GRIOS v15 — گزارش روزانه فرصت‌های معاملاتی | {report_date}","محدوده مجاز: رمزارزها، ارزها و کالاها؛ سهام و ETFهای سهامی نامزد معامله نیستند.","Eligible universe: Crypto / FX / Commodities only. Equities and equity ETFs are excluded.",""]
    if not accepted:
        lines += ["**هیچ معاملهٔ تأییدشده‌ای وجود ندارد؛ فعلاً فقط زیر نظر بمانید.**","**No confirmed trade; monitor only.**","No candidate passed all mandatory checks for a fresh catalyst, timestamped quote, causal transmission, observable trigger, invalidation, risk, evidence grade and source.","از دادهٔ ناقص اسکنر، نقطهٔ ورود، حد ضرر، هدف یا جهت معاملاتی استنباط نمی‌شود.","No entry, stop, target or direction is inferred from incomplete scanner output.",""]
    else:
        lines.append(f"Qualified candidates: {len(accepted)}. The 10-item target is not a fabrication quota.")
        for n,x in enumerate(accepted[:20],1):
            lines += [f"{n}. **{x['instrument']} — {str(x['direction']).upper()}**",f"Price: {x['price']} | {x['price_type']} | {x['provider']} | {x['timestamp']}",f"Catalyst ({x['catalyst_date']}): {x['catalyst']}",f"Transmission: {x['transmission']}",f"Trigger: {x['trigger']}",f"Invalidation: {x['invalidation']}",f"Horizon / Risk / Evidence: {x['horizon']} / {x['risk']} / {str(x['evidence_grade']).upper()}",""]
    if len(accepted)<10: lines.append(f"Coverage note: {len(accepted)} qualified candidate(s); fewer than the 10-item target. No weak or duplicate ideas were added.")
    if rejected: lines.append(f"Rejected candidate records: {len(rejected)}; reasons retained in the audit artifact.")
    lines += ["","پیوندهای شبکه‌های اجتماعی:","Social links:",*SOCIAL]
    audit={"schema_version":"1.0","report_type":"catalyst_driven_trading_brief","report_date":report_date,"accepted_count":len(accepted),"accepted_candidates":accepted,"rejected":rejected,"status":"NO_CONFIRMED_TRADE" if not accepted else "VALIDATED_CANDIDATES"}
    return "\n".join(lines)+"\n",audit

def _fresh_items(payload, now):
    retrieved=parse_time(payload.get("retrieved_at"))
    if retrieved is None or now-retrieved>timedelta(hours=30) or retrieved>now+timedelta(minutes=10): return []
    items=payload.get("items",[]); cutoff=now-timedelta(hours=72); out=[]
    if not isinstance(items,list): return []
    for item in items:
        if not isinstance(item,dict) or not https(item.get("url")) or not str(item.get("title","")).strip(): continue
        published=parse_time(item.get("published_at"))
        if published is None or published<cutoff or published>now+timedelta(hours=6): continue
        text=f"{item.get('title','')} {item.get('summary','')}".casefold()
        themes=[name for name,terms in THEMES.items() if any(term in text for term in terms)]
        if not themes: continue
        capital=any(term in text for term in CAPITAL_WORDS)
        out.append({**item,"_published":published,"_themes":themes,"_capital":capital})
    out.sort(key=lambda x:(x["_capital"],x.get("evidence_tier")=="TIER_1",x["_published"]),reverse=True)
    return out

def _load_13f(directory):
    reports=[]
    for path in sorted(Path(directory).glob("*.json")) if Path(directory).is_dir() else []:
        p=read_json(path)
        if not p or not p.get("report_period"): continue
        filings=p.get("applied_filings",[]); holdings=p.get("holdings",[])
        urls=[x.get("source_url") for x in filings if isinstance(x,dict) and https(x.get("source_url"))] if isinstance(filings,list) else []
        holdings=[x for x in holdings if isinstance(x,dict)] if isinstance(holdings,list) else []
        holdings.sort(key=lambda x:float(x.get("value_usd") or 0),reverse=True)
        reports.append({"manager":p.get("filer_name") or p.get("manager_name") or p.get("name") or path.stem,"report_period":p["report_period"],"filed_at":p.get("latest_filed_at"),"holdings_count":p.get("holdings_count",len(holdings)),"top_holdings":[{"issuer":x.get("issuer"),"value_usd":x.get("value_usd")} for x in holdings[:3]],"source_urls":urls})
    return reports

def build_capital_flows_report(news_path,sec13f_dir,report_date,now=None):
    now=(now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    news=read_json(news_path); stories=_fresh_items(news,now); reports=_load_13f(sec13f_dir)
    lines=[f"GRIOS v15 — گزارش جریان سرمایه راهبردی و مگاترندها | {report_date}","","هدف: ردیابی سرمایه نهادی، خریدهای بزرگ، CapEx، مواد راهبردی و گلوگاه‌های زنجیره تأمین.","","Objective: detect structural demand, supply bottlenecks and disclosed capital allocation before they become consensus narratives.","","اصل راستی‌آزمایی: تیتر خبر اثبات خرید تکمیل‌شده نیست؛ اعلام، امضا، تعهد، اجرا و تکمیل معامله وضعیت‌های متفاوت‌اند.","Evidence discipline: a headline is not proof of a completed purchase. Announced, signed, committed, in-progress and completed activity are distinct. Unknown amounts remain undisclosed.","","1) SEC Form 13F institutional disclosures"]
    if reports:
        for r in reports:
            lines.append(f"- {r['manager']}: report period {r['report_period']}; filing date {r.get('filed_at') or 'not supplied'}; {r['holdings_count']} disclosed holding rows.")
            for h in r["top_holdings"]:
                value=f"USD {float(h['value_usd']):,.0f}" if h.get("value_usd") is not None else "value not supplied"
                lines.append(f"  Top disclosed position: {h.get('issuer') or 'issuer not supplied'} — {value}.")
    else: lines.append("- No SEC 13F watchlist snapshot was available in this run; no institutional accumulation claim is made.")
    lines += ["محدودیت 13F: این داده تصویری فصلی و با تأخیر از مالکیت‌هاست؛ تاریخ معامله را مشخص نمی‌کند و خرید فعلی یا سرمایه‌گذاری اختصاصی مدیر را اثبات نمی‌کند. ممکن است دارایی صندوق‌های متعلق به مشتریان را نشان دهد.","13F limitation: quarterly, delayed holdings snapshots. They do not identify trade dates or prove current buying, short positions, beneficial ownership or a manager's proprietary investment. Managed client funds may be represented.","","2) Strategic demand, supply constraints and capital/procurement signals"]
    selected=stories[:15]
    if selected:
        for n,x in enumerate(selected,1):
            label="Reported capital/procurement signal; execution not independently established" if x["_capital"] else "Strategic industry/technology signal; no transaction inferred"
            lines += [f"{n}. **{x['title']}**",f"Source: {x.get('publisher') or x.get('domain') or 'publisher not supplied'} | Published: {x['_published'].isoformat()} | Evidence: {x.get('evidence_tier','UNRATED')}",f"Classification: {label} | Themes: {', '.join(x['_themes'])}",f"Available excerpt: {x.get('summary') or 'No source excerpt supplied; headline only.'}",""]
    else: lines.append("- No fresh source-attributed strategic-material, industrial-capex or technology signal passed the 72-hour evidence filter. This is not proof that no activity occurred.")
    lines += ["۳) فهرست پایش مواد راهبردی","مس، لیتیوم، اورانیوم، عناصر خاکی کمیاب، گالیوم، ژرمانیوم، آنتیموان، تنگستن، پلاتین، پالادیوم، رودیوم، گرافیت، نیکل و کبالت.","رادیوم و رودیوم دو عنصر متفاوت‌اند و نباید با یکدیگر اشتباه شوند.","3) Critical-material watchlist","Copper, lithium, uranium, rare earth elements, gallium, germanium, antimony, tungsten, platinum, palladium, rhodium, graphite, nickel and cobalt.","Radium and rhodium are different elements and must not be conflated.","","4) Research gaps and investment conversion","This run uses the configured RSS evidence and any available SEC 13F snapshots. It does not claim complete coverage of private contracts, purchase orders, all sovereign funds, all ETF flows or every corporate filing. Beneficiaries, valuation and investable instruments require separate issuer-level evidence; no company is named as a beneficiary solely by keyword association.","For each opportunity, verify the original filing or contract, execution status, amount and reporting period; map the value chain; test supply substitution and capacity; assess valuation, liquidity, geopolitical risk and thesis invalidation.","","Social links:",*SOCIAL]
    evidence={"schema_version":"1.0","report_type":"strategic_capital_flows_megatrends","report_date":report_date,"news_status":news.get("status","UNAVAILABLE"),"news_retrieved_at":news.get("retrieved_at"),"news_window_hours":news.get("window_hours",72),"selected_news":[{k:v for k,v in x.items() if not k.startswith("_")} for x in selected],"sec_13f_reports":reports,"limitations":["13F is a delayed quarterly holdings disclosure, not real-time flow.","RSS headline/excerpt is not full-text research or proof of execution.","Absence of a signal is not evidence of absence.","Beneficiary and valuation claims require issuer-level evidence."]}
    return "\n".join(lines)+"\n",evidence

def main():
    p=argparse.ArgumentParser(description="Build two evidence-gated GRIOS daily reports.")
    p.add_argument("--news",default="reports/news-intelligence-latest.json")
    p.add_argument("--trading-candidates",default="reports/trading-candidates-latest.json")
    p.add_argument("--sec13f-dir",default="reports/sec-13f-watchlist/reports")
    p.add_argument("--output-dir",default="reports")
    p.add_argument("--date",default=None)
    a=p.parse_args(); day=a.date or datetime.now(timezone.utc).date().isoformat(); out=Path(a.output_dir); out.mkdir(parents=True,exist_ok=True)
    trading,ta=build_trading_brief(Path(a.trading_candidates),day)
    capital,ce=build_capital_flows_report(Path(a.news),Path(a.sec13f_dir),day)
    (out/"trading-brief-en.txt").write_text(trading,encoding="utf-8")
    (out/"capital-flows-en.txt").write_text(capital,encoding="utf-8")
    (out/"trading-brief-audit.json").write_text(json.dumps(ta,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (out/"capital-flows-evidence.json").write_text(json.dumps(ce,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"TRADING_BRIEF_CANDIDATES={ta['accepted_count']}")
    print(f"TRADING_BRIEF_STATUS={ta['status']}")
    print(f"CAPITAL_FLOW_SIGNALS={len(ce['selected_news'])}")
    print(f"SEC_13F_REPORTS={len(ce['sec_13f_reports'])}")
    return 0

if __name__=="__main__": raise SystemExit(main())
