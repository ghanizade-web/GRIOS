from __future__ import annotations

import hashlib
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


HOLDINGS_FORMS = {"13F-HR", "13F-HR/A"}
AMENDMENT_TYPES = {"RESTATEMENT", "NEW HOLDINGS"}
CUSIP_PATTERN = re.compile(r"^[A-Z0-9*@#]{9}$")


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].split(":")[-1]


def _children(element: ET.Element, name: str) -> list[ET.Element]:
    return [child for child in element if _local_name(child.tag).casefold() == name.casefold()]


def _first(element: ET.Element, name: str, required: bool = True) -> str | None:
    matches = _children(element, name)
    if not matches:
        if required:
            raise ValueError(f"Missing required 13F XML field: {name}")
        return None
    value = (matches[0].text or "").strip()
    if required and not value:
        raise ValueError(f"Empty required 13F XML field: {name}")
    return value or None


def _nonnegative_int(value: str | None, field: str) -> int:
    if value is None or not re.fullmatch(r"\d+", value.strip()):
        raise ValueError(f"{field} must be a non-negative integer.")
    return int(value)


def _iso(value: str, field: str) -> str:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be an ISO-8601 timestamp.") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{field} must include a timezone.")
    return parsed.astimezone(timezone.utc).isoformat(timespec="seconds")


def _date(value: str, field: str) -> str:
    try:
        return datetime.strptime(value, "%Y-%m-%d").date().isoformat()
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must use YYYY-MM-DD.") from exc


def _sec_source(value: str) -> str:
    parsed = urlparse(value)
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or host not in {"sec.gov", "www.sec.gov", "www.sec.gov"}:
        raise ValueError("source_url must be an HTTPS SEC.gov filing URL.")
    return value


def _parse_entry(node: ET.Element) -> dict[str, Any]:
    issuer = _first(node, "nameOfIssuer")
    title_class = _first(node, "titleOfClass")
    cusip = (_first(node, "cusip") or "").upper()
    if not CUSIP_PATTERN.fullmatch(cusip):
        raise ValueError(f"Invalid CUSIP format: {cusip!r}")
    value_thousands = _nonnegative_int(_first(node, "value"), "value")
    amount_nodes = _children(node, "shrsOrPrnAmt")
    if not amount_nodes:
        raise ValueError("Missing required 13F XML field: shrsOrPrnAmt")
    amount = _nonnegative_int(_first(amount_nodes[0], "sshPrnamt"), "sshPrnamt")
    amount_type = (_first(amount_nodes[0], "sshPrnamtType") or "").upper()
    if amount_type not in {"SH", "PRN"}:
        raise ValueError("sshPrnamtType must be SH or PRN.")
    discretion = (_first(node, "investmentDiscretion") or "").upper()
    if discretion not in {"SOLE", "DFND", "OTR"}:
        raise ValueError("investmentDiscretion must be SOLE, DFND or OTR.")
    put_call = _first(node, "putCall", required=False)
    if put_call:
        put_call = put_call.title()
        if put_call not in {"Put", "Call"}:
            raise ValueError("putCall must be Put or Call.")
    managers = _first(node, "otherManager", required=False)
    voting_nodes = _children(node, "votingAuthority")
    if not voting_nodes:
        raise ValueError("Missing required 13F XML field: votingAuthority")
    voting = {
        "sole": _nonnegative_int(_first(voting_nodes[0], "Sole"), "votingAuthority.Sole"),
        "shared": _nonnegative_int(_first(voting_nodes[0], "Shared"), "votingAuthority.Shared"),
        "none": _nonnegative_int(_first(voting_nodes[0], "None"), "votingAuthority.None"),
    }
    return {
        "issuer": issuer,
        "title_of_class": title_class,
        "cusip": cusip,
        "value_usd_thousands": value_thousands,
        "amount": amount,
        "amount_type": amount_type,
        "investment_discretion": discretion,
        "other_manager": managers,
        "put_call": put_call,
        "voting_authority": voting,
    }


def parse_13f_information_table(
    xml_content: str | bytes,
    *,
    accession_number: str,
    filer_cik: str,
    filer_name: str,
    form_type: str,
    filed_at: str,
    report_period: str,
    source_url: str,
    retrieved_at: str,
) -> dict[str, Any]:
    """Parse a single SEC 13F-HR information-table XML document.

    This parses reported positions only. It does not infer trades, beneficial
    ownership, proprietary manager capital, or real-time flows.
    """
    accession = accession_number.strip()
    if not re.fullmatch(r"\d{10}-\d{2}-\d{6}", accession):
        raise ValueError("accession_number must use SEC accession format.")
    cik = re.sub(r"\D", "", filer_cik)
    if not cik or len(cik) > 10:
        raise ValueError("filer_cik must contain 1 to 10 digits.")
    form = form_type.strip().upper()
    if form not in HOLDINGS_FORMS:
        raise ValueError("Only 13F-HR and 13F-HR/A holdings reports are supported; 13F-NT is not a holdings table.")
    filed = _iso(filed_at, "filed_at")
    retrieved = _iso(retrieved_at, "retrieved_at")
    period = _date(report_period, "report_period")
    source = _sec_source(source_url)
    try:
        root = ET.fromstring(xml_content)
    except (ET.ParseError, TypeError) as exc:
        raise ValueError("Invalid 13F XML document.") from exc
    if _local_name(root.tag).casefold() != "informationtable":
        raise ValueError("XML root must be informationTable.")
    entries = [
        child for child in root.iter()
        if _local_name(child.tag).casefold() == "infotable"
    ]
    if not entries:
        raise ValueError("13F information table contains no infoTable entries.")
    holdings = [_parse_entry(entry) for entry in entries]
    digest = hashlib.sha256(
        f"{accession}|{period}|{form}|{source}".encode()
    ).hexdigest()
    return {
        "filing_id": digest,
        "accession_number": accession,
        "filer_cik": cik.zfill(10),
        "filer_name": filer_name.strip(),
        "form_type": form,
        "filed_at": filed,
        "report_period": period,
        "source_url": source,
        "retrieved_at": retrieved,
        "holdings_count": len(holdings),
        "holdings": holdings,
        "interpretation": {
            "position_snapshot_only": True,
            "reported_value_unit": "USD_THOUSANDS",
            "does_not_prove_trade_date": True,
            "does_not_prove_manager_proprietary_ownership": True,
            "does_not_represent_real_time_flow": True,
        },
    }


def compare_13f_snapshots(
    prior: dict[str, Any], current: dict[str, Any]
) -> dict[str, Any]:
    """Compare two reported snapshots; output is not a transaction ledger."""
    if prior.get("filer_cik") != current.get("filer_cik"):
        raise ValueError("Cannot compare filings from different CIKs.")
    if prior.get("report_period") == current.get("report_period"):
        raise ValueError("Snapshots must have different report periods.")
    prior_period = _date(prior.get("report_period"), "prior.report_period")
    current_period = _date(current.get("report_period"), "current.report_period")
    if current_period <= prior_period:
        raise ValueError("Current report_period must be later than prior report_period.")

    def index(snapshot: dict[str, Any]) -> dict[tuple[str, str | None, str, str, str | None], dict[str, Any]]:
        result: dict[tuple[str, str | None, str, str, str | None], dict[str, Any]] = {}
        for item in snapshot.get("holdings", []):
            key = (
                item["cusip"], item.get("put_call"), item["amount_type"],
                item["investment_discretion"], item.get("other_manager"),
            )
            aggregate = result.setdefault(key, {
                "issuer": item["issuer"], "amount": 0, "value_usd_thousands": 0,
            })
            aggregate["amount"] += item["amount"]
            aggregate["value_usd_thousands"] += item["value_usd_thousands"]
        return result

    old = index(prior)
    new = index(current)
    changes = []
    keys = sorted(set(old) | set(new), key=lambda k: (k[0], k[1] or "", k[2], k[3], k[4] or ""))
    for key in keys:
        before = old.get(key)
        after = new.get(key)
        old_amount = before["amount"] if before else 0
        new_amount = after["amount"] if after else 0
        old_value = before["value_usd_thousands"] if before else 0
        new_value = after["value_usd_thousands"] if after else 0
        changes.append({
            "cusip": key[0],
            "put_call": key[1],
            "amount_type": key[2],
            "investment_discretion": key[3],
            "other_manager": key[4],
            "prior_amount": old_amount,
            "current_amount": new_amount,
            "amount_change": new_amount - old_amount,
            "prior_value_usd_thousands": old_value,
            "current_value_usd_thousands": new_value,
            "value_change_usd_thousands": new_value - old_value,
            "status": "NEWLY_REPORTED" if before is None else (
                "NO_LONGER_REPORTED" if after is None else "CONTINUED"
            ),
            "issuer": (after or before)["issuer"],
        })
    return {
        "filer_cik": current["filer_cik"],
        "prior_report_period": prior_period,
        "current_report_period": current_period,
        "changes": changes,
        "interpretation": (
            "Changes between two reported snapshots are not proof of purchases, "
            "sales, transaction dates, beneficial ownership, or proprietary capital. "
            "They may reflect valuation changes, reporting scope, amendments, "
            "manager discretion, options, or other filing effects."
        ),
    }
