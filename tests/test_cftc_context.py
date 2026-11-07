from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import cftc_context


def _row(symbol="GC", key="cftc:disaggregated_futures_only:088691", report_date=None):
    report_date = report_date or date.today().isoformat()
    return {
        "symbol": symbol,
        "name": "Gold futures",
        "asset_key": key,
        "data_as_of": report_date,
        "extra": {
            "report_type": "Disaggregated Futures Only",
            "source_url": "https://publicreporting.cftc.gov/Commitments-of-Traders/Disaggregated-Futures-Only/72hh-3qpy",
            "categories": {
                "managed_money": {"net": 12000, "weekly_net_change": -900, "historical_percentile": 91.0, "label_fa": "مدیران سرمایه"},
                "producer_merchant": {"net": -3000, "weekly_net_change": 400, "historical_percentile": 55.0, "label_fa": "تولیدکنندگان"},
            },
        },
    }


def test_normalize_cftc_rows_keeps_fresh_valid_futures_only_data():
    result = cftc_context.normalize_cftc_rows([_row()], today=date.today())
    assert result["status"] == "PARTIAL"
    assert len(result["items"]) == 1
    item = result["items"][0]
    assert item["symbol"] == "GC"
    assert item["categories"]["managed_money"]["net"] == 12000
    assert item["categories"]["managed_money"]["weekly_net_change"] == -900


def test_normalize_rejects_stale_and_unapproved_rows():
    stale = _row(report_date=(date.today() - timedelta(days=20)).isoformat())
    legacy = _row(key="cftc:legacy_futures_only:088691")
    assert cftc_context.normalize_cftc_rows([stale, legacy])["items"] == []


def test_fetch_uses_service_role_only_and_never_logs_secret():
    class Response:
        def raise_for_status(self):
            return None
        def json(self):
            return [_row()]
    class Client:
        def __init__(self):
            self.kwargs = None
        def get(self, url, **kwargs):
            self.kwargs = (url, kwargs)
            return Response()
    client = Client()
    result = cftc_context.fetch_cftc_context("https://db.example", "secret-token", client)
    url, kwargs = client.kwargs
    assert url == "https://db.example/rest/v1/grios_market_observations"
    assert kwargs["headers"]["apikey"] == "secret-token"
    assert kwargs["headers"]["Authorization"] == "Bearer secret-token"
    assert kwargs["params"]["asset_class"] == "eq.futures_positioning"
    assert result["items"][0]["symbol"] == "GC"


def test_missing_service_role_configuration_degrades_safely(monkeypatch):
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)
    result = cftc_context.fetch_cftc_context(service_role_key="")
    assert result["status"] == "UNAVAILABLE"
    assert result["items"] == []
