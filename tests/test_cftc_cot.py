from cftc_cot import build_market_series, normalize_rows, positioning_stats


def sample_rows():
    return [
        {
            "cftc_contract_market_code": "088691",
            "report_date_as_yyyy_mm_dd": "2026-01-06T00:00:00.000",
            "market_and_exchange_names": "GOLD - COMMODITY EXCHANGE INC.",
            "open_interest_all": "500000",
            "noncomm_positions_long_all": "200000",
            "noncomm_positions_short_all": "100000",
            "comm_positions_long_all": "90000",
            "comm_positions_short_all": "190000",
        },
        {
            "cftc_contract_market_code": "088691",
            "report_date_as_yyyy_mm_dd": "2026-01-13T00:00:00.000",
            "market_and_exchange_names": "GOLD - COMMODITY EXCHANGE INC.",
            "open_interest_all": "510000",
            "noncomm_positions_long_all": "220000",
            "noncomm_positions_short_all": "90000",
            "comm_positions_long_all": "85000",
            "comm_positions_short_all": "205000",
        },
    ]


def test_normalize_rows_calculates_net_positions_and_orders_dates():
    rows = normalize_rows(list(reversed(sample_rows())), contract_code="088691", market_label="Gold")
    assert [row["report_date"] for row in rows] == ["2026-01-06", "2026-01-13"]
    assert rows[-1]["noncommercial_net"] == 130000
    assert rows[-1]["commercial_net"] == -120000


def test_normalize_rows_rejects_wrong_contract_identity():
    rows = sample_rows()
    rows[0]["cftc_contract_market_code"] = "999999"
    try:
        normalize_rows(rows, contract_code="088691", market_label="Gold")
    except ValueError as exc:
        assert "different contract" in str(exc)
    else:
        raise AssertionError("wrong contract identity must be rejected")


def test_positioning_stats_handles_percentile_and_zero_variance():
    assert positioning_stats([1, 2, 3]) == {"percentile": 100.0, "z_score": 1.2247}
    assert positioning_stats([5, 5]) == {"percentile": 100.0, "z_score": 0.0}


def test_build_market_series_preserves_weekly_disclosure_caveats():
    rows = normalize_rows(sample_rows(), contract_code="088691", market_label="Gold")
    item = build_market_series({"market": "Gold", "symbol": "XAU"}, rows)
    assert item["data_as_of"] == "2026-01-13"
    assert item["extra"]["noncommercial"]["weekly_net_change"] == 40000
    assert item["extra"]["publication_date"] is None
    assert "not transaction records" in item["caveat"]
