import httpx
import pytest

import paper_performance as paper


def _response(status=200, payload=None):
    request = httpx.Request("GET", "https://example.supabase.co/rest/v1/test")
    return (
        httpx.Response(status, json=payload, request=request)
        if payload is not None
        else httpx.Response(status, request=request)
    )


def test_fingerprint_is_stable_and_asset_date_scoped():
    first = paper.make_fingerprint("crypto:BTC", "2026-01-01")
    assert first == paper.make_fingerprint("crypto:BTC", "2026-01-01T00:00:00Z")
    assert first != paper.make_fingerprint("crypto:ETH", "2026-01-01")
    assert first != paper.make_fingerprint("crypto:BTC", "2026-01-02")
    assert len(first) == 64


def test_round_trip_cost_configuration_is_optional_and_validated():
    assert paper.resolve_round_trip_cost_bps("crypto", {}) is None
    assert paper.resolve_round_trip_cost_bps(
        "crypto", {"GRIOS_PAPER_COST_BPS_CRYPTO": "25"}
    ) == 25.0
    with pytest.raises(ValueError):
        paper.resolve_round_trip_cost_bps(
            "crypto", {"GRIOS_PAPER_COST_BPS_CRYPTO": "-1"}
        )
    with pytest.raises(ValueError):
        paper.resolve_round_trip_cost_bps(
            "crypto", {"GRIOS_PAPER_COST_BPS_CRYPTO": "10001"}
        )


def test_record_and_evaluate_persists_benchmark_excess_and_cost_adjusted_returns(monkeypatch):
    idea = {
        "id": "idea-1",
        "asset_key": "equity:NVDA",
        "data_as_of": "2026-01-01",
        "entry_price": 100,
        "benchmark_asset_key": "equity:SPY",
        "benchmark_entry_price": 200,
        "assumed_round_trip_cost_bps": 10,
        "decision": "WATCH_ONLY",
    }
    calls = []
    evaluation_payload = []

    def fake_request(method, url, *, params=None, json=None, headers=None, timeout=None):
        calls.append((method, url, params, json))
        if method == "POST" and url.endswith("/grios_paper_ideas"):
            return _response(201, [])
        if method == "GET" and url.endswith("/grios_paper_ideas"):
            return _response(200, [idea])
        if method == "GET" and url.endswith("/grios_paper_evaluations"):
            return _response(200, [])
        if method == "POST" and url.endswith("/grios_paper_evaluations"):
            evaluation_payload.extend(json)
            return _response(204)
        raise AssertionError(f"Unexpected request: {method} {url}")

    monkeypatch.setattr(paper.httpx, "request", fake_request)
    journal = paper.SupabasePaperJournal("https://example.supabase.co", "service-role")
    records = [
        {
            "asset_key": "equity:NVDA",
            "symbol": "NVDA",
            "asset_class": "us_equity_etf",
            "provider": "OpenBB",
            "data_as_of": "2026-01-02",
            "price": 110,
            "decision": "WATCH_ONLY",
            "technical_score": 70,
            "factor_coverage_pct": 100,
            "assumed_round_trip_cost_bps": 10,
        },
        {
            "asset_key": "equity:SPY",
            "symbol": "SPY",
            "asset_class": "us_equity_etf",
            "provider": "OpenBB",
            "data_as_of": "2026-01-02",
            "price": 210,
            "decision": "DATA_ONLY",
        },
    ]

    result = journal.record_and_evaluate(records, source_revision="a" * 40)

    assert result == {
        "ideas_seen": 1,
        "signals_inserted": 0,
        "evaluations_inserted": 1,
    }
    assert len(evaluation_payload) == 1
    evaluation = evaluation_payload[0]
    assert evaluation["checkpoint_days"] == 1
    assert evaluation["return_pct"] == pytest.approx(10.0)
    assert evaluation["benchmark_return_pct"] == pytest.approx(5.0)
    assert evaluation["excess_return_pct"] == pytest.approx(5.0)
    assert evaluation["estimated_cost_pct"] == pytest.approx(0.1)
    assert evaluation["net_return_pct"] == pytest.approx(9.9)
    assert evaluation["source_revision"] == "a" * 40


def test_performance_summary_separates_gross_excess_and_net(monkeypatch):
    rows = [
        {
            "checkpoint_days": 7,
            "return_pct": 5,
            "benchmark_return_pct": 2,
            "excess_return_pct": 3,
            "assumed_round_trip_cost_bps": 10,
            "net_return_pct": 4.9,
        },
        {
            "checkpoint_days": 7,
            "return_pct": -1,
            "benchmark_return_pct": 1,
            "excess_return_pct": -2,
            "assumed_round_trip_cost_bps": 10,
            "net_return_pct": -1.1,
        },
    ]

    def fake_request(method, url, *, params=None, json=None, headers=None, timeout=None):
        assert method == "GET"
        assert url.endswith("/grios_paper_evaluations")
        return _response(200, rows)

    monkeypatch.setattr(paper.httpx, "request", fake_request)
    journal = paper.SupabasePaperJournal("https://example.supabase.co", "service-role")
    summary = journal.performance_summary()

    checkpoint = summary["checkpoints"][7]
    assert summary["backend"] == "SUPABASE_PERSISTENT"
    assert checkpoint["sample_size"] == 2
    assert checkpoint["mean_return_pct"] == 2.0
    assert checkpoint["mean_excess_return_pct"] == 0.5
    assert checkpoint["mean_net_return_pct"] == 1.9
    assert checkpoint["cost_configured_sample_size"] == 2
