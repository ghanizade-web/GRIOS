from smart_money_registry import add_evidence, list_evidence, normalize_evidence


def sample(**overrides):
    record = {
        "entity_name": "Large Asset Manager",
        "target_name": "Example Copper Producer",
        "evidence_type": "HOLDING_DISCLOSURE",
        "capital_origin": "UNKNOWN",
        "execution_status": "ANNOUNCED",
        "verification_status": "VERIFIED",
        "evidence_tier": 1,
        "source_url": "https://www.sec.gov/Archives/example",
        "source_name": "SEC filing",
        "event_at": "2026-10-31T12:00:00Z",
        "published_at": "2026-11-01T13:00:00Z",
        "retrieved_at": "2026-11-02T09:00:00Z",
        "transaction_value": None,
        "currency": "USD",
        "instrument": "common stock",
        "summary": "A filing reports shares held by investment funds advised by the manager.",
        "caveats": "Beneficial owner and investment discretion require filing-level review.",
    }
    record.update(overrides)
    return record


def test_holding_disclosure_does_not_claim_proprietary_capital():
    item = normalize_evidence(sample())
    assert item["capital_origin"] == "UNKNOWN"
    assert "not established" in item["caveats"]


def test_add_is_idempotent_and_queryable(tmp_path):
    database = tmp_path / "registry.sqlite3"
    first = add_evidence(database, sample())
    second = add_evidence(database, sample())
    assert first["inserted"] is True
    assert second["inserted"] is False
    rows = list_evidence(database, entity_name="Large Asset Manager")
    assert len(rows) == 1
    assert rows[0]["evidence_type"] == "HOLDING_DISCLOSURE"


def test_rejects_http_source():
    try:
        normalize_evidence(sample(source_url="http://example.com/source"))
    except ValueError as exc:
        assert "HTTPS" in str(exc)
    else:
        raise AssertionError("HTTP source must be rejected")


def test_rejects_naive_timestamp():
    try:
        normalize_evidence(sample(published_at="2026-11-01T13:00:00"))
    except ValueError as exc:
        assert "timezone" in str(exc)
    else:
        raise AssertionError("Naive timestamp must be rejected")


def test_rejects_unsupported_evidence_type():
    try:
        normalize_evidence(sample(evidence_type="RUMOR_ONLY"))
    except ValueError as exc:
        assert "evidence_type" in str(exc)
    else:
        raise AssertionError("Unsupported evidence type must be rejected")


def test_different_evidence_types_are_distinct_records(tmp_path):
    database = tmp_path / "registry.sqlite3"
    purchase = sample(evidence_type="ACTUAL_PURCHASE", execution_status="COMPLETED")
    contract = sample(evidence_type="SUPPLY_CONTRACT", execution_status="SIGNED")
    first = add_evidence(database, purchase)
    second = add_evidence(database, contract)
    assert first["evidence_id"] != second["evidence_id"]
    assert len(list_evidence(database)) == 2
