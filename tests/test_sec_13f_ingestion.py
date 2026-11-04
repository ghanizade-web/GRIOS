import pytest

from sec_13f_ingestion import (
    ingest_13f_filing, ingest_13f_report_period, parse_13f_cover_page,
)
from sec_edgar_client import SecFiling
from sec_13f_registry import get_13f_snapshot


ORIGINAL_COVER = """<?xml version="1.0"?>
<edgarSubmission>
  <formData><coverPage>
    <reportCalendarOrQuarter>2026-09-30</reportCalendarOrQuarter>
    <isAmendment>false</isAmendment>
    <filingManager><name>Example Adviser LLC</name></filingManager>
  </coverPage></formData>
</edgarSubmission>"""

AMENDMENT_COVER = """<?xml version="1.0"?>
<edgarSubmission>
  <formData><coverPage>
    <reportCalendarOrQuarter>2026-09-30</reportCalendarOrQuarter>
    <isAmendment>true</isAmendment>
    <amendmentNo>2</amendmentNo>
    <amendmentType>RESTATEMENT</amendmentType>
    <filingManager><name>Example Adviser LLC</name></filingManager>
  </coverPage></formData>
</edgarSubmission>"""

TABLE = b"""<?xml version="1.0"?>
<informationTable xmlns="http://www.sec.gov/edgar/document/thirteenf/informationtable">
  <infoTable>
    <nameOfIssuer>Example Corporation</nameOfIssuer>
    <titleOfClass>COM</titleOfClass>
    <cusip>123456789</cusip>
    <value>125000</value>
    <shrsOrPrnAmt><sshPrnamt>1000000</sshPrnamt><sshPrnamtType>SH</sshPrnamtType></shrsOrPrnAmt>
    <investmentDiscretion>SOLE</investmentDiscretion>
    <votingAuthority><Sole>1000000</Sole><Shared>0</Shared><None>0</None></votingAuthority>
  </infoTable>
</informationTable>"""


def test_parse_original_cover_page():
    result = parse_13f_cover_page(ORIGINAL_COVER, form_type="13F-HR")
    assert result["filer_name"] == "Example Adviser LLC"
    assert result["report_period"] == "2026-09-30"
    assert result["amendment_number"] is None


def test_parse_amendment_cover_page():
    result = parse_13f_cover_page(AMENDMENT_COVER, form_type="13F-HR/A")
    assert result["is_amendment"] is True
    assert result["amendment_number"] == 2
    assert result["amendment_type"] == "RESTATEMENT"


def test_reject_invalid_amendment_cover_metadata():
    with pytest.raises(ValueError, match="isAmendment=true"):
        parse_13f_cover_page(ORIGINAL_COVER, form_type="13F-HR/A")
    bad = AMENDMENT_COVER.replace("RESTATEMENT", "UNSPECIFIED")
    with pytest.raises(ValueError, match="amendmentType"):
        parse_13f_cover_page(bad, form_type="13F-HR/A")


class FakePipelineClient:
    def __init__(self, form="13F-HR", cover=ORIGINAL_COVER, report_date="2026-09-30"):
        self.filing = SecFiling(
            cik="0000123456",
            accession_number="0000123456-26-000001",
            form=form,
            filing_date="2026-11-01",
            report_date=report_date,
            primary_document="primary_doc.xml",
            primary_document_url="https://www.sec.gov/Archives/edgar/data/123456/000012345626000001/primary_doc.xml",
        )
        self.cover = cover
        self.downloads = []

    def discover_13f_filings(self, cik, include_historical=False):
        return [self.filing]

    def download_document(self, url):
        self.downloads.append(url)
        if url == self.filing.primary_document_url:
            return self.cover.encode()
        return TABLE

    def find_information_table_document(self, cik, accession):
        return {
            "name": "infotable.xml",
            "url": "https://www.sec.gov/Archives/edgar/data/123456/000012345626000001/infotable.xml",
        }

    def get_submissions(self, cik):
        return {"name": "Example Adviser LLC"}


def test_ingest_13f_filing_end_to_end_with_mocked_sec_responses():
    client = FakePipelineClient()
    result = ingest_13f_filing(
        client, "123456", "0000123456-26-000001",
        retrieved_at="2026-11-02T12:00:00Z",
    )
    assert result["ingestion_status"] == "PARSED"
    assert result["holdings_count"] == 1
    assert result["filer_name"] == "Example Adviser LLC"
    assert result["source_url"].endswith("/infotable.xml")
    assert result["cover_page_source_url"].endswith("/primary_doc.xml")


def test_ingest_rejects_cover_and_submissions_report_date_mismatch():
    client = FakePipelineClient(report_date="2026-06-30")
    with pytest.raises(ValueError, match="conflicts with the cover-page"):
        ingest_13f_filing(
            client, "123456", "0000123456-26-000001",
            retrieved_at="2026-11-02T12:00:00Z",
        )


def test_ingest_amendment_extracts_metadata_before_parser():
    client = FakePipelineClient(
        form="13F-HR/A", cover=AMENDMENT_COVER
    )
    result = ingest_13f_filing(
        client, "123456", "0000123456-26-000001",
        retrieved_at="2026-11-02T12:00:00Z",
    )
    assert result["amendment_number"] == 2
    assert result["amendment_type"] == "RESTATEMENT"


def test_parse_amendment_cover_page_accepts_yes_marker():
    cover = AMENDMENT_COVER.replace("<isAmendment>true</isAmendment>", "<isAmendment>Y</isAmendment>")
    result = parse_13f_cover_page(cover, form_type="13F-HR/A")
    assert result["is_amendment"] is True



def test_ingestion_can_opt_into_historical_submissions():
    class HistoricalClient(FakePipelineClient):
        def __init__(self):
            super().__init__()
            self.historical_requested = False

        def discover_13f_filings(self, cik, include_historical=False):
            self.historical_requested = include_historical
            return [self.filing]

    client = HistoricalClient()
    ingest_13f_filing(
        client, "123456", "0000123456-26-000001",
        retrieved_at="2026-11-02T12:00:00Z",
        include_historical=True,
    )
    assert client.historical_requested is True



NEW_HOLDINGS_COVER = """<?xml version="1.0"?>
<edgarSubmission>
  <formData><coverPage>
    <reportCalendarOrQuarter>2026-09-30</reportCalendarOrQuarter>
    <isAmendment>true</isAmendment>
    <amendmentNo>1</amendmentNo>
    <amendmentType>NEW HOLDINGS</amendmentType>
    <filingManager><name>Example Adviser LLC</name></filingManager>
  </coverPage></formData>
</edgarSubmission>"""


class FakeQuarterClient:
    def __init__(self):
        self.original = SecFiling(
            cik="0000123456",
            accession_number="0000123456-26-000001",
            form="13F-HR",
            filing_date="2026-11-01",
            report_date="2026-09-30",
            primary_document="primary_doc.xml",
            primary_document_url="https://www.sec.gov/Archives/edgar/data/123456/000012345626000001/primary_doc.xml",
        )
        self.amendment = SecFiling(
            cik="0000123456",
            accession_number="0000123456-26-000002",
            form="13F-HR/A",
            filing_date="2026-11-02",
            report_date="2026-09-30",
            primary_document="amendment.xml",
            primary_document_url="https://www.sec.gov/Archives/edgar/data/123456/000012345626000002/amendment.xml",
        )
        self.docs = {
            self.original.primary_document_url: ORIGINAL_COVER.encode(),
            self.amendment.primary_document_url: NEW_HOLDINGS_COVER.encode(),
            "https://www.sec.gov/Archives/edgar/data/123456/000012345626000001/infotable.xml": TABLE,
            "https://www.sec.gov/Archives/edgar/data/123456/000012345626000002/infotable.xml": TABLE.replace(b"123456789", b"987654321"),
        }
        self.historical_requested = False

    def discover_13f_filings(self, cik, include_historical=False):
        self.historical_requested = include_historical
        return [self.original, self.amendment]

    def download_document(self, url):
        return self.docs[url]

    def find_information_table_document(self, cik, accession):
        compact = accession.replace("-", "")
        return {
            "name": "infotable.xml",
            "url": f"https://www.sec.gov/Archives/edgar/data/123456/{compact}/infotable.xml",
        }


def test_ingest_and_reconcile_complete_report_period_chain():
    client = FakeQuarterClient()
    result = ingest_13f_report_period(
        client, "123456", "2026-09-30",
        retrieved_at="2026-11-03T12:00:00Z",
    )
    assert client.historical_requested is True
    assert result["ingestion_status"] == "RECONCILED_PUBLIC_SNAPSHOT"
    assert result["ingestion_scope"] == "REPORT_PERIOD"
    assert result["discovered_filing_count"] == 2
    assert result["holdings_count"] == 2
    assert result["filing_accessions"] == [
        "0000123456-26-000001", "0000123456-26-000002"
    ]
    assert result["applied_filings"][1]["effect"] == "SUPPLEMENTED_PRIOR_SNAPSHOT"


def test_report_period_ingestion_rejects_missing_public_filing_chain():
    class EmptyClient(FakeQuarterClient):
        def discover_13f_filings(self, cik, include_historical=False):
            return []

    with pytest.raises(ValueError, match="No public 13F"):
        ingest_13f_report_period(
            EmptyClient(), "123456", "2026-09-30",
            retrieved_at="2026-11-03T12:00:00Z",
        )



def test_report_period_ingestion_can_persist_snapshot(tmp_path):
    database = tmp_path / "13f.sqlite3"
    client = FakeQuarterClient()
    result = ingest_13f_report_period(
        client, "123456", "2026-09-30",
        retrieved_at="2026-11-03T12:00:00Z",
        database=str(database),
    )
    assert result["persistence"]["snapshot_inserted"] is True
    restored = get_13f_snapshot(
        database, filer_cik="0000123456", report_period="2026-09-30"
    )
    assert restored["holdings_count"] == 2
    assert restored["applied_filings"][1]["effect"] == "SUPPLEMENTED_PRIOR_SNAPSHOT"



def test_report_period_ingestion_can_publish_to_data_hub():
    class FakeDataHub:
        def __init__(self):
            self.published = None

        def publish_snapshot(self, report, source_revision=None):
            self.published = (report, source_revision)
            return {"status": "accepted", "snapshot_id": "a" * 64}

    client = FakeQuarterClient()
    data_hub = FakeDataHub()
    result = ingest_13f_report_period(
        client, "123456", "2026-09-30",
        retrieved_at="2026-11-03T12:00:00Z",
        data_hub_client=data_hub,
        source_revision="grios-main-sha",
    )
    assert result["data_hub_publish"]["status"] == "accepted"
    assert data_hub.published[1] == "grios-main-sha"
    assert data_hub.published[0]["ingestion_status"] == "RECONCILED_PUBLIC_SNAPSHOT"
