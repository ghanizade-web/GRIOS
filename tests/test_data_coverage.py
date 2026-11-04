from datetime import datetime, timezone
from unittest.mock import patch
import json

from data_coverage import build_data_coverage_report, publish_market_series


class Item:
    def __init__(self, symbol, asset_class, observed_at="2026-11-04T20:00:00+00:00"):
        self.key = f"{asset_class}:{symbol}"
        self.symbol = symbol
        self.name = symbol
        self.asset_class = asset_class
        self.instrument = "spot"
        self.provider = "test-provider"
        self.feed_class = "test"
        self.currency = "USD"
        self.observed_at = observed_at
        self.data_as_of = "2026-11-04"
        self.caveat = None
        self.observations = [{"date": "2026-11-04", "close": 1.0}]
        self.extra = {}


def test_coverage_reports_missing_symbols_and_not_covered_capabilities():
    watchlist = {
        "crypto_symbols": ["BTC", "GRAM"],
        "us_equities_etfs": ["SPY"],
        "commodity_etf_proxies": [],
        "fx_reference_pairs": [],
        "crypto_universe": {"mode": "watchlist"},
    }
    rows = [Item("BTC", "crypto"), Item("SPY", "us_equity_etf")]
    report = build_data_coverage_report(watchlist, rows, now=datetime(2026, 11, 4, 20, 5, tzinfo=timezone.utc))
    assert report["feeds"]["crypto_spot"]["missing_symbols"] == ["GRAM"]
    assert report["feeds"]["crypto_spot"]["coverage_pct"] == 50.0
    assert report["feeds"]["us_equities_etfs"]["status"] == "COMPLETE"
    assert "verified_institutional_fund_flows" in report["capabilities_not_implemented"]


def test_coverage_marks_old_observation_stale():
    watchlist = {"crypto_symbols": ["BTC"], "crypto_universe": {"mode": "watchlist"}}
    rows = [Item("BTC", "crypto", "2026-11-04T18:00:00+00:00")]
    report = build_data_coverage_report(watchlist, rows, now=datetime(2026, 11, 4, 20, 5, tzinfo=timezone.utc))
    assert report["feeds"]["crypto_spot"]["status"] == "STALE"
    assert report["feeds"]["crypto_spot"]["stale_symbols"] == ["BTC"]


def test_discovery_mode_does_not_fabricate_expected_denominator():
    watchlist = {"crypto_symbols": [], "crypto_universe": {"mode": "discovery"}}
    report = build_data_coverage_report(watchlist, [Item("BTC", "crypto")])
    assert report["feeds"]["crypto_spot"]["status"] == "DISCOVERY_MODE"
    assert report["feeds"]["crypto_spot"]["coverage_pct"] is None


def test_data_hub_publish_is_explicitly_not_configured_without_credentials():
    with patch.dict("os.environ", {}, clear=True):
        result = publish_market_series([Item("BTC", "crypto")])
    assert result["status"] == "NOT_CONFIGURED"
    assert result["accepted"] == 0


def test_data_hub_publish_posts_versioned_payload_without_logging_token():
    captured = {}
    class FakeResponse:
        status = 202
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def read(self): return b'{"status":"accepted","accepted":1}'
    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["headers"] = dict(request.header_items())
        captured["payload"] = json.loads(request.data.decode())
        return FakeResponse()
    with patch.dict("os.environ", {"GRIOS_DATA_HUB_URL":"https://hub.example", "GRIOS_DATA_HUB_TOKEN":"never-log-this"}):
        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            result = publish_market_series([Item("BTC", "crypto")], "commit-sha")
    assert result["status"] == "CONNECTED"
    assert result["accepted"] == 1
    assert captured["payload"]["schema_version"] == "1.0"
    assert captured["payload"]["source_revision"] == "commit-sha"
    assert "never-log-this" not in json.dumps(result)



def test_data_hub_publish_classifies_cloudflare_403_challenge_without_leaking_body():
    from email.message import Message
    from urllib.error import HTTPError

    headers = Message()
    headers["Server"] = "cloudflare"
    headers["Content-Type"] = "text/html; charset=UTF-8"
    headers["cf-mitigated"] = "challenge"

    def fail_urlopen(request, timeout):
        raise HTTPError(
            request.full_url,
            403,
            "Forbidden",
            hdrs=headers,
            fp=None,
        )

    with patch.dict("os.environ", {
        "GRIOS_DATA_HUB_URL": "https://hub.example",
        "GRIOS_DATA_HUB_TOKEN": "never-log-this",
    }):
        with patch("urllib.request.urlopen", side_effect=fail_urlopen):
            result = publish_market_series([Item("BTC", "crypto")])

    assert result["status"] == "FAILED"
    assert result["error"] == "HTTP_403:CF_CHALLENGE"
    assert "never-log-this" not in json.dumps(result)


def test_data_hub_publish_reports_worker_http_error_code_without_credentials():
    from urllib.error import HTTPError
    from io import BytesIO

    def fail_urlopen(request, timeout):
        raise HTTPError(
            request.full_url,
            401,
            "Unauthorized",
            hdrs=None,
            fp=BytesIO(b'{"error":"UNAUTHORIZED"}'),
        )

    with patch.dict("os.environ", {
        "GRIOS_DATA_HUB_URL": "https://hub.example",
        "GRIOS_DATA_HUB_TOKEN": "never-log-this",
    }):
        with patch("urllib.request.urlopen", side_effect=fail_urlopen):
            result = publish_market_series([Item("BTC", "crypto")])

    assert result["status"] == "FAILED"
    assert result["error"] == "HTTP_401:UNAUTHORIZED"
    assert "never-log-this" not in json.dumps(result)


def test_direct_supabase_ingestion_is_preferred_and_includes_required_columns():
    captured = {}
    class FakeResponse:
        status = 201
        def __enter__(self): return self
        def __exit__(self, *args): return False
    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["headers"] = dict(request.header_items())
        captured["rows"] = json.loads(request.data.decode())
        return FakeResponse()
    with patch.dict("os.environ", {
        "SUPABASE_URL": "https://project.supabase.co",
        "SUPABASE_SERVICE_ROLE_KEY": "test-key",
        "GRIOS_DATA_HUB_URL": "https://worker.example",
        "GRIOS_DATA_HUB_TOKEN": "worker-token",
    }):
        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            result = publish_market_series([Item("BTC", "crypto")], "revision-123")
    assert result["status"] == "DIRECT_SUPABASE"
    assert result["accepted"] == 1
    assert "/rest/v1/grios_market_observations?" in captured["url"]
    assert captured["headers"]["Apikey"] == "test-key"
    assert captured["rows"][0]["run_id"]
    assert captured["rows"][0]["source_revision"] == "revision-123"
    assert "test-key" not in json.dumps(result)
    assert "worker-token" not in json.dumps(result)


def test_direct_supabase_failure_is_sanitized():
    from urllib.error import HTTPError
    from io import BytesIO
    def fail_urlopen(request, timeout):
        raise HTTPError(request.full_url, 403, "Forbidden", hdrs=None, fp=BytesIO(b"private response"))
    with patch.dict("os.environ", {
        "SUPABASE_URL": "https://project.supabase.co",
        "SUPABASE_SERVICE_ROLE_KEY": "test-key",
    }):
        with patch("urllib.request.urlopen", side_effect=fail_urlopen):
            result = publish_market_series([Item("BTC", "crypto")])
    assert result["status"] == "FAILED"
    assert result["error"] == "SUPABASE_HTTP_403"
    assert "test-key" not in json.dumps(result)
    assert "private response" not in json.dumps(result)

