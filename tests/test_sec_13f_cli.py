import json

import pytest

from scripts import ingest_sec_13f


def test_cli_fails_before_network_when_required_configuration_is_missing(tmp_path):
    with pytest.raises(RuntimeError, match="SEC_USER_AGENT"):
        ingest_sec_13f.run_ingestion(
            "0000123456", "2026-09-30",
            output_path=tmp_path / "report.json",
            registry_path=tmp_path / "registry.sqlite3",
            environ={},
        )


def test_cli_writes_audit_report_after_successful_data_hub_publish(tmp_path, monkeypatch):
    calls = {}

    class FakeSecClient:
        def __init__(self, user_agent):
            calls["user_agent"] = user_agent

    class FakeDataHub:
        def __init__(self, base_url, token):
            calls["base_url"] = base_url
            calls["token"] = token

    def fake_ingest(sec, cik, period, **kwargs):
        calls["ingest"] = (cik, period, kwargs)
        return {
            "filer_cik": "0000123456",
            "report_period": "2026-09-30",
            "holdings_count": 3,
            "discovered_filing_count": 2,
            "data_hub_publish": {
                "status": "accepted",
                "snapshot_id": "a" * 64,
            },
        }

    monkeypatch.setattr(ingest_sec_13f, "SecEdgarClient", FakeSecClient)
    monkeypatch.setattr(ingest_sec_13f, "GriosDataHubClient", FakeDataHub)
    monkeypatch.setattr(ingest_sec_13f, "ingest_13f_report_period", fake_ingest)

    output = tmp_path / "artifacts" / "report.json"
    registry = tmp_path / "artifacts" / "registry.sqlite3"
    result = ingest_sec_13f.run_ingestion(
        "0000123456", "2026-09-30",
        output_path=output,
        registry_path=registry,
        environ={
            "SEC_USER_AGENT": "GRIOS Research contact@example.org",
            "GRIOS_DATA_HUB_URL": "https://hub.example.com",
            "GRIOS_INGEST_TOKEN": "not-a-real-token",
            "GITHUB_SHA": "abc123",
        },
    )
    assert result["data_hub_publish"]["status"] == "accepted"
    assert calls["user_agent"].endswith("contact@example.org")
    assert calls["base_url"] == "https://hub.example.com"
    assert calls["ingest"][2]["include_historical"] is True
    assert calls["ingest"][2]["database"] == str(registry)
    assert json.loads(output.read_text())["holdings_count"] == 3
