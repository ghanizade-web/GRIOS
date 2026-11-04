from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Any

from sec_13f_parser import parse_13f_information_table
from sec_edgar_client import SecEdgarClient, normalize_accession, normalize_cik


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].split(":")[-1]


def _text(root: ET.Element, name: str, *, required: bool = False) -> str | None:
    for node in root.iter():
        if _local_name(node.tag).casefold() == name.casefold():
            value = (node.text or "").strip()
            if value:
                return value
    if required:
        raise ValueError(f"SEC 13F cover page is missing {name}.")
    return None


def parse_13f_cover_page(xml_content: str | bytes, *, form_type: str) -> dict[str, Any]:
    """Extract filing-level identity and amendment metadata from SEC cover XML."""
    form = form_type.strip().upper()
    if form not in {"13F-HR", "13F-HR/A"}:
        raise ValueError("Only 13F-HR and 13F-HR/A cover pages are supported.")
    try:
        root = ET.fromstring(xml_content)
    except (ET.ParseError, TypeError) as exc:
        raise ValueError("Invalid SEC 13F cover-page XML.") from exc

    period = _text(root, "reportCalendarOrQuarter", required=True)
    try:
        period = datetime.strptime(period, "%Y-%m-%d").date().isoformat()
    except ValueError as exc:
        raise ValueError("reportCalendarOrQuarter must use YYYY-MM-DD.") from exc

    manager_name = None
    for node in root.iter():
        if _local_name(node.tag).casefold() == "filingmanager":
            manager_name = _text(node, "name")
            break
    if not manager_name:
        manager_name = _text(root, "name", required=True)

    is_amendment = (_text(root, "isAmendment") or "").casefold()
    if form == "13F-HR":
        if is_amendment in {"true", "1", "yes"}:
            raise ValueError("13F-HR cover page cannot declare an amendment.")
        return {
            "filer_name": manager_name,
            "report_period": period,
            "is_amendment": False,
            "amendment_number": None,
            "amendment_type": None,
        }

    if is_amendment not in {"true", "1", "yes"}:
        raise ValueError("13F-HR/A cover page must declare isAmendment=true.")
    raw_number = _text(root, "amendmentNo", required=True)
    if not re.fullmatch(r"\d{1,2}", raw_number):
        raise ValueError("amendmentNo must be an integer between 1 and 99.")
    number = int(raw_number)
    if not 1 <= number <= 99:
        raise ValueError("amendmentNo must be an integer between 1 and 99.")
    amendment_type = (_text(root, "amendmentType", required=True) or "").strip().upper()
    if amendment_type not in {"RESTATEMENT", "NEW HOLDINGS"}:
        raise ValueError("amendmentType must be RESTATEMENT or NEW HOLDINGS.")
    return {
        "filer_name": manager_name,
        "report_period": period,
        "is_amendment": True,
        "amendment_number": number,
        "amendment_type": amendment_type,
    }


def ingest_13f_filing(
    client: SecEdgarClient,
    cik: str | int,
    accession_number: str,
    *,
    retrieved_at: str,
) -> dict[str, Any]:
    """Discover, download, parse and normalize one SEC 13F filing.

    This is a single-filing ingestion operation. Historical pagination,
    automatic scheduling, persistence and Data Hub publishing are separate.
    """
    normalized_cik = normalize_cik(cik)
    accession = normalize_accession(accession_number)
    filings = client.discover_13f_filings(normalized_cik)
    filing = next((item for item in filings if item.accession_number == accession), None)
    if filing is None:
        raise ValueError("Requested accession was not found in SEC recent 13F submissions.")

    cover_xml = client.download_document(filing.primary_document_url)
    information_table = client.find_information_table_document(normalized_cik, accession)
    table_xml = client.download_document(information_table["url"])
    cover = parse_13f_cover_page(cover_xml, form_type=filing.form)

    if filing.report_date and filing.report_date != cover["report_period"]:
        raise ValueError("SEC submissions reportDate conflicts with the cover-page report period.")

    filed_at = datetime.strptime(filing.filing_date, "%Y-%m-%d").replace(
        tzinfo=timezone.utc
    ).isoformat(timespec="seconds")
    submissions = client.get_submissions(normalized_cik)
    filing_result = parse_13f_information_table(
        table_xml,
        accession_number=filing.accession_number,
        filer_cik=normalized_cik,
        filer_name=cover["filer_name"] or submissions.get("name", ""),
        form_type=filing.form,
        filed_at=filed_at,
        report_period=cover["report_period"],
        source_url=information_table["url"],
        retrieved_at=retrieved_at,
        amendment_number=cover["amendment_number"],
        amendment_type=cover["amendment_type"],
    )
    filing_result["cover_page_source_url"] = filing.primary_document_url
    filing_result["ingestion_status"] = "PARSED"
    filing_result["ingestion_scope"] = "SINGLE_FILING"
    return filing_result
