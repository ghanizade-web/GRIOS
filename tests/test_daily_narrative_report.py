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
    assert "نمای کلان بازار" in report
    assert "سناریوی صعودی" in report
    assert "جمع‌بندی پوشش داده" not in report
    assert "امتیاز آزمایشی" not in report
    assert "توصیه شخصی خرید/فروش" in report
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
    assert "رویدادهای اقتصادی پیش‌رو" in report
    assert "Consumer Price Index" in report
    assert "اجماع بازار" in report
    assert "رقم واقعی" in report


def test_stale_data_does_not_create_a_directional_market_story():
    old = (date.today() - timedelta(days=90)).isoformat()
    series = [_series("SPY", "us_equity_etf", [100, 90], data_as_of=old)]
    report = render_daily_narrative_report(series, [], {}, macro_calendar_path=None)
    assert "رژیم ریسک با اطمینان کافی قابل تشخیص نیست" in report
    assert "سهام آمریکا و فناوری" not in report
