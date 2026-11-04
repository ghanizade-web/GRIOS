from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


LIFECYCLE_STAGES = {
    "EMERGENCE",
    "ACCELERATION",
    "SCALING",
    "MATURITY",
    "SATURATION_OR_DECLINE",
}
CONFIDENCE_LEVELS = {"LOW", "MEDIUM", "HIGH"}
VERIFICATION_STATUSES = {
    "VERIFIED",
    "CORROBORATED",
    "PARTIALLY_VERIFIED",
    "UNVERIFIED",
    "DISPUTED",
    "REJECTED",
}
SCORE_WEIGHTS = {
    "structural_demand_strength": 20,
    "supply_constraints": 15,
    "technology_commercial_adoption": 15,
    "corporate_capex_commitment": 15,
    "strategic_government_support": 10,
    "verified_capital_allocation": 10,
    "economic_value_capture": 10,
    "evidence_quality_freshness": 5,
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


def _normalize_evidence(items: Any) -> list[dict[str, Any]]:
    if not isinstance(items, list):
        raise ValueError("evidence must be a list.")
    normalized: list[dict[str, Any]] = []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise ValueError(f"evidence[{index}] must be an object.")
        source_url = _required_text(item, "source_url")
        parsed_url = urlparse(source_url)
        if parsed_url.scheme != "https" or not parsed_url.netloc:
            raise ValueError(f"evidence[{index}].source_url must be an absolute HTTPS URL.")
        tier = item.get("evidence_tier")
        if isinstance(tier, bool) or not isinstance(tier, int) or tier not in (1, 2, 3, 4):
            raise ValueError(f"evidence[{index}].evidence_tier must be an integer from 1 to 4.")
        verification = _required_text(item, "verification_status").upper()
        if verification not in VERIFICATION_STATUSES:
            raise ValueError(f"evidence[{index}].verification_status is unsupported.")
        normalized.append({
            "source_url": source_url,
            "source_name": _optional_text(item, "source_name"),
            "evidence_type": _required_text(item, "evidence_type").upper(),
            "evidence_tier": tier,
            "verification_status": verification,
            "published_at": _timestamp(item.get("published_at"), f"evidence[{index}].published_at", required=True),
            "retrieved_at": _timestamp(item.get("retrieved_at"), f"evidence[{index}].retrieved_at", required=True),
            "summary": _required_text(item, "summary"),
        })
    return normalized


def _normalize_scores(value: Any) -> dict[str, float | None]:
    if not isinstance(value, dict):
        raise ValueError("scores must be an object.")
    unknown = set(value) - set(SCORE_WEIGHTS)
    if unknown:
        raise ValueError(f"Unsupported score components: {', '.join(sorted(unknown))}.")
    scores: dict[str, float | None] = {}
    for component in SCORE_WEIGHTS:
        score = value.get(component)
        if score is None:
            scores[component] = None
            continue
        if isinstance(score, bool) or not isinstance(score, (int, float)) or not 0 <= score <= 100:
            raise ValueError(f"scores.{component} must be between 0 and 100 or null.")
        scores[component] = float(score)
    return scores


def _score_classification(score: float | None) -> str:
    if score is None:
        return "NOT_SCORED"
    if score >= 85:
        return "EXCEPTIONAL_STRUCTURAL_TREND"
    if score >= 70:
        return "STRONG_STRUCTURAL_TREND"
    if score >= 55:
        return "DEVELOPING_TREND"
    if score >= 40:
        return "WEAK_OR_UNCERTAIN_TREND"
    return "INSUFFICIENT_STRUCTURAL_EVIDENCE"


def normalize_megatrend(record: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(record, dict):
        raise ValueError("Megatrend record must be an object.")
    lifecycle = _required_text(record, "lifecycle_stage").upper()
    if lifecycle not in LIFECYCLE_STAGES:
        raise ValueError("Unsupported lifecycle_stage.")
    confidence = _required_text(record, "confidence").upper()
    if confidence not in CONFIDENCE_LEVELS:
        raise ValueError("confidence must be LOW, MEDIUM, or HIGH.")

    scores = _normalize_scores(record.get("scores", {}))
    evidence = _normalize_evidence(record.get("evidence", []))
    score_complete = all(value is not None for value in scores.values())
    # No composite score is published without complete component inputs and at least one source record.
    composite = None
    if score_complete and evidence:
        composite = round(
            sum(scores[key] * weight for key, weight in SCORE_WEIGHTS.items()) / 100,
            2,
        )

    normalized = {
        "name": _required_text(record, "name"),
        "sector": _required_text(record, "sector"),
        "subsector": _optional_text(record, "subsector"),
        "geography": _optional_text(record, "geography"),
        "lifecycle_stage": lifecycle,
        "thesis": _required_text(record, "thesis"),
        "demand_drivers": record.get("demand_drivers", []),
        "supply_constraints": record.get("supply_constraints", []),
        "critical_materials": record.get("critical_materials", []),
        "value_chain": record.get("value_chain", []),
        "scores": scores,
        "composite_score": composite,
        "score_classification": _score_classification(composite),
        "score_status": "COMPLETE" if composite is not None else "INCOMPLETE",
        "confidence": confidence,
        "evidence": evidence,
        "disconfirming_evidence": record.get("disconfirming_evidence", []),
        "next_review_at": _timestamp(record.get("next_review_at"), "next_review_at"),
    }
    for field in ("demand_drivers", "supply_constraints", "critical_materials", "value_chain", "disconfirming_evidence"):
        if not isinstance(normalized[field], list) or any(not isinstance(item, str) for item in normalized[field]):
            raise ValueError(f"{field} must be a list of strings.")
        normalized[field] = [item.strip() for item in normalized[field] if item.strip()]

    canonical = json.dumps(normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    normalized["record_id"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return normalized


def initialize_registry(database: str | Path) -> None:
    path = Path(database)
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS megatrend_snapshots (
                record_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                sector TEXT NOT NULL,
                lifecycle_stage TEXT NOT NULL,
                confidence TEXT NOT NULL,
                composite_score REAL,
                score_classification TEXT NOT NULL,
                score_status TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                inserted_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS megatrend_name_inserted_idx "
            "ON megatrend_snapshots(name, inserted_at DESC)"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS megatrend_score_idx "
            "ON megatrend_snapshots(score_classification, composite_score DESC)"
        )


def add_megatrend(database: str | Path, record: dict[str, Any]) -> dict[str, Any]:
    item = normalize_megatrend(record)
    initialize_registry(database)
    inserted_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    payload = json.dumps(item, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    with sqlite3.connect(database) as connection:
        cursor = connection.execute(
            """
            INSERT OR IGNORE INTO megatrend_snapshots (
                record_id, name, sector, lifecycle_stage, confidence,
                composite_score, score_classification, score_status,
                payload_json, inserted_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                item["record_id"], item["name"], item["sector"],
                item["lifecycle_stage"], item["confidence"],
                item["composite_score"], item["score_classification"],
                item["score_status"], payload, inserted_at,
            ),
        )
    return {
        "record_id": item["record_id"],
        "inserted": cursor.rowcount == 1,
        "composite_score": item["composite_score"],
        "score_classification": item["score_classification"],
        "score_status": item["score_status"],
    }


def list_megatrends(
    database: str | Path,
    *,
    name: str | None = None,
    sector: str | None = None,
    score_classification: str | None = None,
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
        ("name", name),
        ("sector", sector),
        ("score_classification", score_classification.upper() if score_classification else None),
    ):
        if value:
            clauses.append(f"{column} = ?")
            values.append(value)
    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    with sqlite3.connect(path) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            "SELECT payload_json, inserted_at FROM megatrend_snapshots" + where +
            " ORDER BY inserted_at DESC LIMIT ?",
            values + [limit],
        ).fetchall()
    result = []
    for row in rows:
        item = json.loads(row["payload_json"])
        item["inserted_at"] = row["inserted_at"]
        result.append(item)
    return result
