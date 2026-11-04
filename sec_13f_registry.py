from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


def _utc(value: Any, field: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be an ISO-8601 timestamp.")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} must be an ISO-8601 timestamp.") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{field} must include a timezone.")
    return parsed.astimezone(timezone.utc).isoformat(timespec="seconds")


def _sec_url(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} is required.")
    parsed = urlparse(value)
    if parsed.scheme != "https" or parsed.hostname not in {"sec.gov", "www.sec.gov"}:
        raise ValueError(f"{field} must be an HTTPS SEC.gov URL.")
    return value


def _nonnegative_integer(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{field} must be a non-negative integer.")
    return value


def _stable_id(namespace: str, payload: Any) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(f"{namespace}:{canonical}".encode("utf-8")).hexdigest()


def _normalize_report(report: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(report, dict):
        raise ValueError("report must be an object.")
    if report.get("ingestion_status") != "RECONCILED_PUBLIC_SNAPSHOT":
        raise ValueError("Only reconciled public 13F report-period snapshots can be persisted.")
    cik = report.get("filer_cik")
    if not isinstance(cik, str) or not re.fullmatch(r"\d{10}", cik):
        raise ValueError("filer_cik must be a zero-padded 10-digit CIK.")
    period = report.get("report_period")
    if not isinstance(period, str):
        raise ValueError("report_period must use YYYY-MM-DD.")
    try:
        period = datetime.strptime(period, "%Y-%m-%d").date().isoformat()
    except ValueError as exc:
        raise ValueError("report_period must use YYYY-MM-DD.") from exc
    latest_filed = _utc(report.get("latest_filed_at"), "latest_filed_at")
    filings = report.get("applied_filings")
    holdings = report.get("holdings")
    if not isinstance(filings, list) or not filings:
        raise ValueError("applied_filings must contain at least one filing.")
    if not isinstance(holdings, list):
        raise ValueError("holdings must be a list.")
    if report.get("holdings_count") != len(holdings):
        raise ValueError("holdings_count does not match the holdings array.")

    normalized_filings = []
    seen_accessions = set()
    previous_filed = None
    for filing in filings:
        if not isinstance(filing, dict):
            raise ValueError("Each applied filing must be an object.")
        accession = filing.get("accession_number")
        if not isinstance(accession, str) or not re.fullmatch(r"\d{10}-\d{2}-\d{6}", accession):
            raise ValueError("Invalid accession_number in applied filing ledger.")
        if accession in seen_accessions:
            raise ValueError("Duplicate accession_number in applied filing ledger.")
        seen_accessions.add(accession)
        form_type = filing.get("form_type")
        amendment_number = filing.get("amendment_number")
        amendment_type = filing.get("amendment_type")
        if form_type == "13F-HR":
            if amendment_number is not None or amendment_type != "ORIGINAL":
                raise ValueError("Original 13F-HR filing has invalid amendment metadata.")
        elif form_type == "13F-HR/A":
            if isinstance(amendment_number, bool) or not isinstance(amendment_number, int) or not 1 <= amendment_number <= 99:
                raise ValueError("13F-HR/A requires amendment_number between 1 and 99.")
            if amendment_type not in {"RESTATEMENT", "NEW HOLDINGS"}:
                raise ValueError("13F-HR/A requires a valid amendment_type.")
        else:
            raise ValueError("Unsupported form_type in applied filing ledger.")
        filed_at = _utc(filing.get("filed_at"), "filing.filed_at")
        if previous_filed and filed_at < previous_filed:
            raise ValueError("Applied filing timestamps must be chronological.")
        previous_filed = filed_at
        effect = filing.get("effect")
        if effect not in {"BASE_SNAPSHOT", "REPLACED_PRIOR_SNAPSHOT", "SUPPLEMENTED_PRIOR_SNAPSHOT"}:
            raise ValueError("Unsupported amendment reconciliation effect.")
        normalized_filings.append({
            "accession_number": accession,
            "form_type": form_type,
            "amendment_number": amendment_number,
            "amendment_type": amendment_type,
            "filed_at": filed_at,
            "source_url": _sec_url(filing.get("source_url"), "filing.source_url"),
            "cover_page_source_url": (
                _sec_url(filing["cover_page_source_url"], "filing.cover_page_source_url")
                if filing.get("cover_page_source_url") else None
            ),
            "effect": effect,
        })

    normalized_holdings = []
    for holding in holdings:
        if not isinstance(holding, dict):
            raise ValueError("Each holding must be an object.")
        cusip = holding.get("cusip")
        if not isinstance(cusip, str) or not re.fullmatch(r"[A-Z0-9*@#]{9}", cusip):
            raise ValueError("Invalid CUSIP in holdings.")
        amount = _nonnegative_integer(holding.get("amount"), "holding.amount")
        value_usd = _nonnegative_integer(holding.get("value_usd"), "holding.value_usd")
        figi = holding.get("figi")
        if figi is not None and (
            not isinstance(figi, str) or not re.fullmatch(r"[A-Z0-9]{12}", figi)
        ):
            raise ValueError("holding.figi must be a 12-character FIGI or null.")
        voting = holding.get("voting_authority")
        if not isinstance(voting, dict):
            raise ValueError("holding.voting_authority must be an object.")
        voting = {
            key: _nonnegative_integer(voting.get(key), f"voting_authority.{key}")
            for key in ("sole", "shared", "none")
        }
        normalized_holdings.append({
            "issuer": str(holding.get("issuer") or "").strip(),
            "title_of_class": str(holding.get("title_of_class") or "").strip(),
            "cusip": cusip,
            "figi": figi,
            "put_call": holding.get("put_call"),
            "amount_type": holding.get("amount_type"),
            "investment_discretion": holding.get("investment_discretion"),
            "other_manager": holding.get("other_manager"),
            "amount": amount,
            "value_usd": value_usd,
            "voting_authority": voting,
        })

    identity = {
        "filer_cik": cik,
        "report_period": period,
        "latest_filed_at": latest_filed,
        "accessions": [item["accession_number"] for item in normalized_filings],
        "holdings_hash": _stable_id("grios-sec-13f-holdings-v1", normalized_holdings),
    }
    snapshot_id = _stable_id("grios-sec-13f-snapshot-v1", identity)
    return {
        "snapshot_id": snapshot_id,
        "filer_cik": cik,
        "report_period": period,
        "latest_filed_at": latest_filed,
        "holdings_count": len(normalized_holdings),
        "filings": normalized_filings,
        "holdings": normalized_holdings,
    }


def prepare_13f_data_hub_payload(
    report: dict[str, Any],
    *,
    source_revision: str | None = None,
) -> dict[str, Any]:
    """Build the validated, versioned payload accepted by the GRIOS Data Hub."""
    item = _normalize_report(report)
    if source_revision is not None and (
        not isinstance(source_revision, str) or len(source_revision) > 160
    ):
        raise ValueError("source_revision must be text of at most 160 characters.")
    holdings = []
    for holding in item["holdings"]:
        row_identity = {
            key: holding[key] for key in (
                "cusip", "put_call", "amount_type",
                "investment_discretion", "other_manager",
            )
        }
        holdings.append({
            **holding,
            "row_id": _stable_id("grios-sec-13f-position-v1", row_identity),
        })
    snapshot = {
        "snapshot_id": item["snapshot_id"],
        "filer_cik": item["filer_cik"],
        "report_period": item["report_period"],
        "latest_filed_at": item["latest_filed_at"],
        "holdings_count": item["holdings_count"],
        "source_revision": source_revision,
        "applied_filings": item["filings"],
        "holdings": holdings,
    }
    return {"schema_version": "1.0", "snapshot": snapshot}


def initialize_13f_registry(database: str | Path) -> None:
    path = Path(database)
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS sec_13f_snapshots (
                snapshot_id TEXT PRIMARY KEY,
                filer_cik TEXT NOT NULL,
                report_period TEXT NOT NULL,
                latest_filed_at TEXT NOT NULL,
                holdings_count INTEGER NOT NULL,
                inserted_at TEXT NOT NULL,
                UNIQUE(filer_cik, report_period, latest_filed_at, snapshot_id)
            );
            CREATE INDEX IF NOT EXISTS sec_13f_latest_snapshot_idx
                ON sec_13f_snapshots(filer_cik, report_period, latest_filed_at DESC);
            CREATE TABLE IF NOT EXISTS sec_13f_snapshot_filings (
                snapshot_id TEXT NOT NULL REFERENCES sec_13f_snapshots(snapshot_id),
                accession_number TEXT NOT NULL,
                form_type TEXT NOT NULL,
                amendment_number INTEGER,
                amendment_type TEXT,
                filed_at TEXT NOT NULL,
                source_url TEXT NOT NULL,
                cover_page_source_url TEXT,
                effect TEXT NOT NULL,
                PRIMARY KEY(snapshot_id, accession_number)
            );
            CREATE TABLE IF NOT EXISTS sec_13f_snapshot_holdings (
                snapshot_id TEXT NOT NULL REFERENCES sec_13f_snapshots(snapshot_id),
                row_id TEXT NOT NULL,
                issuer TEXT NOT NULL,
                title_of_class TEXT NOT NULL,
                cusip TEXT NOT NULL,
                figi TEXT,
                put_call TEXT,
                amount_type TEXT NOT NULL,
                investment_discretion TEXT NOT NULL,
                other_manager TEXT,
                amount REAL NOT NULL,
                value_usd REAL NOT NULL,
                voting_authority_json TEXT NOT NULL,
                PRIMARY KEY(snapshot_id, row_id)
            );
            CREATE INDEX IF NOT EXISTS sec_13f_holdings_cusip_idx
                ON sec_13f_snapshot_holdings(cusip, snapshot_id);
            """
        )


def persist_13f_snapshot(database: str | Path, report: dict[str, Any]) -> dict[str, Any]:
    item = _normalize_report(report)
    initialize_13f_registry(database)
    inserted_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with sqlite3.connect(database) as db:
        cursor = db.execute(
            """INSERT OR IGNORE INTO sec_13f_snapshots
            (snapshot_id, filer_cik, report_period, latest_filed_at, holdings_count, inserted_at)
            VALUES (?, ?, ?, ?, ?, ?)""",
            (
                item["snapshot_id"], item["filer_cik"], item["report_period"],
                item["latest_filed_at"], item["holdings_count"], inserted_at,
            ),
        )
        snapshot_inserted = cursor.rowcount == 1
        filing_rows = [
            (
                item["snapshot_id"], filing["accession_number"], filing["form_type"],
                filing["amendment_number"], filing["amendment_type"], filing["filed_at"],
                filing["source_url"], filing["cover_page_source_url"], filing["effect"],
            )
            for filing in item["filings"]
        ]
        db.executemany(
            """INSERT OR IGNORE INTO sec_13f_snapshot_filings
            (snapshot_id, accession_number, form_type, amendment_number, amendment_type,
             filed_at, source_url, cover_page_source_url, effect)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            filing_rows,
        )
        holding_rows = []
        for holding in item["holdings"]:
            row_identity = {
                key: holding[key] for key in (
                    "cusip", "put_call", "amount_type",
                    "investment_discretion", "other_manager",
                )
            }
            row_id = _stable_id("grios-sec-13f-position-v1", row_identity)
            holding_rows.append((
                item["snapshot_id"], row_id, holding["issuer"], holding["title_of_class"],
                holding["cusip"], holding["figi"], holding["put_call"],
                holding["amount_type"], holding["investment_discretion"],
                holding["other_manager"], holding["amount"], holding["value_usd"],
                json.dumps(holding["voting_authority"], sort_keys=True),
            ))
        db.executemany(
            """INSERT OR IGNORE INTO sec_13f_snapshot_holdings
            (snapshot_id, row_id, issuer, title_of_class, cusip, figi, put_call,
             amount_type, investment_discretion, other_manager, amount, value_usd,
             voting_authority_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            holding_rows,
        )
    return {
        "snapshot_id": item["snapshot_id"],
        "snapshot_inserted": snapshot_inserted,
        "filings_stored": len(item["filings"]),
        "holdings_stored": len(item["holdings"]),
    }


def get_13f_snapshot(
    database: str | Path,
    *,
    filer_cik: str,
    report_period: str,
    snapshot_id: str | None = None,
) -> dict[str, Any] | None:
    path = Path(database)
    if not path.exists():
        return None
    with sqlite3.connect(path) as db:
        db.row_factory = sqlite3.Row
        if snapshot_id:
            snapshot = db.execute(
                "SELECT * FROM sec_13f_snapshots WHERE snapshot_id = ? AND filer_cik = ? AND report_period = ?",
                (snapshot_id, filer_cik, report_period),
            ).fetchone()
        else:
            snapshot = db.execute(
                """SELECT * FROM sec_13f_snapshots
                   WHERE filer_cik = ? AND report_period = ?
                   ORDER BY latest_filed_at DESC, inserted_at DESC LIMIT 1""",
                (filer_cik, report_period),
            ).fetchone()
        if snapshot is None:
            return None
        selected_id = snapshot["snapshot_id"]
        filings = db.execute(
            """SELECT accession_number, form_type, amendment_number, amendment_type,
                      filed_at, source_url, cover_page_source_url, effect
               FROM sec_13f_snapshot_filings
               WHERE snapshot_id = ? ORDER BY filed_at, accession_number""",
            (selected_id,),
        ).fetchall()
        holdings = db.execute(
            """SELECT issuer, title_of_class, cusip, figi, put_call, amount_type,
                      investment_discretion, other_manager, amount, value_usd,
                      voting_authority_json
               FROM sec_13f_snapshot_holdings WHERE snapshot_id = ?
               ORDER BY cusip, put_call, amount_type, investment_discretion, other_manager""",
            (selected_id,),
        ).fetchall()
    return {
        "snapshot_id": selected_id,
        "filer_cik": snapshot["filer_cik"],
        "report_period": snapshot["report_period"],
        "latest_filed_at": snapshot["latest_filed_at"],
        "holdings_count": snapshot["holdings_count"],
        "applied_filings": [dict(row) for row in filings],
        "holdings": [
            {
                **{key: row[key] for key in row.keys() if key != "voting_authority_json"},
                "voting_authority": json.loads(row["voting_authority_json"]),
            }
            for row in holdings
        ],
    }
