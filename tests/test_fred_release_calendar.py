from datetime import date

from fred_release_calendar import (
    build_calendar_payload,
    match_release_catalog,
    normalize_release_dates,
    render_persian_report,
)


def test_match_release_catalog_uses_exact_official_names_and_reports_missing():
    releases = [
        {"id": 10, "name": "Consumer Price Index", "link": "https://www.bls.gov/cpi/"},
        {"id": 50, "name": "Employment Situation", "link": "https://www.bls.gov/"},
    ]
    matched, missing = match_release_catalog(releases)
    assert {item["release_id"] for item in matched} == {10, 50}
    assert "Consumer Price Index" in {item["release_name"] for item in matched}
    assert "Gross Domestic Product" in missing


def test_normalize_release_dates_keeps_only_future_window_and_date_only_semantics():
    release = {
        "release_id": 10,
        "release_name": "Consumer Price Index",
        "label_fa": "شاخص قیمت مصرف‌کننده (CPI)",
        "category": "inflation",
        "source_url": "https://www.bls.gov/cpi/",
    }
    rows = [
        {"release_id": 10, "date": "2026-11-04"},
        {"release_id": 10, "date": "2026-11-05"},
        {"release_id": 10, "date": "2026-11-19"},
        {"release_id": 10, "date": "2026-12-01"},
        {"release_id": 999, "date": "2026-11-10"},
    ]
    events = normalize_release_dates(release, rows, today=date(2026, 11, 5), horizon_days=14)
    assert [item["event_date"] for item in events] == ["2026-11-05", "2026-11-19"]
    assert events[0]["event_time"] is None
    assert events[0]["consensus"] is None
    assert events[0]["impact_score"] is None


def test_calendar_payload_and_persian_report_preserve_data_limitations():
    release = {
        "release_id": 50,
        "release_name": "Employment Situation",
        "label_fa": "گزارش وضعیت اشتغال آمریکا",
        "category": "labor",
        "source_url": "https://www.bls.gov/",
    }
    payload = build_calendar_payload(
        [release],
        {50: [{"release_id": 50, "date": "2026-11-06"}]},
        today=date(2026, 11, 5),
        horizon_days=14,
    )
    report = render_persian_report(payload)
    assert payload["event_count"] == 1
    assert "گزارش وضعیت اشتغال آمریکا" in report
    assert "ساعت انتشار" in report
    assert "اجماع بازار و نتیجه واقعی" in report
    assert "حدس نمی‌زند" in report
