from __future__ import annotations

import json
import sys
from datetime import timedelta
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import scanner


def stamp(minutes_ago: int = 0) -> str:
    return (scanner.now_utc() - timedelta(minutes=minutes_ago)).isoformat()


def cg_row(
    symbol: str = "BTC",
    name: str = "Bitcoin",
    price: float = 65000.0,
    updated: str | None = None,
    **extra,
) -> dict:
    row = {
        "symbol": symbol.lower(),
        "name": name,
        "current_price": price,
        "last_updated": updated or stamp(),
        "market_cap": 1_200_000_000_000,
        "total_volume": 30_000_000_000,
        "fully_diluted_valuation": 1_300_000_000_000,
        "price_change_percentage_24h": 1.2,
        "price_change_percentage_7d_in_currency": 2.3,
        "price_change_percentage_30d_in_currency": 4.5,
        "id": "bitcoin",
    }
    row.update(extra)
    return row


def cmc_row(
    symbol: str = "BTC",
    name: str = "Bitcoin",
    price: float = 65010.0,
    updated: str | None = None,
    **extra,
) -> dict:
    usd = {
        "price": price,
        "last_updated": updated or stamp(),
        "market_cap": 1_200_000_000_000,
        "volume_24h": 30_000_000_000,
        "fully_diluted_market_cap": 1_300_000_000_000,
        "percent_change_24h": 1.2,
        "percent_change_7d": 2.3,
        "percent_change_30d": 4.5,
    }
    usd.update(extra)
    return {
        "symbol": symbol,
        "name": name,
        "slug": "bitcoin",
        "quote": {"USD": usd},
    }


def series(
    symbol: str = "BTC",
    name: str = "Bitcoin",
    provider: str = "CoinGecko",
    price: float = 65000.0,
    **extra,
) -> scanner.MarketSeries:
    return scanner.MarketSeries(
        key=f"crypto:asset:{symbol}:{scanner.normalized_name(name)}",
        symbol=symbol,
        name=name,
        asset_class="crypto",
        instrument="spot token",
        provider=provider,
        feed_class="mock",
        currency="USD",
        observations=[{"date": scanner.now_utc().date().isoformat(), "close": price}],
        observed_at=stamp(),
        data_as_of=scanner.now_utc().date().isoformat(),
        extra={
            "market_cap": 1_200_000_000_000,
            "volume_24h": 30_000_000_000,
            "fdv": None,
            "change_24h": 1.0,
            "change_7d": 2.0,
            "change_30d": 3.0,
            **extra,
        },
    )


def config(**overrides) -> dict:
    value = {
        "min_market_cap_usd": 250_000_000,
        "min_volume_24h_usd": 10_000_000,
        "min_turnover_ratio": 0.01,
        "max_fdv_market_cap_ratio": 3.0,
        "require_two_sources": False,
        "excluded_symbols": ["USDT"],
        "excluded_name_terms": ["wrapped", "stablecoin"],
    }
    value.update(overrides)
    return value



def test_load_watchlist_normalizes_legacy_ton_to_gram(tmp_path):
    watchlist = tmp_path / "watchlist.json"
    watchlist.write_text(
        json.dumps({"crypto_symbols": ["BTC", "TON", "GRAM", "TON"]}),
        encoding="utf-8",
    )
    loaded = scanner.load_watchlist(watchlist)
    assert loaded["crypto_symbols"] == ["BTC", "GRAM"]


def test_parse_timestamp_rejects_naive_datetime():
    assert scanner.parse_timestamp("2026-11-04T12:00:00") is None


def test_provider_audit_accepts_fresh_valid_row_without_secrets():
    secret = "DO_NOT_LEAK_THIS_API_KEY"
    audit, valid = scanner.audit_crypto_provider(
        "CoinGecko", [cg_row()], ["BTC"], 30, error_type=None
    )
    serialized = json.dumps(audit)
    assert audit["symbols"]["BTC"]["status"] == "VALID"
    assert "BTC" in valid
    assert secret not in serialized
    assert "current_price" not in serialized


@pytest.mark.parametrize(
    ("row", "expected"),
    [
        (cg_row(price=0), "INVALID_PRICE"),
        (cg_row(updated="not-a-timestamp"), "INVALID_TIMESTAMP"),
        (cg_row(updated=stamp(minutes_ago=90)), "STALE"),
        (cg_row(updated=(scanner.now_utc() + timedelta(minutes=5)).isoformat()), "FUTURE_TIMESTAMP"),
        (cg_row(name=""), "INVALID_NAME"),
    ],
)
def test_provider_audit_rejects_invalid_rows(row, expected):
    audit, valid = scanner.audit_crypto_provider(
        "CoinGecko", [row], ["BTC"], 30
    )
    assert audit["symbols"]["BTC"]["status"] == expected
    assert valid == {}


def test_provider_audit_rejects_gram_ticker_with_wrong_coingecko_asset_id():
    row = cg_row(
        symbol="gram",
        name="Gram (prev. Toncoin)",
        id="unrelated-gram",
    )
    audit, valid = scanner.audit_crypto_provider(
        "CoinGecko", [row], ["GRAM"], 30
    )
    assert valid == {}
    assert audit["symbols"]["GRAM"]["status"] == "IDENTITY_MISMATCH"
    assert audit["symbols"]["GRAM"]["provider_identity_checks"]["asset_id_matches"] is False


def test_provider_audit_rejects_gram_ticker_with_wrong_coinmarketcap_asset_id():
    row = cmc_row(symbol="GRAM", name="Gram (prev. Toncoin)")
    row.update({"id": 999999, "slug": "gram"})
    audit, valid = scanner.audit_crypto_provider(
        "CoinMarketCap", [row], ["GRAM"], 30
    )
    assert valid == {}
    assert audit["symbols"]["GRAM"]["status"] == "IDENTITY_MISMATCH"
    assert audit["symbols"]["GRAM"]["provider_identity_checks"]["asset_id_matches"] is False


def test_provider_audit_marks_duplicate_ticker_ambiguous():
    audit, valid = scanner.audit_crypto_provider(
        "CoinGecko",
        [cg_row(), cg_row(name="Bitcoin (duplicate)", price=65001)],
        ["BTC"],
        30,
    )
    assert audit["symbols"]["BTC"]["status"] == "AMBIGUOUS_SYMBOL"
    assert valid == {}


def test_provider_audit_records_missing_requested_symbols():
    audit, valid = scanner.audit_crypto_provider(
        "CoinGecko", [cg_row()], ["BTC", "ETH"], 30
    )
    assert audit["symbols"]["ETH"]["status"] == "NOT_RETURNED"
    assert set(valid) == {"BTC"}


def test_provider_error_is_reported_without_payload_or_key():
    audit, valid = scanner.audit_crypto_provider(
        "CoinGecko", [], ["BTC"], 30, error_type="HTTPStatusError"
    )
    assert audit["status"] == "PROVIDER_ERROR"
    assert audit["error_type"] == "HTTPStatusError"
    assert valid == {}


def test_coinmarketcap_adapter_parses_usd_quote_and_keeps_two_value_contract():
    response = Mock()
    response.json.return_value = {"status": {"error_code": 0}, "data": [cmc_row()]}
    response.raise_for_status.return_value = None
    audit = {}
    with patch.object(scanner.httpx, "get", return_value=response):
        rows, error = scanner.fetch_coinmarketcap("test-secret", ["BTC"], 30, audit=audit)
    assert error is None
    assert len(rows) == 1
    assert rows[0].provider == "CoinMarketCap"
    assert rows[0].observations[-1]["close"] == pytest.approx(65010.0)
    assert audit["symbols"]["BTC"]["status"] == "VALID"
    assert "test-secret" not in json.dumps(audit)


def test_coingecko_adapter_parses_response_and_keeps_two_value_contract():
    response = Mock()
    response.json.return_value = [cg_row()]
    response.raise_for_status.return_value = None
    audit = {}
    with patch.object(scanner.httpx, "get", return_value=response):
        rows, error = scanner.fetch_coingecko("test-secret", ["BTC"], 30, audit=audit)
    assert error is None
    assert len(rows) == 1
    assert rows[0].provider == "CoinGecko"
    assert audit["symbols"]["BTC"]["status"] == "VALID"
    assert "test-secret" not in json.dumps(audit)


def test_coinmarketcap_api_error_is_not_misreported_as_missing_symbols():
    response = Mock()
    response.json.return_value = {
        "status": {"error_code": 100, "error_message": "private provider detail"},
        "data": [],
    }
    response.raise_for_status.return_value = None
    audit = {}
    with patch.object(scanner.httpx, "get", return_value=response):
        rows, error = scanner.fetch_coinmarketcap("secret", ["BTC"], 30, audit=audit)
    assert rows == []
    assert error
    assert audit["status"] == "PROVIDER_ERROR"
    assert audit["provider_error_code"] == 100
    assert "private provider detail" not in json.dumps(audit)


def test_reconciliation_accepts_matching_sources_and_records_unconfirmed_identity():
    audit = {}
    rows, conflicts = scanner.reconcile_crypto(
        [series(provider="CoinGecko"), series(provider="CoinMarketCap", price=65010)],
        audit=audit,
    )
    assert conflicts == []
    assert len(rows) == 1
    assert rows[0].provider == "CoinGecko + CoinMarketCap"
    assert rows[0].extra["provider_count"] == 2
    assert rows[0].extra["identity_status"] == "UNCONFIRMED_NAME_MATCH"
    assert audit["reconciliation"]["BTC"]["status"] == "ACCEPTED_CROSS_SOURCE"


def test_reconciliation_blocks_name_mismatch():
    audit = {}
    rows, conflicts = scanner.reconcile_crypto(
        [series(name="Bitcoin"), series(name="Bitcoin Cash", provider="CoinMarketCap")],
        audit=audit,
    )
    assert rows == []
    assert conflicts
    assert audit["reconciliation"]["BTC"]["status"] == "IDENTITY_MISMATCH"


def test_reconciliation_blocks_price_conflict():
    audit = {}
    rows, conflicts = scanner.reconcile_crypto(
        [series(price=65000), series(provider="CoinMarketCap", price=70000)],
        audit=audit,
    )
    assert rows == []
    assert conflicts
    assert audit["reconciliation"]["BTC"]["status"] == "SOURCE_CONFLICT"


def test_reconciliation_blocks_duplicate_provider_records():
    audit = {}
    rows, conflicts = scanner.reconcile_crypto(
        [series(), series(price=65001), series(provider="CoinMarketCap")],
        audit=audit,
    )
    assert rows == []
    assert conflicts
    assert audit["reconciliation"]["BTC"]["status"] == "AMBIGUOUS_SYMBOL"


def test_reconciliation_allows_single_source_with_explicit_status():
    audit = {}
    rows, conflicts = scanner.reconcile_crypto([series()], audit=audit)
    assert conflicts == []
    assert len(rows) == 1
    assert audit["reconciliation"]["BTC"]["status"] == "ACCEPTED_SINGLE_SOURCE"


def test_fetch_crypto_blocks_ambiguous_symbol_even_if_other_provider_returns_it():
    def ambiguous_fetch(api_key, symbols, max_age, audit=None):
        audit.update({
            "provider": "CoinGecko",
            "symbols": {"BTC": {"status": "AMBIGUOUS_SYMBOL"}},
        })
        return [], "duplicate symbol"
    def valid_fetch(api_key, symbols, max_age, audit=None):
        audit.update({
            "provider": "CoinMarketCap",
            "symbols": {"BTC": {"status": "VALID"}},
        })
        return [series(provider="CoinMarketCap")], None

    audit = {}
    with patch.object(scanner, "fetch_coingecko", side_effect=ambiguous_fetch), patch.object(
        scanner, "fetch_coinmarketcap", side_effect=valid_fetch
    ):
        rows, errors = scanner.fetch_crypto(["BTC"], 30, audit=audit)
    assert rows == []
    assert errors
    assert audit["summary"]["ambiguous_symbols_blocked"] == ["BTC"]



def test_gram_coingecko_fallback_uses_exact_asset_id_and_accepts_fresh_quote():
    row = cg_row(
        symbol="gram",
        name="Gram (prev. Toncoin)",
        price=5.25,
        id="the-open-network",
        market_cap=12_000_000_000,
        total_volume=300_000_000,
        fully_diluted_valuation=25_000_000_000,
    )
    response = Mock()
    response.json.return_value = [row]
    response.raise_for_status.return_value = None
    audit = {}
    with patch.object(scanner.httpx, "get", return_value=response) as get:
        rows, error = scanner.fetch_gram_by_provider_id("CoinGecko", "secret", 30, audit)
    assert error is None
    assert len(rows) == 1
    assert rows[0].symbol == "GRAM"
    assert rows[0].observations[-1]["close"] == pytest.approx(5.25)
    assert audit["endpoint_mode"] == "provider_asset_id"
    assert get.call_args.kwargs["params"]["ids"] == "the-open-network"


def test_gram_fallback_rejects_wrong_provider_asset_identity():
    row = cg_row(symbol="gram", name="Gram (prev. Toncoin)", id="not-ton")
    response = Mock()
    response.json.return_value = [row]
    response.raise_for_status.return_value = None
    audit = {}
    with patch.object(scanner.httpx, "get", return_value=response):
        rows, error = scanner.fetch_gram_by_provider_id("CoinGecko", "secret", 30, audit)
    assert rows == []
    assert error
    assert audit["symbols"]["GRAM"]["status"] == "IDENTITY_MISMATCH"
    evidence = audit["identity_evidence"][0]
    assert evidence["provider_asset_id"] == "not-ton"
    assert evidence["checks"]["asset_id_matches"] is False
    assert evidence["checks"]["symbol_matches"] is True
    assert evidence["checks"]["name_matches"] is True


def test_gram_fallback_marks_duplicate_asset_rows_ambiguous():
    row = cg_row(symbol="gram", name="Gram (prev. Toncoin)", id="the-open-network")
    duplicate = {**row, "current_price": 5.26}
    response = Mock()
    response.json.return_value = [row, duplicate]
    response.raise_for_status.return_value = None
    audit = {}
    with patch.object(scanner.httpx, "get", return_value=response):
        rows, error = scanner.fetch_gram_by_provider_id("CoinGecko", "secret", 30, audit)
    assert rows == []
    assert error
    assert audit["symbols"]["GRAM"]["status"] == "AMBIGUOUS_SYMBOL"


def test_gram_fallback_rejects_stale_quote():
    row = cg_row(symbol="gram", name="Gram (prev. Toncoin)", id="the-open-network", updated=stamp(minutes_ago=90))
    response = Mock()
    response.json.return_value = [row]
    response.raise_for_status.return_value = None
    audit = {}
    with patch.object(scanner.httpx, "get", return_value=response):
        rows, error = scanner.fetch_gram_by_provider_id("CoinGecko", "secret", 30, audit)
    assert rows == []
    assert error
    assert audit["symbols"]["GRAM"]["status"] == "STALE"


def test_gram_fallback_provider_outage_is_sanitized():
    audit = {}
    with patch.object(scanner.httpx, "get", side_effect=scanner.httpx.ConnectError("private connection detail")):
        rows, error = scanner.fetch_gram_by_provider_id("CoinGecko", "secret", 30, audit)
    assert rows == []
    assert error
    assert audit["status"] == "PROVIDER_ERROR"
    assert "private connection detail" not in json.dumps(audit)


def test_gram_coinmarketcap_fallback_uses_numeric_asset_id():
    record = cmc_row(symbol="GRAM", name="Gram (prev. Toncoin)", price=5.2)
    record.update({"id": 11419, "slug": "gram"})
    response = Mock()
    response.json.return_value = {"status": {"error_code": 0}, "data": {"11419": record}}
    response.raise_for_status.return_value = None
    audit = {}
    with patch.object(scanner.httpx, "get", return_value=response) as get:
        rows, error = scanner.fetch_gram_by_provider_id("CoinMarketCap", "secret", 30, audit)
    assert error is None
    assert len(rows) == 1
    assert rows[0].symbol == "GRAM"
    assert get.call_args.kwargs["params"]["id"] == "11419"

def test_universe_filter_preserves_missing_fdv_eligibility_and_audits_rejection():
    good = series(extra_marker="good")
    low_cap = series(symbol="SMALL", name="Small", market_cap=10)
    eligible, stats = scanner.filter_crypto_universe(
        [good, low_cap], config(), audit := {}
    )
    assert [item.symbol for item in eligible] == ["BTC"]
    assert stats["excluded_reasons"]["market_cap_below_minimum"] == 1
    assert audit["universe_filter"]["assets"]["BTC"]["accepted"] is True
    assert audit["universe_filter"]["assets"]["BTC"]["fdv_market_cap_ratio"] is None


def test_universe_filter_can_require_two_sources():
    eligible, stats = scanner.filter_crypto_universe(
        [series()], config(require_two_sources=True)
    )
    assert eligible == []
    assert stats["excluded_reasons"]["single_source"] == 1


def test_save_crypto_audit_writes_valid_json_atomically(tmp_path):
    target = scanner.save_crypto_audit(
        {"summary": {"valid": 1}},
        tmp_path,
        "20261104T120000Z",
        "baseline-sha",
        "watchlist",
        30,
    )
    payload = json.loads(target.read_text(encoding="utf-8"))
    assert payload["source_revision"]["git_commit_sha"] == "baseline-sha"
    assert payload["audit"]["summary"]["valid"] == 1
    assert not target.with_suffix(".json.tmp").exists()

def test_main_uses_declared_source_commit_argument():
    import ast
    from pathlib import Path

    scanner_path = Path(__file__).resolve().parents[1] / "scanner.py"
    tree = ast.parse(scanner_path.read_text(encoding="utf-8"))
    attributes = {
        node.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute)
    }
    assert "crypto_audit_source_commit_sha" in attributes
    assert "crypto_audit_baseline_sha" not in attributes

def test_main_persists_runtime_commit_sha_in_audit(tmp_path, monkeypatch):
    watchlist = tmp_path / "watchlist.json"
    watchlist.write_text(
        json.dumps({
            "crypto_symbols": ["BTC"],
            "crypto_universe": {"mode": "watchlist"},
        }),
        encoding="utf-8",
    )
    output_dir = tmp_path / "reports"
    database = tmp_path / "journal.sqlite3"
    monkeypatch.setenv("GRIOS_SOURCE_COMMIT_SHA", "runtime-commit-123")
    monkeypatch.setenv("MAX_CRYPTO_AGE_MINUTES", "30")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "scanner.py",
            "--watchlist",
            str(watchlist),
            "--out",
            str(output_dir),
            "--db",
            str(database),
            "--skip-openbb",
        ],
    )
    monkeypatch.setattr(scanner, "fetch_crypto", lambda symbols, max_age, audit=None: ([], []))
    monkeypatch.setattr(
        scanner,
        "filter_crypto_universe",
        lambda rows, cfg, audit=None: (
            [],
            {
                "input_count": 0,
                "eligible_count": 0,
                "excluded_count": 0,
                "excluded_reasons": {},
            },
        ),
    )
    monkeypatch.setattr(scanner, "telegram_report", lambda *args, **kwargs: "test report")

    assert scanner.main() == 0

    audit_files = list(output_dir.glob("crypto-audit-*.json"))
    assert len(audit_files) == 1
    payload = json.loads(audit_files[0].read_text(encoding="utf-8"))
    assert payload["source_revision"]["git_commit_sha"] == "runtime-commit-123"
    assert "baseline_sha" not in payload["audit"]
    assert (output_dir / "latest.txt").read_text(encoding="utf-8").startswith("test report\n\n📊 پوشش داده:")



def test_ecb_fx_retries_one_transient_timeout_and_accepts_reference_data(monkeypatch):
    from types import SimpleNamespace

    response = Mock()
    obb = SimpleNamespace(ecb=Mock())
    obb.ecb.exchange_rates.side_effect = [
        TimeoutError("temporary timeout"),
        response,
    ]
    monkeypatch.setattr(
        scanner,
        "dataframe_rows",
        lambda value: [{"date": "2026-11-04", "value": 1.16}],
    )
    sleep = Mock()
    monkeypatch.setattr(scanner.time, "sleep", sleep)

    rows, errors = scanner.fetch_fx_reference(obb, ["EURUSD"])

    assert errors == []
    assert len(rows) == 1
    assert rows[0].symbol == "EURUSD"
    assert rows[0].observations[-1]["close"] == pytest.approx(1.16)
    assert obb.ecb.exchange_rates.call_count == 2
    sleep.assert_called_once_with(0.5)


def test_ecb_fx_reports_timeout_after_single_retry(monkeypatch):
    from types import SimpleNamespace

    obb = SimpleNamespace(ecb=Mock())
    obb.ecb.exchange_rates.side_effect = TimeoutError("temporary timeout")
    sleep = Mock()
    monkeypatch.setattr(scanner.time, "sleep", sleep)

    rows, errors = scanner.fetch_fx_reference(obb, ["EURTRY"])

    assert rows == []
    assert len(errors) == 1
    assert "EURTRY" in errors[0]
    assert "TimeoutError" in errors[0]
    assert obb.ecb.exchange_rates.call_count == 2
    sleep.assert_called_once_with(0.5)


def test_ecb_fx_does_not_retry_non_timeout_errors(monkeypatch):
    from types import SimpleNamespace

    obb = SimpleNamespace(ecb=Mock())
    obb.ecb.exchange_rates.side_effect = ValueError("invalid provider request")
    sleep = Mock()
    monkeypatch.setattr(scanner.time, "sleep", sleep)

    rows, errors = scanner.fetch_fx_reference(obb, ["EURUSD"])

    assert rows == []
    assert len(errors) == 1
    assert "ValueError" in errors[0]
    assert obb.ecb.exchange_rates.call_count == 1
    sleep.assert_not_called()
