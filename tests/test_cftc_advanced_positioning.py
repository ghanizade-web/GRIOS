from cftc_advanced_positioning import (
    DATASETS,
    build_market_series,
    normalize_rows,
    positioning_stats,
    render_persian_report,
)


def row(report_type="DISAGGREGATED", date="2026-01-13"):
    common = {
        "cftc_contract_market_code": "088691" if report_type == "DISAGGREGATED" else "13874A",
        "report_date_as_yyyy_mm_dd": date,
        "market_and_exchange_names": "GOLD - COMMODITY EXCHANGE INC." if report_type == "DISAGGREGATED" else "E-MINI S&P 500 - CME",
        "open_interest_all": "500000",
    }
    if report_type == "DISAGGREGATED":
        common.update({
            "prod_merc_positions_long": "90000",
            "prod_merc_positions_short": "180000",
            "swap_positions_long_all": "40000",
            "swap__positions_short_all": "30000",
            "m_money_positions_long_all": "150000",
            "m_money_positions_short_all": "80000",
            "other_rept_positions_long": "20000",
            "other_rept_positions_short": "10000",
            "nonrept_positions_long_all": "100000",
            "nonrept_positions_short_all": "100000",
        })
    else:
        common.update({
            "dealer_positions_long_all": "100000",
            "dealer_positions_short_all": "180000",
            "asset_mgr_positions_long": "220000",
            "asset_mgr_positions_short": "100000",
            "lev_money_positions_long": "70000",
            "lev_money_positions_short": "90000",
            "other_rept_positions_long": "20000",
            "other_rept_positions_short": "10000",
            "nonrept_positions_long_all": "90000",
            "nonrept_positions_short_all": "110000",
        })
    return common


def test_disaggregated_positions_are_mapped_to_cftc_participant_classes():
    rows = normalize_rows([row(), {**row(date="2026-01-06"), "m_money_positions_long_all": "140000"}], contract_code="088691", report_type="DISAGGREGATED")
    latest = rows[-1]
    assert latest["categories"]["managed_money"]["net"] == 70000
    assert latest["categories"]["producer_merchant"]["net"] == -90000
    assert latest["categories"]["swap_dealer"]["net"] == 10000


def test_tff_positions_are_mapped_to_financial_trader_classes():
    rows = normalize_rows([row("TFF")], contract_code="13874A", report_type="TFF")
    latest = rows[-1]
    assert latest["categories"]["asset_manager"]["net"] == 120000
    assert latest["categories"]["leveraged_funds"]["net"] == -20000
    assert latest["categories"]["dealer_intermediary"]["net"] == -80000


def test_normalize_rows_rejects_wrong_dataset_identity_and_missing_fields():
    try:
        normalize_rows([row()], contract_code="999999", report_type="DISAGGREGATED")
    except ValueError as exc:
        assert "different contract" in str(exc)
    else:
        raise AssertionError("wrong CFTC contract must be rejected")

    broken = row()
    broken["m_money_positions_long_all"] = None
    try:
        normalize_rows([broken], contract_code="088691", report_type="DISAGGREGATED")
    except ValueError as exc:
        assert "invalid numeric" in str(exc).lower()
    else:
        raise AssertionError("missing position must be rejected")


def test_positioning_stats_are_descriptive_and_stable():
    assert positioning_stats([1, 2, 3]) == {"percentile": 100.0, "z_score": 1.2247}
    assert positioning_stats([5, 5]) == {"percentile": 100.0, "z_score": 0.0}


def test_advanced_series_computes_weekly_change_and_open_interest_share():
    first = row(date="2026-01-06")
    first["m_money_positions_long_all"] = "140000"
    second = row(date="2026-01-13")
    series = build_market_series(
        {"report_type": "DISAGGREGATED", "market": "Gold", "symbol": "GC", "contract_market_code": "088691"},
        normalize_rows([first, second], contract_code="088691", report_type="DISAGGREGATED"),
    )
    managed = series["extra"]["categories"]["managed_money"]
    assert managed["net"] == 70000
    assert managed["weekly_net_change"] == 10000
    assert managed["net_as_pct_open_interest"] == 14.0


def test_persian_report_labels_participant_categories_and_discloses_limits():
    series = build_market_series(
        {"report_type": "TFF", "market": "E-mini S&P 500", "symbol": "ES", "contract_market_code": "13874A"},
        normalize_rows([row("TFF")], contract_code="13874A", report_type="TFF"),
    )
    report = render_persian_report(
        [series],
        generated_at="2026-11-06T23:00:00+00:00",
        publish_result={"status": "DIRECT_SUPABASE", "accepted": 1},
    )
    assert "مدیران دارایی و نهادهای سرمایه‌گذاری" in report
    assert "صندوق‌های اهرمی" in report
    assert "معاملات لحظه‌ای" in report
    assert "Futures Only" in report
    assert "https://farcaster.xyz/drghanizade" in report


def test_dataset_ids_are_cftc_futures_only_reports():
    assert DATASETS["DISAGGREGATED"]["dataset_id"] == "72hh-3qpy"
    assert DATASETS["TFF"]["dataset_id"] == "gpe5-46if"
