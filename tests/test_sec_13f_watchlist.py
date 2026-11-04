import json

import pytest

import scripts.ingest_sec_13f_watchlist as watchlist_module


ENV = {
    "SEC_USER_AGENT": "GRIOS Research research@example.org",
    "GRIOS_DATA_HUB_URL": "https://grios.example.workers.dev",
    "GRIOS_INGEST_TOKEN": "test-token",
    "GITHUB_SHA": "test-revision",
}


def write_watchlist(path, entries):
    path.write_text(
        json.dumps({"schema_version": "1.0", "watchlist": entries}),
        encoding="utf-8",
    )


def test_load_watchlist_normalizes_cik_and_validates_reference(tmp_path):
    source = tmp_path / "watchlist.json"
    write_watchlist(source, [{
        "cik": "1364742",
        "name": "BlackRock, Inc.",
        "enabled": True,
        "reference_url": "https://www.sec.gov/Archives/edgar/data/1364742/example-index.htm",
    }])
    result = watchlist_module.load_watchlist(source)
    assert result[0]["cik"] == "0001364742"
    assert result[0]["name"] == "BlackRock, Inc."


def test_load_watchlist_rejects_duplicate_ciks_and_non_sec_reference(tmp_path):
    source = tmp_path / "watchlist.json"
    entry = {"cik": "1364742", "name": "BlackRock"}
    write_watchlist(source, [entry, dict(entry)])
    with pytest.raises(ValueError, match="Duplicate CIK"):
        watchlist_module.load_watchlist(source)

    write_watchlist(source, [{
        **entry,
        "reference_url": "https://example.com/blackrock",
    }])
    with pytest.raises(ValueError, match="HTTPS SEC.gov"):
        watchlist_module.load_watchlist(source)


def test_watchlist_batch_reuses_one_sec_client_and_continues_after_failure(
    tmp_path, monkeypatch
):
    source = tmp_path / "watchlist.json"
    write_watchlist(source, [
        {"cik": "1364742", "name": "BlackRock, Inc.", "enabled": True},
        {"cik": "123456", "name": "Example Manager", "enabled": True},
        {"cik": "999999", "name": "Disabled Manager", "enabled": False},
    ])
    sec_instances = []

    class FakeSecClient:
        def __init__(self, *, user_agent):
            self.user_agent = user_agent
            sec_instances.append(self)

    class FakeHubClient:
        def __init__(self, base_url, token):
            self.base_url = base_url
            self.token = token

    monkeypatch.setattr(watchlist_module, "SecEdgarClient", FakeSecClient)
    monkeypatch.setattr(watchlist_module, "GriosDataHubClient", FakeHubClient)

    calls = []

    def fake_ingest(sec, cik, period, **kwargs):
        calls.append((sec, cik, period, kwargs))
        if cik == "0000123456":
            raise RuntimeError("mocked SEC response failure")
        return {
            "filer_cik": cik,
            "report_period": period,
            "holdings_count": 7,
            "discovered_filing_count": 2,
            "data_hub_publish": {"snapshot_id": "a" * 64},
        }

    monkeypatch.setattr(
        watchlist_module, "ingest_13f_report_period", fake_ingest
    )
    summary_path = tmp_path / "artifacts" / "summary.json"
    result = watchlist_module.run_watchlist(
        "2026-09-30",
        watchlist_path=source,
        output_dir=tmp_path / "reports",
        registry_path=tmp_path / "registry.sqlite3",
        summary_path=summary_path,
        environ=ENV,
    )

    assert len(sec_instances) == 1
    assert len(calls) == 2
    assert calls[0][0] is calls[1][0] is sec_instances[0]
    assert result["status"] == "PARTIAL_FAILURE"
    assert result["filers_published"] == 1
    assert result["filers_failed"] == 1
    assert result["filers_skipped"] == 1
    assert (tmp_path / "reports" / "0001364742_2026-09-30.json").exists()
    assert json.loads(summary_path.read_text(encoding="utf-8"))["filers_failed"] == 1


def test_watchlist_batch_requires_data_hub_configuration(tmp_path):
    source = tmp_path / "watchlist.json"
    write_watchlist(source, [{"cik": "1364742", "name": "BlackRock"}])
    with pytest.raises(RuntimeError, match="GRIOS_INGEST_TOKEN"):
        watchlist_module.run_watchlist(
            "2026-09-30",
            watchlist_path=source,
            output_dir=tmp_path / "reports",
            registry_path=tmp_path / "registry.sqlite3",
            summary_path=tmp_path / "summary.json",
            environ={"SEC_USER_AGENT": ENV["SEC_USER_AGENT"]},
        )


def test_committed_watchlist_contains_verified_unique_institutional_filers():
    entries = watchlist_module.load_watchlist(
        "config/sec_13f_watchlist.json"
    )
    assert {item["cik"] for item in entries} == {
        "0001364742",
        "0001067983",
        "0000315066",
        "0000093751",
    }
    assert all(
        item["reference_url"].startswith("https://www.sec.gov/")
        for item in entries
    )
