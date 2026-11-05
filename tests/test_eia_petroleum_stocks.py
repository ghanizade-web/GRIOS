from eia_petroleum_stocks import (
    EIA_SERIES,
    build_persian_report,
    historical_percentile,
    normalize_observations,
)


def test_normalize_observations_orders_deduplicates_and_limits():
    rows = [
        {"period": "2026-01-14", "value": "110"},
        {"period": "2026-01-07", "value": "100"},
        {"period": "2026-01-14", "value": "110"},
        {"period": "2026-01-21", "value": "120"},
    ]
    result = normalize_observations(rows, limit=2)
    assert result == [
        {"date": "2026-01-14", "value": 110.0},
        {"date": "2026-01-21", "value": 120.0},
    ]


def test_normalize_observations_rejects_invalid_values():
    try:
        normalize_observations([{"period": "2026-01-07", "value": "NaN"}])
    except ValueError as exc:
        assert "not finite" in str(exc)
    else:
        raise AssertionError("non-finite inventory value must be rejected")


def test_historical_percentile_is_empirical_and_deterministic():
    assert historical_percentile([10, 20, 30, 40, 50]) == 100.0
    assert historical_percentile([10, 20, 30, 40, 30]) == 60.0
    assert historical_percentile([]) is None


def test_eia_watchlist_uses_known_weekly_inventory_series():
    assert {item["series_id"] for item in EIA_SERIES} == {
        "PET.WCESTUS1.W",
        "PET.WGTSTUS1.W",
        "PET.WDISTUS1.W",
    }


def test_persian_report_discloses_no_consensus_or_causal_claim():
    item = {
        "symbol": "EIA_CRUDE_STOCKS",
        "data_as_of": "2026-10-23",
        "extra": {
            "latest_value": 410000,
            "weekly_change": -5000,
            "weekly_change_pct": -1.2,
            "historical_percentile": 20.0,
            "source_url": "https://www.eia.gov/",
        },
    }
    report = build_persian_report(
        [item],
        generated_at="2026-11-05T00:00:00+00:00",
        publish_result={"status": "DIRECT_SUPABASE", "accepted": 1},
    )
    assert "موجودی نفت و فرآورده‌های آمریکا" in report
    assert "اجماع تحلیلگران" in report
    assert "به‌تنهایی جهت قیمت نفت را تعیین نمی‌کند" in report
