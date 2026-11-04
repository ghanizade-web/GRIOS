import pytest

from sec_13f_parser import compare_13f_snapshots, parse_13f_information_table


XML = """<?xml version="1.0" encoding="UTF-8"?>
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
  <infoTable>
    <nameOfIssuer>Example Corporation</nameOfIssuer>
    <titleOfClass>COM</titleOfClass>
    <cusip>123456780</cusip>
    <value>5000</value>
    <shrsOrPrnAmt><sshPrnamt>25000</sshPrnamt><sshPrnamtType>SH</sshPrnamtType></shrsOrPrnAmt>
    <investmentDiscretion>DFND</investmentDiscretion>
    <putCall>Call</putCall>
    <otherManager>1</otherManager>
    <votingAuthority><Sole>0</Sole><Shared>25000</Shared><None>0</None></votingAuthority>
  </infoTable>
</informationTable>
"""

BASE = dict(
    accession_number="0000123456-26-000001",
    filer_cik="123456",
    filer_name="Example Adviser",
    form_type="13F-HR",
    filed_at="2026-11-01T12:00:00Z",
    report_period="2026-09-30",
    source_url="https://www.sec.gov/Archives/edgar/data/123456/000012345626000001/example.xml",
    retrieved_at="2026-11-02T12:00:00Z",
)


def parse(**overrides):
    return parse_13f_information_table(XML, **(BASE | overrides))


def test_parse_namespace_and_reported_fields():
    result = parse()
    assert result["holdings_count"] == 2
    assert result["filer_cik"] == "0000123456"
    assert result["holdings"][0]["value_usd_thousands"] == 125000
    assert result["holdings"][1]["put_call"] == "Call"
    assert result["interpretation"]["does_not_prove_manager_proprietary_ownership"]


def test_reject_notice_form_and_non_sec_url():
    with pytest.raises(ValueError, match="Only 13F-HR"):
        parse(form_type="13F-NT")
    with pytest.raises(ValueError, match="SEC.gov"):
        parse(source_url="https://example.com/filing.xml")


def test_reject_malformed_xml_and_invalid_cusip():
    with pytest.raises(ValueError, match="Invalid 13F XML"):
        parse_13f_information_table("<broken", **BASE)
    bad = XML.replace("123456789", "BAD")
    with pytest.raises(ValueError, match="Invalid CUSIP"):
        parse_13f_information_table(bad, **BASE)


def test_compare_snapshots_reports_position_change_not_trade():
    prior = parse()
    current = parse(
        accession_number="0000123456-26-000002",
        report_period="2026-12-31",
        filed_at="2027-02-01T12:00:00Z",
        source_url="https://www.sec.gov/Archives/edgar/data/123456/000012345626000002/example.xml",
    )
    current["holdings"][0]["amount"] += 100
    comparison = compare_13f_snapshots(prior, current)
    assert comparison["changes"][0]["amount_change"] == 100
    assert "not proof of purchases" in comparison["interpretation"]


def test_compare_requires_same_filer_and_chronological_periods():
    prior = parse()
    later = parse(
        accession_number="0000123456-26-000002",
        report_period="2026-12-31",
        filed_at="2027-02-01T12:00:00Z",
        source_url="https://www.sec.gov/Archives/edgar/data/123456/000012345626000002/example.xml",
    )
    later["filer_cik"] = "0000000001"
    with pytest.raises(ValueError, match="different CIKs"):
        compare_13f_snapshots(prior, later)

def test_compare_aggregates_repeated_rows_and_handles_put_call_null():
    prior = parse()
    current = parse(
        accession_number="0000123456-26-000002",
        report_period="2026-12-31",
        filed_at="2027-02-01T12:00:00Z",
        source_url="https://www.sec.gov/Archives/edgar/data/123456/000012345626000002/example.xml",
    )
    current["holdings"].append(dict(current["holdings"][0]))
    comparison = compare_13f_snapshots(prior, current)
    ordinary = next(
        row for row in comparison["changes"]
        if row["cusip"] == "123456789" and row["put_call"] is None
    )
    assert ordinary["current_amount"] == 2000000
    assert ordinary["amount_change"] == 1000000
