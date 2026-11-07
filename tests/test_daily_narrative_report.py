from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace

from daily_narrative_report import render_daily_narrative_report


def _series(symbol, asset_class, closes, *, extra=None, data_as_of=None):
    today = date.today()
    return SimpleNamespace(
        symbol=symbol,
        name=symbol,
        asset_class=asset_class,
        currency="USD",
        observations=[
            {"date": (today - timedelta(days=len(closes) - index - 1)).isoformat(), "close": value}
            for index, value in enumerate(closes)
        ],
        data_as_of=data_as_of or today.isoformat(),
        observed_at=datetime.now(timezone.utc).isoformat(),
        extra=extra or {},
    )


def test_daily_report_is_narrative_not_a_raw_score_dump():
    series = [
        _series("SPY", "us_equity_etf", [100 + index * 0.2 for index in range(60)]),
        _series("QQQ", "us_equity_etf", [100 + index * 0.1 for index in range(60)]),
        _series("VIXCLS", "macro", [20 + index * 0.05 for index in range(60)]),
        _series("DGS10", "macro", [4 + index * 0.001 for index in range(60)]),
        _series("DGS2", "macro", [4.2 + index * 0.001 for index in range(60)]),
        _series("DTWEXBGS", "macro", [120 + index * 0.1 for index in range(60)]),
        _series("BTC", "crypto", [10000], extra={"change_24h": -2.4, "change_7d": -4.1}),
        _series("ETH", "crypto", [3000], extra={"change_24h": -3.2, "change_7d": -5.0}),
        _series("GLD", "commodity_proxy", [180 + index * 0.1 for index in range(60)]),
        _series("USO", "commodity_proxy", [70 - index * 0.1 for index in range(60)]),
        _series("EURUSD", "fx_reference", [1.1 + index * 0.001 for index in range(60)]),
    ]
    report = render_daily_narrative_report(series, [], {}, macro_calendar_path=None)
    assert "نقشه معاملات امروز" in report
    assert "وضعیت بازار" in report
    assert "تصمیم سریع" in report
    assert "قانون ریسک" in report
    assert len(report) < 5000
    assert "جمع‌بندی پوشش داده" not in report
    assert "امتیاز آزمایشی" not in report
    assert "https://t.me/drghanizade" in report


def test_risk_off_label_requires_cross_asset_confirmation():
    series = [
        _series("SPY", "us_equity_etf", [100 - index * 0.2 for index in range(60)]),
        _series("QQQ", "us_equity_etf", [100 - index * 0.3 for index in range(60)]),
        _series("VIXCLS", "macro", [15 + index * 0.1 for index in range(60)]),
        _series("BTC", "crypto", [10000], extra={"change_24h": -2.5, "change_7d": -4.0}),
    ]
    report = render_daily_narrative_report(series, [], {}, macro_calendar_path=None)
    assert "احتیاط و کاهش اشتهای ریسک" in report


def test_official_calendar_events_are_included_without_inventing_consensus(tmp_path):
    calendar = tmp_path / "calendar.json"
    calendar.write_text(json.dumps({"events": [{
        "event_date": "2026-11-10",
        "official_release_name": "Consumer Price Index",
        "release_id": 10,
    }]}), encoding="utf-8")
    report = render_daily_narrative_report([], [], {}, macro_calendar_path=calendar)
    assert "رویدادی که می‌تواند معامله را تغییر دهد" in report
    assert "شاخص قیمت مصرف‌کننده (CPI)" in report
    assert "۱۹ آبان ۱۴۰۵" in report
    assert "Consumer Price Index" not in report


def test_stale_data_does_not_create_a_directional_market_story():
    old = (date.today() - timedelta(days=90)).isoformat()
    series = [_series("SPY", "us_equity_etf", [100, 90], data_as_of=old)]
    report = render_daily_narrative_report(series, [], {}, macro_calendar_path=None)
    assert "رژیم ریسک با اطمینان کافی قابل تشخیص نیست" in report
    assert "سهام آمریکا و فناوری" not in report



def test_report_hides_routine_market_numbers_and_explains_verified_catalysts(tmp_path):
    now = datetime.now(timezone.utc)
    news = tmp_path / "news.json"
    news.write_text(json.dumps({
        "status": "FULL",
        "retrieved_at": now.isoformat(),
        "items": [{
            "title": "Data center investment expands as chip demand grows",
            "summary": "Large technology companies are increasing data center investment.",
            "url": "https://www.reuters.com/technology/example",
            "publisher": "Reuters",
            "domain": "reuters.com",
            "published_at": now.isoformat(),
            "evidence_tier": "TIER_2",
            "topics": ["ai_semiconductors"],
        }],
    }), encoding="utf-8")
    series = [
        _series("SPY", "us_equity_etf", [100 + index * 0.2 for index in range(60)]),
        _series("QQQ", "us_equity_etf", [100 + index * 0.3 for index in range(60)]),
        _series("BTC", "crypto", [10000], extra={"change_24h": 2.4, "change_7d": 4.1}),
        _series("ETH", "crypto", [3000], extra={"change_24h": 3.2, "change_7d": 5.0}),
        _series("VIXCLS", "macro", [20 - index * 0.05 for index in range(60)]),
    ]
    report = render_daily_narrative_report(series, [], {}, macro_calendar_path=None, news_intelligence_path=news)
    assert "علت" not in report or "علت‌ومعلولی" in report
    assert "هوش مصنوعی" in report
    assert "بازده اقتصادی" in report
    assert "Reuters" in report
    assert "https://www.reuters.com/technology/example" in report
    assert "تصمیم سریع" in report
    assert "سناریوی صعودی" not in report
    assert "$" not in report
    assert "٪" not in report



def test_report_explains_weekly_cftc_positioning_without_printing_position_numbers(tmp_path):
    now = datetime.now(timezone.utc)
    cftc = tmp_path / "cftc.json"
    cftc.write_text(json.dumps({
        "status": "FULL",
        "retrieved_at": now.isoformat(),
        "items": [{
            "symbol": "GC",
            "name": "Gold",
            "asset_key": "cftc:disaggregated_futures_only:088691",
            "data_as_of": date.today().isoformat(),
            "report_type": "Disaggregated Futures Only",
            "source_url": "https://publicreporting.cftc.gov/Commitments-of-Traders/Disaggregated-Futures-Only/72hh-3qpy",
            "categories": {
                "managed_money": {"label_fa": "مدیران سرمایه", "net": 10000, "weekly_net_change": -800, "historical_percentile": 95},
                "producer_merchant": {"label_fa": "تولیدکنندگان", "net": -3000, "weekly_net_change": 200, "historical_percentile": 50},
            },
        }],
    }), encoding="utf-8")
    report = render_daily_narrative_report([], [], {}, macro_calendar_path=None, news_intelligence_path=None, cftc_context_path=cftc)
    assert "هشدار موقعیت‌گیری نهادی" in report
    assert "معامله‌گران اهرمی/مدیریت‌شده" in report
    assert "خالص خرید" in report
    assert "در حال کاهش" in report
    assert "فیوچرز" in report or "Futures Only" in report
    assert "۱۰۰۰۰" not in report
    assert "800" not in report



def test_report_covers_bonds_global_equities_and_agriculture_proxies():
    series = [
        _series("SPY", "us_equity_etf", [100 + index * 0.2 for index in range(60)]),
        _series("QQQ", "us_equity_etf", [100 + index * 0.2 for index in range(60)]),
        _series("TLT", "us_equity_etf", [100 + index * 0.2 for index in range(60)]),
        _series("IEF", "us_equity_etf", [100 + index * 0.1 for index in range(60)]),
        _series("HYG", "us_equity_etf", [100 - index * 0.1 for index in range(60)]),
        _series("LQD", "us_equity_etf", [100 + index * 0.1 for index in range(60)]),
        _series("EFA", "us_equity_etf", [100 + index * 0.1 for index in range(60)]),
        _series("EEM", "us_equity_etf", [100 + index * 0.1 for index in range(60)]),
        _series("DBA", "commodity_proxy", [100 + index * 0.1 for index in range(60)]),
        _series("DBB", "commodity_proxy", [100 + index * 0.1 for index in range(60)]),
    ]
    report = render_daily_narrative_report(series, [], {}, macro_calendar_path=None, news_intelligence_path=None, cftc_context_path=None)
    assert "نقشه معاملات امروز" in report
    assert "تصمیم سریع" in report
    assert len(report) < 5000
    assert "چرخش سرمایه میان بخش‌ها و مناطق" not in report

def test_safe_headline_suppresses_market_figures_but_keeps_clean_titles():
    from daily_narrative_report import _safe_headline
    assert _safe_headline({"title": "How Wall Street’s all-in bet on AI blew up"}) == "How Wall Street’s all-in bet on AI blew up"
    assert _safe_headline({"title": "Bitcoin rebounds to $76,000 after selloff"}) is None
    assert _safe_headline({"title": "Oil rises 2.4% as supply concerns grow"}) is None


def test_source_reference_list_deduplicates_by_publisher_not_aggregator_domain():
    from daily_narrative_report import _story_refs
    items = [
        {"publisher": "Reuters", "domain": "news.google.com", "url": "https://news.google.com/reuters", "topics": ["geopolitics"]},
        {"publisher": "Bloomberg", "domain": "news.google.com", "url": "https://news.google.com/bloomberg", "topics": ["energy"]},
        {"publisher": "Reuters", "domain": "news.google.com", "url": "https://news.google.com/reuters-2", "topics": ["markets"]},
    ]
    refs = _story_refs(items, limit=5)
    assert len(refs) == 2
    assert "Reuters" in refs[0]
    assert "Bloomberg" in refs[1]
