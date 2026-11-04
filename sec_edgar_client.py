from __future__ import annotations

import re
import math
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx


SEC_DATA_BASE = "https://data.sec.gov/"
SEC_ARCHIVES_BASE = "https://www.sec.gov/Archives/edgar/data/"
SUPPORTED_FORMS = {"13F-HR", "13F-HR/A"}


def normalize_cik(value: str | int) -> str:
    digits = re.sub(r"\D", "", str(value))
    if not digits or len(digits) > 10:
        raise ValueError("CIK must contain 1 to 10 digits.")
    return digits.zfill(10)


def normalize_accession(value: str) -> str:
    accession = value.strip()
    if not re.fullmatch(r"\d{10}-\d{2}-\d{6}", accession):
        raise ValueError("Invalid SEC accession number.")
    return accession


def _sec_url(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme != "https" or parsed.hostname not in {"sec.gov", "www.sec.gov", "data.sec.gov"}:
        raise ValueError("URL must point to an HTTPS SEC.gov host.")
    return value


@dataclass(frozen=True)
class SecFiling:
    cik: str
    accession_number: str
    form: str
    filing_date: str
    report_date: str | None
    primary_document: str
    primary_document_url: str


class SecEdgarClient:
    """Small, injectable SEC EDGAR submissions/index client.

    The caller must supply a descriptive User-Agent with a contact email, as
    requested by SEC developer guidance. This client does not crawl filings
    automatically or infer amendment metadata from filenames.
    """

    def __init__(
        self,
        *,
        user_agent: str,
        timeout: float = 20.0,
        min_request_interval: float = 0.11,
        client: Any | None = None,
    ) -> None:
        agent = user_agent.strip()
        if not agent or "@" not in agent:
            raise ValueError("Provide a descriptive SEC User-Agent containing a contact email.")
        self.headers = {
            "User-Agent": agent,
            "Accept-Encoding": "gzip, deflate",
        }
        if isinstance(min_request_interval, bool) or not isinstance(min_request_interval, (int, float)) or not math.isfinite(min_request_interval) or min_request_interval < 0:
            raise ValueError("min_request_interval must be a finite non-negative number of seconds.")
        self.timeout = timeout
        self.min_request_interval = float(min_request_interval)
        self._client = client
        self._request_lock = threading.Lock()
        self._last_request_at: float | None = None

    def _pace_request(self) -> None:
        """Serialize request starts to remain below the SEC fair-access ceiling."""
        with self._request_lock:
            now = time.monotonic()
            if self._last_request_at is not None:
                wait = self.min_request_interval - (now - self._last_request_at)
                if wait > 0:
                    time.sleep(wait)
            self._last_request_at = time.monotonic()

    def _get_json(self, url: str) -> dict[str, Any]:
        _sec_url(url)
        self._pace_request()
        if self._client is None:
            with httpx.Client(timeout=self.timeout, headers=self.headers) as client:
                response = client.get(url)
        else:
            response = self._client.get(url, headers=self.headers, timeout=self.timeout)
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("SEC response must be a JSON object.")
        return payload


    def download_document(self, url: str, *, max_bytes: int = 10_000_000) -> bytes:
        """Stream one SEC filing document with a strict host and size limit."""
        _sec_url(url)
        self._pace_request()
        if isinstance(max_bytes, bool) or not isinstance(max_bytes, int) or max_bytes <= 0:
            raise ValueError("max_bytes must be a positive integer.")

        def consume(response: Any) -> bytes:
            response.raise_for_status()
            declared = response.headers.get("content-length") if hasattr(response, "headers") else None
            if declared and declared.isdigit() and int(declared) > max_bytes:
                raise ValueError("SEC document exceeds configured download size limit.")
            chunks = []
            total = 0
            iterator = response.iter_bytes() if hasattr(response, "iter_bytes") else [response.content]
            for chunk in iterator:
                total += len(chunk)
                if total > max_bytes:
                    raise ValueError("SEC document exceeds configured download size limit.")
                chunks.append(chunk)
            content = b"".join(chunks)
            if not content:
                raise ValueError("SEC document response is empty.")
            return content

        if self._client is None:
            with httpx.Client(timeout=self.timeout, headers=self.headers) as client:
                with client.stream("GET", url) as response:
                    return consume(response)
        if hasattr(self._client, "stream"):
            with self._client.stream(
                "GET", url, headers=self.headers, timeout=self.timeout
            ) as response:
                return consume(response)
        response = self._client.get(url, headers=self.headers, timeout=self.timeout)
        return consume(response)

    def get_submissions(self, cik: str | int) -> dict[str, Any]:
        normalized = normalize_cik(cik)
        url = urljoin(SEC_DATA_BASE, f"submissions/CIK{normalized}.json")
        payload = self._get_json(url)
        if not isinstance(payload.get("filings"), dict):
            raise ValueError("SEC submissions response is missing filings metadata.")
        return payload

    @staticmethod
    def _filings_from_arrays(
        cik: str,
        arrays: dict[str, Any],
        *,
        start_date: str | None,
        end_date: str | None,
        include_amendments: bool,
    ) -> list[SecFiling]:
        forms = arrays.get("form", [])
        accessions = arrays.get("accessionNumber", [])
        dates = arrays.get("filingDate", [])
        report_dates = arrays.get("reportDate", [])
        documents = arrays.get("primaryDocument", [])
        lengths = {len(forms), len(accessions), len(dates), len(report_dates), len(documents)}
        if len(lengths) != 1:
            raise ValueError("SEC submissions filing arrays have inconsistent lengths.")
        results = []
        for form, accession, filing_date, report_date, document in zip(
            forms, accessions, dates, report_dates, documents
        ):
            if form not in SUPPORTED_FORMS or (form == "13F-HR/A" and not include_amendments):
                continue
            if not isinstance(filing_date, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", filing_date):
                raise ValueError("SEC filingDate must use YYYY-MM-DD.")
            try:
                datetime.strptime(filing_date, "%Y-%m-%d")
            except ValueError as exc:
                raise ValueError("SEC filingDate is not a valid calendar date.") from exc
            if start_date and filing_date < start_date:
                continue
            if end_date and filing_date > end_date:
                continue
            accession = normalize_accession(accession)
            if not isinstance(document, str) or not document.strip() or "/" in document or "\\" in document:
                raise ValueError("SEC primaryDocument must be a filename, not a path.")
            archive_dir = (
                f"{SEC_ARCHIVES_BASE}{int(cik)}/"
                f"{accession.replace('-', '')}/"
            )
            results.append(SecFiling(
                cik=cik,
                accession_number=accession,
                form=form,
                filing_date=filing_date,
                report_date=report_date or None,
                primary_document=document,
                primary_document_url=urljoin(archive_dir, document),
            ))
        return results

    def discover_13f_filings(
        self,
        cik: str | int,
        *,
        start_date: str | None = None,
        end_date: str | None = None,
        include_amendments: bool = True,
        include_historical: bool = False,
        max_historical_files: int = 1000,
    ) -> list[SecFiling]:
        normalized = normalize_cik(cik)
        for label, value in (("start_date", start_date), ("end_date", end_date)):
            if value is not None:
                try:
                    datetime.strptime(value, "%Y-%m-%d")
                except ValueError as exc:
                    raise ValueError(f"{label} must use YYYY-MM-DD.") from exc
        if start_date and end_date and start_date > end_date:
            raise ValueError("start_date must not be later than end_date.")
        if isinstance(max_historical_files, bool) or not isinstance(max_historical_files, int) or max_historical_files < 1:
            raise ValueError("max_historical_files must be a positive integer.")

        payload = self.get_submissions(normalized)
        filing_data = payload["filings"]
        recent = filing_data.get("recent")
        if not isinstance(recent, dict):
            raise ValueError("SEC submissions response is missing recent filing arrays.")
        results = self._filings_from_arrays(
            normalized, recent, start_date=start_date, end_date=end_date,
            include_amendments=include_amendments,
        )

        if include_historical:
            historical_files = filing_data.get("files", [])
            if not isinstance(historical_files, list):
                raise ValueError("SEC submissions historical files metadata must be a list.")
            if len(historical_files) > max_historical_files:
                raise ValueError(
                    f"SEC history has {len(historical_files)} files, exceeding max_historical_files={max_historical_files}."
                )
            for entry in historical_files:
                if not isinstance(entry, dict):
                    raise ValueError("SEC historical file metadata must be an object.")
                name = entry.get("name")
                if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9_.-]+\.json", name):
                    raise ValueError("SEC historical submissions filename is invalid.")
                filing_from = entry.get("filingFrom")
                filing_to = entry.get("filingTo")
                if start_date and isinstance(filing_to, str) and filing_to < start_date:
                    continue
                if end_date and isinstance(filing_from, str) and filing_from > end_date:
                    continue
                history_url = urljoin(SEC_DATA_BASE, f"submissions/{name}")
                historical_payload = self._get_json(history_url)
                historical_arrays = historical_payload.get("recent", historical_payload)
                if not isinstance(historical_arrays, dict):
                    raise ValueError("SEC historical submissions file has an invalid structure.")
                results.extend(self._filings_from_arrays(
                    normalized, historical_arrays, start_date=start_date,
                    end_date=end_date, include_amendments=include_amendments,
                ))

        unique = {item.accession_number: item for item in results}
        return sorted(unique.values(), key=lambda item: (item.filing_date, item.accession_number))

    def get_filing_index(self, cik: str | int, accession_number: str) -> list[dict[str, Any]]:
        normalized = normalize_cik(cik)
        accession = normalize_accession(accession_number)
        compact = accession.replace("-", "")
        url = f"{SEC_ARCHIVES_BASE}{int(normalized)}/{compact}/index.json"
        payload = self._get_json(url)
        directory = payload.get("directory")
        if not isinstance(directory, dict) or not isinstance(directory.get("item"), list):
            raise ValueError("SEC filing index has an invalid directory.item structure.")
        items = []
        for item in directory["item"]:
            if not isinstance(item, dict) or not isinstance(item.get("name"), str):
                continue
            name = item["name"]
            if "/" in name or "\\" in name:
                continue
            items.append({
                "name": name,
                "type": item.get("type"),
                "size": item.get("size"),
                "url": urljoin(url.rsplit("/", 1)[0] + "/", name),
            })
        return items

    def find_information_table_document(
        self, cik: str | int, accession_number: str
    ) -> dict[str, Any]:
        items = self.get_filing_index(cik, accession_number)
        candidates = [
            item for item in items
            if item["name"].lower().endswith(".xml")
            and ("infotable" in item["name"].lower()
                 or "informationtable" in item["name"].lower())
        ]
        if len(candidates) != 1:
            raise ValueError(
                f"Expected exactly one identifiable Information Table XML; found {len(candidates)}."
            )
        return candidates[0]
