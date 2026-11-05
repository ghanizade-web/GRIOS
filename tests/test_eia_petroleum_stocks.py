from eia_petroleum_stocks import (
    EIA_SERIES,
    _validate_units,
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
        raise AssertionError("non-finite EIA value must be rejected")


def test_historical_percentile_is_empirical_and_deterministic():
    assert historical_percentile([10, 20, 30, 40, 50]) == 100.0
    assert historical_percentile([10, 20, 30, 40, 30]) == 80.0
    assert historical_percentile([]) is None


def test_eia_watchlist_contains_official_weekly_supply_demand_series():
    by_symbol = {item["symbol"]: item for item in EIA_SERIES}
    assert len(EIA_SERIES) == 9
    assert {
        "EIA_CRUDE_STOCKS",
        "EIA_GASOLINE_STOCKS",
        "EIA_DISTILLATE_STOCKS",
        "EIA_CRUDE_PRODUCTION",
        "EIA_CRUDE_IMPORTS",
        "EIA_CRUDE_EXPORTS",
        "EIA_REFINERY_CRUDE_INPUTS",
        "EIA_REFINERY_UTILIZATION",
        "EIA_TOTAL_PRODUCT_SUPPLIED",
    } == set(by_symbol)
    assert by_symbol["EIA_CRUDE_PRODUCTION"]["series_id"] == "PET.WCRFPUS2.W"
    assert by_symbol["EIA_CRUDE_IMPORTS"]["series_id"] == "PET.WCRIMUS2.W"
    assert by_symbol["EIA_CRUDE_EXPORTS"]["series_id"] == "PET.WCREXUS2.W"
    assert by_symbol["EIA_REFINERY_CRUDE_INPUTS"]["series_id"] == "PET.WCRRIUS2.W"
    assert by_symbol["EIA_REFINERY_UTILIZATION"]["series_id"] == "PET.WPULEUS3.W"
    assert by_symbol["EIA_TOTAL_PRODUCT_SUPPLIED"]["series_id"] == "PET.WRPUPUS2.W"


def test_eia_units_are_checked_against_series_contract():
    assert _validate_units("Percent", "percent", "PET.WPULEUS3.W") == "percent"
    assert _validate_units("Thousand Barrels per Day", "thousand barrels per day", "PET.WCRFPUS2.W") == "thousand barrels per day"
    try:
        _validate_units("thousand barrels", "percent", "PET.WPULEUS3.W")
    except ValueError as exc:
        assert "Unexpected EIA unit" in str(exc)
    else:
        raise AssertionError("mismatched EIA units must be rejected")


def test_persian_report_discloses_source_limits_and_data_type():
    item = {
        "symbol": "EIA_CRUDE_STOCKS",
        "units": "thousand barrels",
        "value_kind": "stock",
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
    assert "تراز عرضه و تقاضا" in report
    assert "اجماع تحلیلگران" in report
    assert "صدک‌ها بر اساس تاریخچه دریافت‌شده و بدون تعدیل فصلی" in report
    assert "سیگنال خریدوفروش نیست" in report
