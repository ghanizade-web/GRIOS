from institutional_entities import (
    add_entity_alias, add_entity_relationship, list_relationships,
    register_entity, resolve_entity,
)


def register(db, name, identifier):
    return register_entity(
        db, legal_name=name, entity_type="ASSET_MANAGER",
        jurisdiction="US", identifier_type="CIK", identifier_value=identifier,
    )["entity_id"]


def test_cik_identity_is_idempotent(tmp_path):
    db = tmp_path / "entities.sqlite3"
    first = register(db, "Example Asset Management", "0000123456")
    second = register(db, "Example Asset Management", "0000123456")
    assert first == second


def test_alias_resolution_is_exact_and_source_backed(tmp_path):
    db = tmp_path / "entities.sqlite3"
    entity_id = register(db, "Example Asset Management", "0000123456")
    add_entity_alias(
        db, entity_id=entity_id, alias="Example AM",
        source_url="https://www.sec.gov/example",
        published_at="2026-11-01T10:00:00Z",
        retrieved_at="2026-11-02T10:00:00Z",
    )
    assert resolve_entity(db, "Example AM")["status"] == "RESOLVED"
    assert resolve_entity(db, "Example")["status"] == "NOT_FOUND"


def test_ambiguous_alias_is_not_auto_resolved(tmp_path):
    db = tmp_path / "entities.sqlite3"
    a = register(db, "Manager A", "0000000001")
    b = register(db, "Manager B", "0000000002")
    for entity_id in (a, b):
        add_entity_alias(
            db, entity_id=entity_id, alias="The Manager",
            source_url="https://www.sec.gov/example",
            published_at="2026-11-01T10:00:00Z",
            retrieved_at="2026-11-02T10:00:00Z",
        )
    result = resolve_entity(db, "The Manager")
    assert result["status"] == "AMBIGUOUS"
    assert len(result["matches"]) == 2


def test_relationship_requires_verified_provenance_and_is_idempotent(tmp_path):
    db = tmp_path / "entities.sqlite3"
    manager = register(db, "Example Asset Management", "0000000001")
    fund = register_entity(
        db, legal_name="Example Client Fund", entity_type="INVESTMENT_FUND",
        jurisdiction="US", identifier_type="OTHER", identifier_value="FUND-001",
    )["entity_id"]
    args = dict(
        subject_entity_id=manager, relationship_type="ADVISES",
        object_entity_id=fund, source_url="https://www.sec.gov/example",
        published_at="2026-11-01T10:00:00Z",
        retrieved_at="2026-11-02T10:00:00Z",
        verification_status="VERIFIED",
        caveat="Adviser relationship; does not establish proprietary ownership.",
    )
    assert add_entity_relationship(db, **args)["inserted"] is True
    assert add_entity_relationship(db, **args)["inserted"] is False
    rows = list_relationships(db, manager, include_unverified=False)
    assert len(rows) == 1
    assert rows[0]["relationship_type"] == "ADVISES"


def test_rejects_self_relationship_and_invalid_source(tmp_path):
    db = tmp_path / "entities.sqlite3"
    entity_id = register(db, "Example Asset Management", "0000000001")
    try:
        add_entity_relationship(
            db, subject_entity_id=entity_id, relationship_type="CONTROLS",
            object_entity_id=entity_id, source_url="https://www.sec.gov/example",
            published_at="2026-11-01T10:00:00Z",
            retrieved_at="2026-11-02T10:00:00Z",
            verification_status="VERIFIED",
        )
    except ValueError as exc:
        assert "itself" in str(exc)
    else:
        raise AssertionError("Self-relationship must be rejected")
