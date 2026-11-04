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
DOLLAR_VALUE_RULE_EFFECTIVE_DATE = "2023-01-03"
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
    if parsed.scheme != "https" or host not in {"sec.gov", "www.sec.gov"}:
        raise ValueError("source_url must be an HTTPS SEC.gov filing URL.")
    return value


def _parse_entry(node: ET.Element) -> dict[str, Any]:
    issuer = _first(node, "nameOfIssuer")
    title_class = _first(node, "titleOfClass")
    cusip = (_first(node, "cusip") or "").upper()
    if not CUSIP_PATTERN.fullmatch(cusip):
        raise ValueError(f"Invalid CUSIP format: {cusip!r}")
    reported_value = _nonnegative_int(_first(node, "value"), "value")
    figi = _first(node, "figi", required=False)
    if figi:
        figi = figi.upper()
        if not re.fullmatch(r"[A-Z0-9]{12}", figi):
            raise ValueError(f"Invalid FIGI format: {figi!r}")
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
        "figi": figi,
        "reported_value_raw": reported_value,
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
    amendment_number: int | None = None,
    amendment_type: str | None = None,
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
    if form == "13F-HR":
        if amendment_number is not None or amendment_type is not None:
            raise ValueError("Original 13F-HR filings cannot carry amendment metadata.")
    else:
        if isinstance(amendment_number, bool) or not isinstance(amendment_number, int) or not 1 <= amendment_number <= 99:
            raise ValueError("13F-HR/A requires amendment_number between 1 and 99.")
        amendment_type = (amendment_type or "").strip().upper()
        if amendment_type not in AMENDMENT_TYPES:
            raise ValueError("13F-HR/A requires amendment_type RESTATEMENT or NEW HOLDINGS.")
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
    reported_value_unit = "USD" if filed[:10] >= DOLLAR_VALUE_RULE_EFFECTIVE_DATE else "USD_THOUSANDS"
    for holding in holdings:
        raw_value = holding.pop("reported_value_raw")
        holding["reported_value"] = raw_value
        holding["reported_value_unit"] = reported_value_unit
        holding["value_usd"] = raw_value if reported_value_unit == "USD" else raw_value * 1000
    digest = hashlib.sha256(
        f"{accession}|{period}|{form}|{source}".encode()
    ).hexdigest()
    return {
        "filing_id": digest,
        "accession_number": accession,
        "filer_cik": cik.zfill(10),
        "filer_name": filer_name.strip(),
        "form_type": form,
        "amendment_number": amendment_number,
        "amendment_type": amendment_type,
        "filed_at": filed,
        "report_period": period,
        "source_url": source,
        "retrieved_at": retrieved,
        "holdings_count": len(holdings),
        "holdings": holdings,
        "interpretation": {
            "position_snapshot_only": True,
            "reported_value_unit": reported_value_unit,
            "normalized_value_unit": "USD",
            "value_rule_effective_date": DOLLAR_VALUE_RULE_EFFECTIVE_DATE,
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
                "issuer": item["issuer"], "figi": item.get("figi"),
                "amount": 0, "value_usd": 0,
            })
            aggregate["figi"] = aggregate.get("figi") or item.get("figi")
            aggregate["amount"] += item["amount"]
            aggregate["value_usd"] += item["value_usd"]
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
        old_value = before["value_usd"] if before else 0
        new_value = after["value_usd"] if after else 0
        changes.append({
            "cusip": key[0],
            "figi": (after or before).get("figi"),
            "put_call": key[1],
            "amount_type": key[2],
            "investment_discretion": key[3],
            "other_manager": key[4],
            "prior_amount": old_amount,
            "current_amount": new_amount,
            "amount_change": new_amount - old_amount,
            "prior_value_usd": old_value,
            "current_value_usd": new_value,
            "value_change_usd": new_value - old_value,
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


def reconcile_13f_filing_chain(filings: list[dict[str, Any]]) -> dict[str, Any]:
    """Reconstruct a quarter's public holdings from an original 13F and amendments.

    RESTATEMENT replaces the full prior public snapshot. NEW HOLDINGS supplements
    the then-current public snapshot. Filing order is validated using amendment
    sequence and filing timestamps; no trade or ownership inference is made.
    """
    if not filings:
        raise ValueError("At least one 13F filing is required.")
    first = filings[0]
    cik = first.get("filer_cik")
    period = _date(first.get("report_period"), "report_period")
    for filing in filings:
        if filing.get("filer_cik") != cik:
            raise ValueError("All filings must belong to the same filer CIK.")
        if _date(filing.get("report_period"), "report_period") != period:
            raise ValueError("All filings must have the same report period.")
        _iso(filing.get("filed_at"), "filed_at")
        if filing.get("form_type") not in HOLDINGS_FORMS:
            raise ValueError("Unsupported form type in filing chain.")

    originals = [f for f in filings if f["form_type"] == "13F-HR"]
    amendments = [f for f in filings if f["form_type"] == "13F-HR/A"]
    if len(originals) != 1:
        raise ValueError("Exactly one original 13F-HR filing is required.")
    original = originals[0]
    if original.get("amendment_number") is not None or original.get("amendment_type") is not None:
        raise ValueError("Original filing contains amendment metadata.")
    if any(f.get("amendment_number") is None or f.get("amendment_type") not in AMENDMENT_TYPES for f in amendments):
        raise ValueError("Every 13F-HR/A filing requires valid amendment metadata.")
    amendments.sort(key=lambda f: f["amendment_number"])
    numbers = [f["amendment_number"] for f in amendments]
    if len(numbers) != len(set(numbers)):
        raise ValueError("Duplicate amendment number in filing chain.")
    previous_filed = _iso(original["filed_at"], "filed_at")
    for amendment in amendments:
        filed = _iso(amendment["filed_at"], "filed_at")
        if filed <= previous_filed:
            raise ValueError("Amendments must be filed after the preceding filing in amendment-number order.")
        previous_filed = filed

    def key_for(item: dict[str, Any]) -> tuple[str, str | None, str, str, str | None]:
        return (
            item["cusip"], item.get("put_call"), item["amount_type"],
            item["investment_discretion"], item.get("other_manager"),
        )

    def aggregate(items: list[dict[str, Any]]) -> dict[tuple[str, str | None, str, str, str | None], dict[str, Any]]:
        result: dict[tuple[str, str | None, str, str, str | None], dict[str, Any]] = {}
        for item in items:
            key = key_for(item)
            row = result.setdefault(key, {
                "issuer": item["issuer"],
                "title_of_class": item["title_of_class"],
                "cusip": item["cusip"],
                "figi": item.get("figi"),
                "put_call": item.get("put_call"),
                "amount_type": item["amount_type"],
                "investment_discretion": item["investment_discretion"],
                "other_manager": item.get("other_manager"),
                "amount": 0,
                "value_usd": 0,
                "voting_authority": {"sole": 0, "shared": 0, "none": 0},
            })
            row["figi"] = row.get("figi") or item.get("figi")
            row["amount"] += item["amount"]
            row["value_usd"] += item["value_usd"]
            for field in ("sole", "shared", "none"):
                row["voting_authority"][field] += item["voting_authority"][field]
        return result

    positions = aggregate(original["holdings"])
    applied = [{
        "accession_number": original["accession_number"],
        "form_type": original["form_type"],
        "amendment_number": None,
        "amendment_type": "ORIGINAL",
        "filed_at": original["filed_at"],
        "source_url": original["source_url"],
        "cover_page_source_url": original.get("cover_page_source_url"),
        "effect": "BASE_SNAPSHOT",
    }]
    for amendment in amendments:
        incoming = aggregate(amendment["holdings"])
        if amendment["amendment_type"] == "RESTATEMENT":
            positions = incoming
            effect = "REPLACED_PRIOR_SNAPSHOT"
        else:
            for key, row in incoming.items():
                if key not in positions:
                    positions[key] = row
                else:
                    existing = positions[key]
                    existing["amount"] += row["amount"]
                    existing["value_usd"] += row["value_usd"]
                    for field in ("sole", "shared", "none"):
                        existing["voting_authority"][field] += row["voting_authority"][field]
            effect = "SUPPLEMENTED_PRIOR_SNAPSHOT"
        applied.append({
            "accession_number": amendment["accession_number"],
            "form_type": amendment["form_type"],
            "amendment_number": amendment["amendment_number"],
            "amendment_type": amendment["amendment_type"],
            "filed_at": amendment["filed_at"],
            "source_url": amendment["source_url"],
            "cover_page_source_url": amendment.get("cover_page_source_url"),
            "effect": effect,
        })

    final_positions = sorted(
        positions.values(),
        key=lambda row: (row["cusip"], row["put_call"] or "", row["amount_type"],
                         row["investment_discretion"], row["other_manager"] or ""),
    )
    return {
        "filer_cik": cik,
        "report_period": period,
        "latest_filed_at": previous_filed,
        "applied_filings": applied,
        "holdings_count": len(final_positions),
        "holdings": final_positions,
        "interpretation": (
            "Reconstructed public reported holdings only. Amendment handling follows "
            "the declared RESTATEMENT (replace) and NEW HOLDINGS (supplement) types. "
            "This is not a transaction ledger and does not establish trade dates, "
            "beneficial ownership, proprietary manager capital, or real-time flows."
        ),
    }
