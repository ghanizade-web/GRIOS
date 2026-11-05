from scanner import (
    MarketSeries,
    build_paper_performance_records,
    ensure_db,
    market_score,
    performance_summary,
    render_performance_summary,
)


def test_performance_summary_calculates_forward_tracking_metrics(tmp_path):
    db = ensure_db(tmp_path / "forward.sqlite3")
    try:
        db.executemany(
            """INSERT INTO ideas
            (id,asset_key,symbol,asset_class,source,data_as_of,recorded_at,
             price,technical_score,factor_coverage_pct,decision,thesis,invalidation)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            [
                (1,'BTC','BTC','crypto','provider','2026-01-01','2026-01-01T00:00:00Z',100,70,100,'WATCH_ONLY','test','test'),
                (2,'ETH','ETH','crypto','provider','2026-01-01','2026-01-01T00:00:00Z',100,70,100,'WATCH_ONLY','test','test'),
                (3,'SOL','SOL','crypto','provider','2026-01-01','2026-01-01T00:00:00Z',100,70,100,'WATCH_ONLY','test','test'),
            ],
        )
        db.executemany(
            """INSERT INTO evaluations
            (id,idea_id,checkpoint_days,evaluated_at,observed_at,price,return_pct)
            VALUES (?,?,?,?,?,?,?)""",
            [
                (1, 1, 1, "2026-01-02T00:00:00Z", "2026-01-02", 99, -1.0),
                (2, 2, 1, "2026-01-03T00:00:00Z", "2026-01-03", 102, 2.0),
                (3, 3, 1, "2026-01-04T00:00:00Z", "2026-01-04", 103, 3.0),
                (4, 1, 7, "2026-01-09T00:00:00Z", "2026-01-09", 104, 4.0),
            ],
        )
        db.commit()
        result = performance_summary(db)
    finally:
        db.close()

    assert result["status"] == "AVAILABLE"
    assert result["total_evaluations"] == 4
    assert result["checkpoints"][1]["sample_size"] == 3
    assert result["checkpoints"][1]["mean_return_pct"] == 1.333
    assert result["checkpoints"][1]["win_rate_pct"] == 66.67
    assert result["checkpoints"][7]["median_return_pct"] == 4.0


def test_performance_report_warns_when_sample_is_small():
    lines = render_performance_summary({
        "checkpoints": {
            7: {
                "sample_size": 2,
                "mean_return_pct": 1.5,
                "median_return_pct": 1.5,
                "win_rate_pct": 100.0,
                "best_return_pct": 2.0,
                "worst_return_pct": 1.0,
            }
        }
    })
    rendered = "\\n".join(lines)
    assert "Forward Paper Tracking" in rendered
    assert "نمونه کمتر از ۱۰" in rendered
    assert "هزینه رفت‌وبرگشت هنوز" in rendered


def test_performance_report_handles_no_matured_evaluations():
    lines = render_performance_summary({"checkpoints": {}})
    assert any("هنوز ارزیابی سررسیدشده‌ای" in line for line in lines)



def test_paper_records_match_same_date_spy_and_keep_dbc_as_reference():
    today = __import__("datetime").date.today().isoformat()
    nvda = MarketSeries(
        key="equity:NVDA", symbol="NVDA", name="NVIDIA",
        asset_class="us_equity_etf", instrument="equity", provider="OpenBB",
        feed_class="daily", currency="USD",
        observations=[{"date": today, "close": 100}],
        data_as_of=today,
    )
    spy = MarketSeries(
        key="equity:SPY", symbol="SPY", name="S&P 500",
        asset_class="us_equity_etf", instrument="ETF", provider="OpenBB",
        feed_class="daily", currency="USD",
        observations=[{"date": today, "close": 500}],
        data_as_of=today,
    )
    dbc = MarketSeries(
        key="commodity:DBC", symbol="DBC", name="Broad Commodity ETF",
        asset_class="commodity_proxy", instrument="ETF", provider="OpenBB",
        feed_class="daily", currency="USD",
        observations=[{"date": today, "close": 20}],
        data_as_of=today,
    )
    scores = {
        nvda.key: {"score": 75, "coverage": 100, "decision": "WATCH_ONLY", "why": "test"},
        spy.key: {"score": 70, "coverage": 100, "decision": "WATCH_ONLY", "why": "benchmark"},
        dbc.key: market_score(dbc),
    }

    records, warnings = build_paper_performance_records([nvda, spy, dbc], scores)
    by_key = {item["asset_key"]: item for item in records}

    assert warnings == []
    assert by_key[nvda.key]["benchmark_symbol"] == "SPY"
    assert by_key[nvda.key]["benchmark_asset_key"] == spy.key
    assert by_key[nvda.key]["benchmark_entry_price"] == 500
    assert by_key[spy.key]["benchmark_asset_key"] is None
    assert by_key[dbc.key]["decision"] == "DATA_ONLY"
