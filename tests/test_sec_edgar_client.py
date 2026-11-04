import pytest

from sec_edgar_client import SecEdgarClient, normalize_accession, normalize_cik


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeHttpClient:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return FakeResponse(self.responses[url])


def submissions_payload():
    return {
        "filings": {
            "recent": {
                "form": ["13F-HR", "13F-HR/A", "13F-NT"],
                "accessionNumber": [
                    "0000123456-26-000001",
                    "0000123456-26-000002",
                    "0000123456-26-000003",
                ],
                "filingDate": ["2026-11-01", "2026-11-02", "2026-11-03"],
                "reportDate": ["2026-09-30", "2026-09-30", "2026-09-30"],
                "primaryDocument": ["primary.xml", "amendment.xml", "notice.xml"],
            }
        }
    }


def test_normalize_identifiers():
    assert normalize_cik("123456") == "0000123456"
    assert normalize_accession("0000123456-26-000001") == "0000123456-26-000001"
    with pytest.raises(ValueError):
        normalize_cik("not-a-cik")
    with pytest.raises(ValueError):
        normalize_accession("bad-accession")


def test_user_agent_requires_contact_email():
    with pytest.raises(ValueError, match="contact email"):
        SecEdgarClient(user_agent="GRIOS Research")


def test_discover_only_13f_holdings_and_amendments():
    url = "https://data.sec.gov/submissions/CIK0000123456.json"
    fake = FakeHttpClient({url: submissions_payload()})
    client = SecEdgarClient(user_agent="GRIOS Research research@example.org", client=fake)
    filings = client.discover_13f_filings("123456")
    assert [item.form for item in filings] == ["13F-HR", "13F-HR/A"]
    assert filings[0].report_date == "2026-09-30"
    assert filings[1].primary_document_url.endswith("/000012345626000002/amendment.xml")


def test_discover_can_exclude_amendments_and_filter_dates():
    url = "https://data.sec.gov/submissions/CIK0000123456.json"
    fake = FakeHttpClient({url: submissions_payload()})
    client = SecEdgarClient(user_agent="GRIOS Research research@example.org", client=fake)
    filings = client.discover_13f_filings(
        "123456", start_date="2026-11-02", include_amendments=False
    )
    assert filings == []


def test_rejects_misaligned_submissions_arrays():
    payload = submissions_payload()
    payload["filings"]["recent"]["reportDate"] = []
    url = "https://data.sec.gov/submissions/CIK0000123456.json"
    fake = FakeHttpClient({url: payload})
    client = SecEdgarClient(user_agent="GRIOS Research research@example.org", client=fake)
    with pytest.raises(ValueError, match="inconsistent lengths"):
        client.discover_13f_filings("123456")


def test_filing_index_selects_information_table_xml():
    url = "https://www.sec.gov/Archives/edgar/data/123456/000012345626000001/index.json"
    payload = {
        "directory": {
            "item": [
                {"name": "primary_doc.xml", "type": "13F-HR"},
                {"name": "infotable.xml", "type": "INFORMATION TABLE"},
                {"name": "primary_doc.htm", "type": "TEXT"},
            ]
        }
    }
    fake = FakeHttpClient({url: payload})
    client = SecEdgarClient(user_agent="GRIOS Research research@example.org", client=fake)
    selected = client.find_information_table_document("123456", "0000123456-26-000001")
    assert selected["name"] == "infotable.xml"
    assert selected["url"].endswith("/infotable.xml")


def test_ambiguous_information_table_documents_are_rejected():
    url = "https://www.sec.gov/Archives/edgar/data/123456/000012345626000001/index.json"
    fake = FakeHttpClient({url: {"directory": {"item": [
        {"name": "infotable-a.xml"}, {"name": "infotable-b.xml"}
    ]}}})
    client = SecEdgarClient(user_agent="GRIOS Research research@example.org", client=fake)
    with pytest.raises(ValueError, match="exactly one"):
        client.find_information_table_document("123456", "0000123456-26-000001")



class FakeBinaryResponse:
    def __init__(self, content, content_length=None):
        self.content = content
        self.headers = {}
        if content_length is not None:
            self.headers["content-length"] = str(content_length)

    def raise_for_status(self):
        return None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def iter_bytes(self):
        midpoint = max(1, len(self.content) // 2)
        yield self.content[:midpoint]
        if self.content[midpoint:]:
            yield self.content[midpoint:]


class FakeBinaryClient:
    def __init__(self, response):
        self.response = response

    def stream(self, method, url, **kwargs):
        return self.response


def test_download_document_accepts_sec_https_and_enforces_size_limit():
    url = "https://www.sec.gov/Archives/edgar/data/123456/filing.xml"
    client = SecEdgarClient(
        user_agent="GRIOS Research research@example.org",
        client=FakeBinaryClient(FakeBinaryResponse(b"<xml/>")),
    )
    assert client.download_document(url) == b"<xml/>"
    with pytest.raises(ValueError, match="size limit"):
        client.download_document(url, max_bytes=3)


def test_download_document_rejects_non_sec_and_non_https_urls():
    client = SecEdgarClient(user_agent="GRIOS Research research@example.org")
    with pytest.raises(ValueError, match="HTTPS SEC.gov"):
        client.download_document("https://example.com/filing.xml")
    with pytest.raises(ValueError, match="HTTPS SEC.gov"):
        client.download_document("http://www.sec.gov/filing.xml")



def test_discover_historical_13f_filings_and_deduplicates_accessions():
    submissions_url = "https://data.sec.gov/submissions/CIK0000123456.json"
    history_url = "https://data.sec.gov/submissions/CIK0000123456-submissions-001.json"
    current = submissions_payload()
    current["filings"]["files"] = [{
        "name": "CIK0000123456-submissions-001.json",
        "filingFrom": "2020-01-01",
        "filingTo": "2025-12-31",
        "filingCount": 2,
    }]
    historical = {
        "form": ["13F-HR", "13F-HR/A"],
        "accessionNumber": [
            "0000123456-25-000001",
            "0000123456-25-000002",
        ],
        "filingDate": ["2025-02-14", "2025-02-15"],
        "reportDate": ["2024-12-31", "2024-12-31"],
        "primaryDocument": ["primary25.xml", "amendment25.xml"],
    }
    fake = FakeHttpClient({
        submissions_url: current,
        history_url: historical,
    })
    client = SecEdgarClient(
        user_agent="GRIOS Research research@example.org", client=fake
    )
    filings = client.discover_13f_filings("123456", include_historical=True)
    assert len(filings) == 4
    assert filings[0].accession_number == "0000123456-25-000001"
    assert filings[-1].accession_number == "0000123456-26-000002"
    assert sum(item.accession_number == "0000123456-26-000001" for item in filings) == 1


def test_historical_pagination_respects_date_window_and_file_cap():
    submissions_url = "https://data.sec.gov/submissions/CIK0000123456.json"
    history_url = "https://data.sec.gov/submissions/CIK0000123456-submissions-001.json"
    current = submissions_payload()
    current["filings"]["files"] = [{
        "name": "CIK0000123456-submissions-001.json",
        "filingFrom": "2020-01-01",
        "filingTo": "2025-12-31",
        "filingCount": 2,
    }]
    historical = {
        "form": ["13F-HR"],
        "accessionNumber": ["0000123456-25-000001"],
        "filingDate": ["2025-02-14"],
        "reportDate": ["2024-12-31"],
        "primaryDocument": ["primary25.xml"],
    }
    fake = FakeHttpClient({submissions_url: current, history_url: historical})
    client = SecEdgarClient(
        user_agent="GRIOS Research research@example.org", client=fake
    )
    filtered = client.discover_13f_filings(
        "123456", start_date="2026-01-01", include_historical=True
    )
    assert all(item.filing_date >= "2026-01-01" for item in filtered)
    with pytest.raises(ValueError, match="max_historical_files"):
        client.discover_13f_filings(
            "123456", include_historical=True, max_historical_files=0
        )


def test_historical_filename_is_validated_before_request():
    submissions_url = "https://data.sec.gov/submissions/CIK0000123456.json"
    current = submissions_payload()
    current["filings"]["files"] = [{
        "name": "../outside.json",
        "filingFrom": "2020-01-01",
        "filingTo": "2025-12-31",
        "filingCount": 1,
    }]
    fake = FakeHttpClient({submissions_url: current})
    client = SecEdgarClient(
        user_agent="GRIOS Research research@example.org", client=fake
    )
    with pytest.raises(ValueError, match="filename is invalid"):
        client.discover_13f_filings("123456", include_historical=True)
