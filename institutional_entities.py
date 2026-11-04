from __future__ import annotations

import hashlib
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


ENTITY_TYPES = {
    "ASSET_MANAGER", "INVESTMENT_FUND", "SOVEREIGN_WEALTH_FUND",
    "PENSION_FUND", "CORPORATION", "SUBSIDIARY", "GOVERNMENT",
    "INDIVIDUAL", "SPV", "UNKNOWN",
}
IDENTIFIER_TYPES = {"CIK", "LEI", "ISIN", "FIGI", "SEDOL", "INTERNAL", "OTHER"}
RELATIONSHIP_TYPES = {
    "MANAGES", "ADVISES", "BENEFICIAL_OWNER_OF", "SUBSIDIARY_OF",
    "GENERAL_PARTNER_OF", "ISSUER_OF", "CONTROLS", "UNKNOWN",
}


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} is required.")
    return value.strip()


def _utc(value: Any, field: str, required: bool = True) -> str | None:
    if value in (None, ""):
        if required:
            raise ValueError(f"{field} is required.")
        return None
    if not isinstance(value, str):
        raise ValueError(f"{field} must be an ISO-8601 timestamp.")
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} must be an ISO-8601 timestamp.") from exc
    if dt.tzinfo is None:
        raise ValueError(f"{field} must include a timezone.")
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds")


def _source(url: Any) -> str:
    value = _text(url, "source_url")
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError("source_url must be an absolute HTTPS URL.")
    return value


def _canonical(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def _stable_id(namespace: str, value: str) -> str:
    return hashlib.sha256(f"{namespace}:{value}".encode()).hexdigest()


def initialize_entity_registry(database: str | Path) -> None:
    path = Path(database)
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as db:
        db.execute("PRAGMA foreign_keys = ON")
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS entities (
                entity_id TEXT PRIMARY KEY,
                legal_name TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                jurisdiction TEXT,
                identifier_type TEXT,
                identifier_value TEXT,
                created_at TEXT NOT NULL,
                UNIQUE(identifier_type, identifier_value)
            );
            CREATE TABLE IF NOT EXISTS entity_aliases (
                alias_id TEXT PRIMARY KEY,
                entity_id TEXT NOT NULL REFERENCES entities(entity_id),
                alias TEXT NOT NULL,
                alias_normalized TEXT NOT NULL,
                source_url TEXT NOT NULL,
                published_at TEXT NOT NULL,
                retrieved_at TEXT NOT NULL,
                UNIQUE(entity_id, alias_normalized, source_url)
            );
            CREATE INDEX IF NOT EXISTS entity_alias_lookup_idx
                ON entity_aliases(alias_normalized);
            CREATE TABLE IF NOT EXISTS entity_relationships (
                relationship_id TEXT PRIMARY KEY,
                subject_entity_id TEXT NOT NULL REFERENCES entities(entity_id),
                relationship_type TEXT NOT NULL,
                object_entity_id TEXT NOT NULL REFERENCES entities(entity_id),
                effective_from TEXT,
                effective_to TEXT,
                verification_status TEXT NOT NULL,
                source_url TEXT NOT NULL,
                published_at TEXT NOT NULL,
                retrieved_at TEXT NOT NULL,
                caveat TEXT,
                CHECK(subject_entity_id <> object_entity_id)
            );
            CREATE INDEX IF NOT EXISTS entity_relationship_subject_idx
                ON entity_relationships(subject_entity_id, relationship_type);
            CREATE INDEX IF NOT EXISTS entity_relationship_object_idx
                ON entity_relationships(object_entity_id, relationship_type);
            """
        )


def register_entity(
    database: str | Path,
    *,
    legal_name: str,
    entity_type: str,
    jurisdiction: str | None = None,
    identifier_type: str | None = None,
    identifier_value: str | None = None,
) -> dict[str, Any]:
    name = _text(legal_name, "legal_name")
    kind = _text(entity_type, "entity_type").upper()
    if kind not in ENTITY_TYPES:
        raise ValueError("Unsupported entity_type.")
    id_type = identifier_type.upper() if identifier_type else None
    id_value = identifier_value.strip() if identifier_value else None
    if bool(id_type) != bool(id_value):
        raise ValueError("identifier_type and identifier_value must be supplied together.")
    if id_type and id_type not in IDENTIFIER_TYPES:
        raise ValueError("Unsupported identifier_type.")
    identity = f"{id_type}:{id_value}" if id_type else f"name:{_canonical(name)}:{(jurisdiction or '').upper()}"
    entity_id = _stable_id("grios-entity-v1", identity)
    initialize_entity_registry(database)
    created = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with sqlite3.connect(database) as db:
        db.execute("PRAGMA foreign_keys = ON")
        existing = db.execute(
            "SELECT entity_id, legal_name, entity_type FROM entities WHERE entity_id = ?",
            (entity_id,),
        ).fetchone()
        if existing:
            if existing[1] != name or existing[2] != kind:
                raise ValueError("Entity identifier collision or conflicting canonical record.")
            return {"entity_id": entity_id, "inserted": False}
        db.execute(
            """INSERT INTO entities
            (entity_id, legal_name, entity_type, jurisdiction, identifier_type,
             identifier_value, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (entity_id, name, kind, jurisdiction, id_type, id_value, created),
        )
    return {"entity_id": entity_id, "inserted": True}


def add_entity_alias(
    database: str | Path,
    *,
    entity_id: str,
    alias: str,
    source_url: str,
    published_at: str,
    retrieved_at: str,
) -> dict[str, Any]:
    label = _text(alias, "alias")
    normalized = _canonical(label)
    if not normalized:
        raise ValueError("alias must contain letters or numbers.")
    source = _source(source_url)
    published = _utc(published_at, "published_at")
    retrieved = _utc(retrieved_at, "retrieved_at")
    alias_id = _stable_id("grios-alias-v1", f"{entity_id}:{normalized}:{source}")
    initialize_entity_registry(database)
    with sqlite3.connect(database) as db:
        db.execute("PRAGMA foreign_keys = ON")
        cursor = db.execute(
            """INSERT OR IGNORE INTO entity_aliases
            (alias_id, entity_id, alias, alias_normalized, source_url,
             published_at, retrieved_at) VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (alias_id, entity_id, label, normalized, source, published, retrieved),
        )
    return {"alias_id": alias_id, "inserted": cursor.rowcount == 1}


def add_entity_relationship(
    database: str | Path,
    *,
    subject_entity_id: str,
    relationship_type: str,
    object_entity_id: str,
    source_url: str,
    published_at: str,
    retrieved_at: str,
    verification_status: str,
    effective_from: str | None = None,
    effective_to: str | None = None,
    caveat: str | None = None,
) -> dict[str, Any]:
    relation = _text(relationship_type, "relationship_type").upper()
    if relation not in RELATIONSHIP_TYPES:
        raise ValueError("Unsupported relationship_type.")
    verification = _text(verification_status, "verification_status").upper()
    if verification not in {
        "VERIFIED", "CORROBORATED", "PARTIALLY_VERIFIED",
        "UNVERIFIED", "DISPUTED", "REJECTED",
    }:
        raise ValueError("Unsupported verification_status.")
    if subject_entity_id == object_entity_id:
        raise ValueError("An entity cannot be related to itself.")
    source = _source(source_url)
    published = _utc(published_at, "published_at")
    retrieved = _utc(retrieved_at, "retrieved_at")
    start = _utc(effective_from, "effective_from", required=False)
    end = _utc(effective_to, "effective_to", required=False)
    if start and end and end < start:
        raise ValueError("effective_to cannot precede effective_from.")
    identity = "|".join((subject_entity_id, relation, object_entity_id, source, published))
    relationship_id = _stable_id("grios-relationship-v1", identity)
    initialize_entity_registry(database)
    with sqlite3.connect(database) as db:
        db.execute("PRAGMA foreign_keys = ON")
        cursor = db.execute(
            """INSERT OR IGNORE INTO entity_relationships
            (relationship_id, subject_entity_id, relationship_type, object_entity_id,
             effective_from, effective_to, verification_status, source_url,
             published_at, retrieved_at, caveat)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (relationship_id, subject_entity_id, relation, object_entity_id,
             start, end, verification, source, published, retrieved, caveat),
        )
    return {"relationship_id": relationship_id, "inserted": cursor.rowcount == 1}


def resolve_entity(database: str | Path, name_or_alias: str) -> dict[str, Any]:
    """Resolve exact normalized canonical names/aliases only; never fuzzy-match."""
    needle = _canonical(_text(name_or_alias, "name_or_alias"))
    if not needle or not Path(database).exists():
        return {"status": "NOT_FOUND", "matches": []}
    with sqlite3.connect(database) as db:
        db.row_factory = sqlite3.Row
        rows = db.execute(
            """SELECT DISTINCT e.entity_id, e.legal_name, e.entity_type,
                      e.jurisdiction, e.identifier_type, e.identifier_value
               FROM entities e
               LEFT JOIN entity_aliases a ON a.entity_id = e.entity_id
               WHERE lower(trim(e.legal_name)) = lower(trim(?))
                  OR a.alias_normalized = ?
               ORDER BY e.legal_name""",
            (name_or_alias.strip(), needle),
        ).fetchall()
    matches = [dict(row) for row in rows]
    status = "NOT_FOUND" if not matches else ("RESOLVED" if len(matches) == 1 else "AMBIGUOUS")
    return {"status": status, "matches": matches}


def list_relationships(
    database: str | Path,
    entity_id: str,
    *,
    relationship_type: str | None = None,
    include_unverified: bool = True,
) -> list[dict[str, Any]]:
    if not Path(database).exists():
        return []
    clauses = ["(subject_entity_id = ? OR object_entity_id = ?)"]
    params: list[Any] = [entity_id, entity_id]
    if relationship_type:
        relation = relationship_type.upper()
        if relation not in RELATIONSHIP_TYPES:
            raise ValueError("Unsupported relationship_type.")
        clauses.append("relationship_type = ?")
        params.append(relation)
    if not include_unverified:
        clauses.append("verification_status IN ('VERIFIED', 'CORROBORATED')")
    with sqlite3.connect(database) as db:
        db.row_factory = sqlite3.Row
        rows = db.execute(
            "SELECT * FROM entity_relationships WHERE " + " AND ".join(clauses) +
            " ORDER BY published_at DESC",
            params,
        ).fetchall()
    return [dict(row) for row in rows]
