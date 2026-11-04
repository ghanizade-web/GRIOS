import pytest

from sec_13f_data_hub import GriosDataHubClient
from sec_13f_registry import prepare_13f_data_hub_payload


class FakeResponse:
    def __init__(self, payload, status=202):
        self.payload = payload
        self.status = status

    def raise_for_status(self):
        if self.status >= 400:
            raise RuntimeError("HTTP error")

    def json(self):
        return self.payload


class FakeHttpClient:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        return self.response


def sample_report():
    return {
        "filer_cik": "0000123456",
        "report_period": "2026-09-30",
        "latest_filed_at": "2026-11-02T00:00:00+00:00",
        "ingestion_status": "RECONCILED_PUBLIC_SNAPSHOT",
        "holdings_count": 1,
        "applied_filings": [{
            "accession_number": "0000123456-26-000001",
            "form_type": "13F-HR",
            "amendment_number": None,
            "amendment_type": "ORIGINAL",
            "filed_at": "2026-11-01T00:00:00+00:00",
            "source_url": "https://www.sec.gov/Archives/edgar/data/123456/000012345626000001/infotable.xml",
            "cover_page_source_url": "https://www.sec.gov/Archives/edgar/data/123456/000012345626000001/primary_doc.xml",
            "effect": "BASE_SNAPSHOT",
        }],
        "holdings": [{
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
        }],
    }


def test_publish_sends_authenticated_validated_snapshot():
    snapshot_id = prepare_13f_data_hub_payload(sample_report())["snapshot"]["snapshot_id"]
    fake = FakeHttpClient(FakeResponse({
        "status": "accepted", "snapshot_id": snapshot_id,
    }))
    client = GriosDataHubClient(
        "https://hub.example.com", "test-token", client=fake
    )
    result = client.publish_snapshot(sample_report(), source_revision="abc123")
    method, url, kwargs = fake.calls[0]
    assert method == "POST"
    assert url.endswith("/v1/13f/snapshots")
    assert kwargs["headers"]["authorization"] == "Bearer test-token"
    assert kwargs["json"]["snapshot"]["source_revision"] == "abc123"
    assert result["snapshot_id"] == snapshot_id


def test_publish_rejects_wrong_snapshot_identity():
    fake = FakeHttpClient(FakeResponse({
        "status": "accepted", "snapshot_id": "b" * 64,
    }))
    client = GriosDataHubClient("https://hub.example.com", "test-token", client=fake)
    with pytest.raises(ValueError, match="different"):
        client.publish_snapshot(sample_report())


def test_read_latest_snapshot_uses_filer_and_period():
    fake = FakeHttpClient(FakeResponse({"snapshot": {"filer_cik": "0000123456"}} , status=200))
    client = GriosDataHubClient("https://hub.example.com", "test-token", client=fake)
    result = client.get_latest_snapshot("0000123456", "2026-09-30")
    method, url, kwargs = fake.calls[0]
    assert method == "GET"
    assert url.endswith("/v1/13f/latest")
    assert kwargs["params"] == {"cik": "0000123456", "report_period": "2026-09-30"}
    assert result["filer_cik"] == "0000123456"


def test_rejects_non_https_or_pathful_base_url():
    with pytest.raises(ValueError, match="HTTPS origin"):
        GriosDataHubClient("http://hub.example.com", "token")
    with pytest.raises(ValueError, match="must not include a path"):
        GriosDataHubClient("https://hub.example.com/api", "token")
