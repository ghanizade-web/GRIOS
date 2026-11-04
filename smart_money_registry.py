from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


EVIDENCE_TYPES = {
    "ACTUAL_PURCHASE",
    "PURCHASE_ORDER",
    "SUPPLY_CONTRACT",
    "CORPORATE_CAPEX",
    "M_AND_A_ANNOUNCEMENT",
    "HOLDING_DISCLOSURE",
    "FUND_FLOW",
    "STATED_INTEREST",
}
CAPITAL_ORIGINS = {
    "CLIENT_ASSETS",
    "PROPRIETARY",
    "SOVEREIGN",
    "CORPORATE_BALANCE_SHEET",
    "UNKNOWN",
}
EXECUTION_STATUSES = {
    "RUMORED",
    "ANNOUNCED",
    "SIGNED",
    "PARTIALLY_EXECUTED",
    "COMPLETED",
    "CANCELLED",
    "UNKNOWN",
}
VERIFICATION_STATUSES = {
    "VERIFIED",
    "CORROBORATED",
    "PARTIALLY_VERIFIED",
    "UNVERIFIED",
    "DISPUTED",
    "REJECTED",
}


def _required_text(record: dict[str, Any], field: str) -> str:
    value = record.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} is required.")
    return value.strip()


def _optional_text(record: dict[str, Any], field: str) -> str | None:
    value = record.get(field)
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        raise ValueError(f"{field} must be text.")
    return value.strip() or None


def _timestamp(value: Any, field: str, required: bool = False) -> str | None:
    if value is None or value == "":
        if required:
            raise ValueError(f"{field} is required.")
        return None
    if not isinstance(value, str):
        raise ValueError(f"{field} must be an ISO-8601 timestamp.")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} must be an ISO-8601 timestamp.") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{field} must include a timezone.")
    return parsed.astimezone(timezone.utc).isoformat(timespec="seconds")


def normalize_evidence(record: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(record, dict):
        raise ValueError("Evidence record must be an object.")

    evidence_type = _required_text(record, "evidence_type").upper()
    capital_origin = _required_text(record, "capital_origin").upper()
    execution_status = _required_text(record, "execution_status").upper()
    verification_status = _required_text(record, "verification_status").upper()
    if evidence_type not in EVIDENCE_TYPES:
        raise ValueError("Unsupported evidence_type.")
    if capital_origin not in CAPITAL_ORIGINS:
        raise ValueError("Unsupported capital_origin.")
    if execution_status not in EXECUTION_STATUSES:
        raise ValueError("Unsupported execution_status.")
    if verification_status not in VERIFICATION_STATUSES:
        raise ValueError("Unsupported verification_status.")

    source_url = _required_text(record, "source_url")
    parsed_url = urlparse(source_url)
    if parsed_url.scheme != "https" or not parsed_url.netloc:
        raise ValueError("source_url must be an absolute HTTPS URL.")

    tier = record.get("evidence_tier")
    if isinstance(tier, bool) or not isinstance(tier, int) or tier not in (1, 2, 3, 4):
        raise ValueError("evidence_tier must be an integer from 1 to 4.")

    amount = record.get("transaction_value")
    if amount is not None:
        if isinstance(amount, bool) or not isinstance(amount, (int, float)) or amount < 0:
            raise ValueError("transaction_value must be a non-negative number or null.")

    normalized = {
        "entity_name": _required_text(record, "entity_name"),
        "target_name": _required_text(record, "target_name"),
        "evidence_type": evidence_type,
        "capital_origin": capital_origin,
        "execution_status": execution_status,
        "verification_status": verification_status,
        "evidence_tier": tier,
        "source_url": source_url,
        "source_name": _optional_text(record, "source_name"),
        "event_at": _timestamp(record.get("event_at"), "event_at"),
        "published_at": _timestamp(record.get("published_at"), "published_at", required=True),
        "retrieved_at": _timestamp(record.get("retrieved_at"), "retrieved_at", required=True),
        "transaction_value": float(amount) if amount is not None else None,
        "currency": _optional_text(record, "currency"),
        "instrument": _optional_text(record, "instrument"),
        "summary": _required_text(record, "summary"),
        "caveats": _optional_text(record, "caveats"),
    }
    # A 13F/ETF/client-fund holding must never be silently represented as manager proprietary capital.
    if normalized["evidence_type"] == "HOLDING_DISCLOSURE" and normalized["capital_origin"] == "UNKNOWN":
        normalized["caveats"] = (
            (normalized["caveats"] + " ") if normalized["caveats"] else ""
        ) + "Beneficial capital owner is not established by this record."
    canonical = json.dumps(normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    normalized["evidence_id"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return normalized


def initialize_registry(database: str | Path) -> None:
    path = Path(database)
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS smart_money_evidence (
                evidence_id TEXT PRIMARY KEY,
                entity_name TEXT NOT NULL,
                target_name TEXT NOT NULL,
                evidence_type TEXT NOT NULL,
                capital_origin TEXT NOT NULL,
                execution_status TEXT NOT NULL,
                verification_status TEXT NOT NULL,
                evidence_tier INTEGER NOT NULL CHECK (evidence_tier BETWEEN 1 AND 4),
                source_url TEXT NOT NULL,
                source_name TEXT,
                event_at TEXT,
                published_at TEXT NOT NULL,
                retrieved_at TEXT NOT NULL,
                transaction_value REAL,
                currency TEXT,
                instrument TEXT,
                summary TEXT NOT NULL,
                caveats TEXT,
                inserted_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS smart_money_entity_published_idx "
            "ON smart_money_evidence(entity_name, published_at DESC)"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS smart_money_target_published_idx "
            "ON smart_money_evidence(target_name, published_at DESC)"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS smart_money_verification_idx "
            "ON smart_money_evidence(verification_status, evidence_tier)"
        )


def add_evidence(database: str | Path, record: dict[str, Any]) -> dict[str, Any]:
    item = normalize_evidence(record)
    initialize_registry(database)
    columns = [
        "evidence_id", "entity_name", "target_name", "evidence_type",
        "capital_origin", "execution_status", "verification_status",
        "evidence_tier", "source_url", "source_name", "event_at",
        "published_at", "retrieved_at", "transaction_value", "currency",
        "instrument", "summary", "caveats",
    ]
    values = [item.get(column) for column in columns]
    inserted_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with sqlite3.connect(database) as connection:
        cursor = connection.execute(
            f"INSERT OR IGNORE INTO smart_money_evidence "
            f"({', '.join(columns)}, inserted_at) VALUES "
            f"({', '.join('?' for _ in range(len(columns) + 1))})",
            values + [inserted_at],
        )
    return {"evidence_id": item["evidence_id"], "inserted": cursor.rowcount == 1}


def list_evidence(
    database: str | Path,
    *,
    entity_name: str | None = None,
    target_name: str | None = None,
    verification_status: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 1000:
        raise ValueError("limit must be between 1 and 1000.")
    path = Path(database)
    if not path.exists():
        return []
    clauses: list[str] = []
    values: list[Any] = []
    for column, value in (
        ("entity_name", entity_name),
        ("target_name", target_name),
        ("verification_status", verification_status.upper() if verification_status else None),
    ):
        if value:
            clauses.append(f"{column} = ?")
            values.append(value)
    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    with sqlite3.connect(path) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            "SELECT * FROM smart_money_evidence" + where +
            " ORDER BY published_at DESC, inserted_at DESC LIMIT ?",
            values + [limit],
        ).fetchall()
    return [dict(row) for row in rows]
