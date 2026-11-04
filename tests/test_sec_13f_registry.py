import pytest

from sec_13f_registry import get_13f_snapshot, persist_13f_snapshot


def sample_report():
    return {
        "filer_cik": "0000123456",
        "report_period": "2026-09-30",
        "latest_filed_at": "2026-11-02T00:00:00+00:00",
        "ingestion_status": "RECONCILED_PUBLIC_SNAPSHOT",
        "holdings_count": 1,
        "applied_filings": [
            {
                "accession_number": "0000123456-26-000001",
                "form_type": "13F-HR",
                "amendment_number": None,
                "amendment_type": "ORIGINAL",
                "filed_at": "2026-11-01T00:00:00+00:00",
                "source_url": "https://www.sec.gov/Archives/edgar/data/123456/000012345626000001/infotable.xml",
                "cover_page_source_url": "https://www.sec.gov/Archives/edgar/data/123456/000012345626000001/primary_doc.xml",
                "effect": "BASE_SNAPSHOT",
            }
        ],
        "holdings": [
            {
                "issuer": "Example Corporation",
                "title_of_class": "COM",
                "cusip": "123456789",
                "figi": "BBG000B9XRY4",
                "put_call": None,
                "amount_type": "SH",
                "investment_discretion": "SOLE",
                "other_manager": None,
                "amount": 1000000,
                "value_usd": 125000000,
                "voting_authority": {"sole": 1000000, "shared": 0, "none": 0},
            }
        ],
    }


def test_persist_13f_snapshot_is_idempotent_and_round_trips(tmp_path):
    database = tmp_path / "13f.sqlite3"
    report = sample_report()
    first = persist_13f_snapshot(database, report)
    second = persist_13f_snapshot(database, report)
    assert first["snapshot_inserted"] is True
    assert second["snapshot_inserted"] is False
    restored = get_13f_snapshot(
        database, filer_cik="0000123456", report_period="2026-09-30"
    )
    assert restored["holdings_count"] == 1
    assert restored["holdings"][0]["figi"] == "BBG000B9XRY4"
    assert restored["holdings"][0]["value_usd"] == 125000000
    assert restored["applied_filings"][0]["cover_page_source_url"].endswith("primary_doc.xml")


def test_persist_rejects_unreconciled_or_untrusted_records(tmp_path):
    database = tmp_path / "13f.sqlite3"
    report = sample_report()
    report["ingestion_status"] = "PARSED"
    with pytest.raises(ValueError, match="reconciled"):
        persist_13f_snapshot(database, report)
    report = sample_report()
    report["applied_filings"][0]["source_url"] = "http://example.com/filing.xml"
    with pytest.raises(ValueError, match="HTTPS SEC.gov"):
        persist_13f_snapshot(database, report)


def test_persist_rejects_inconsistent_holdings_count(tmp_path):
    report = sample_report()
    report["holdings_count"] = 2
    with pytest.raises(ValueError, match="does not match"):
        persist_13f_snapshot(tmp_path / "13f.sqlite3", report)


def test_latest_snapshot_lookup_does_not_cross_cik_or_period(tmp_path):
    database = tmp_path / "13f.sqlite3"
    persist_13f_snapshot(database, sample_report())
    assert get_13f_snapshot(
        database, filer_cik="0000000001", report_period="2026-09-30"
    ) is None
    assert get_13f_snapshot(
        database, filer_cik="0000123456", report_period="2026-06-30"
    ) is None



def test_registry_rejects_duplicate_accessions_and_invalid_amendment_metadata(tmp_path):
    report = sample_report()
    report["applied_filings"].append(dict(report["applied_filings"][0]))
    with pytest.raises(ValueError, match="Duplicate accession"):
        persist_13f_snapshot(tmp_path / "13f.sqlite3", report)

    report = sample_report()
    report["applied_filings"][0]["amendment_type"] = "RESTATEMENT"
    with pytest.raises(ValueError, match="Original 13F-HR"):
        persist_13f_snapshot(tmp_path / "13f.sqlite3", report)


def test_registry_rejects_non_integer_share_amounts(tmp_path):
    report = sample_report()
    report["holdings"][0]["amount"] = 10.5
    with pytest.raises(ValueError, match="non-negative integer"):
        persist_13f_snapshot(tmp_path / "13f.sqlite3", report)
