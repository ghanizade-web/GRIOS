from megatrend_registry import (
    SCORE_WEIGHTS,
    add_megatrend,
    list_megatrends,
    normalize_megatrend,
)


def sample(**overrides):
    record = {
        "name": "AI Infrastructure & Power",
        "sector": "Technology and Energy",
        "subsector": "Data centers and grid equipment",
        "geography": "United States",
        "lifecycle_stage": "ACCELERATION",
        "thesis": "Data-center expansion is increasing demand for reliable power and grid equipment.",
        "demand_drivers": ["AI compute demand", "Cloud infrastructure"],
        "supply_constraints": ["Transformer lead times", "Grid interconnection queues"],
        "critical_materials": ["Copper"],
        "value_chain": ["Semiconductors", "Data centers", "Power generation", "Grid equipment"],
        "scores": {
            "structural_demand_strength": 80,
            "supply_constraints": 70,
            "technology_commercial_adoption": 75,
            "corporate_capex_commitment": 80,
            "strategic_government_support": 60,
            "verified_capital_allocation": 65,
            "economic_value_capture": 70,
            "evidence_quality_freshness": 90,
        },
        "confidence": "MEDIUM",
        "evidence": [{
            "source_url": "https://www.sec.gov/Archives/example",
            "source_name": "SEC filing",
            "evidence_type": "CORPORATE_CAPEX",
            "evidence_tier": 1,
            "verification_status": "VERIFIED",
            "published_at": "2026-11-01T13:00:00Z",
            "retrieved_at": "2026-11-02T09:00:00Z",
            "summary": "Issuer filing describes planned data-center infrastructure investment.",
        }],
        "disconfirming_evidence": ["Project delays could reduce near-term equipment demand."],
        "next_review_at": "2026-12-01T00:00:00Z",
    }
    record.update(overrides)
    return record


def test_score_weights_sum_to_100():
    assert sum(SCORE_WEIGHTS.values()) == 100


def test_complete_record_gets_weighted_score_and_classification():
    item = normalize_megatrend(sample())
    expected = sum(
        item["scores"][key] * weight
        for key, weight in SCORE_WEIGHTS.items()
    ) / 100
    assert item["composite_score"] == round(expected, 2)
    assert item["score_status"] == "COMPLETE"
    assert item["score_classification"] == "STRONG_STRUCTURAL_TREND"


def test_missing_component_does_not_receive_neutral_score():
    scores = sample()["scores"]
    scores["verified_capital_allocation"] = None
    item = normalize_megatrend(sample(scores=scores))
    assert item["composite_score"] is None
    assert item["score_status"] == "INCOMPLETE"
    assert item["score_classification"] == "NOT_SCORED"


def test_no_evidence_prevents_composite_score():
    item = normalize_megatrend(sample(evidence=[]))
    assert item["composite_score"] is None
    assert item["score_status"] == "INCOMPLETE"


def test_registry_is_append_only_and_idempotent(tmp_path):
    database = tmp_path / "megatrends.sqlite3"
    first = add_megatrend(database, sample())
    second = add_megatrend(database, sample())
    assert first["inserted"] is True
    assert second["inserted"] is False
    rows = list_megatrends(database, sector="Technology and Energy")
    assert len(rows) == 1
    assert rows[0]["name"] == "AI Infrastructure & Power"


def test_new_evidence_creates_new_historical_snapshot(tmp_path):
    database = tmp_path / "megatrends.sqlite3"
    first = add_megatrend(database, sample())
    changed = sample()
    changed["evidence"] = changed["evidence"] + [{
        "source_url": "https://www.energy.gov/example",
        "source_name": "Department of Energy",
        "evidence_type": "GOVERNMENT_POLICY",
        "evidence_tier": 1,
        "verification_status": "VERIFIED",
        "published_at": "2026-11-03T13:00:00Z",
        "retrieved_at": "2026-11-04T09:00:00Z",
        "summary": "Official program supports grid infrastructure modernization.",
    }]
    second = add_megatrend(database, changed)
    assert first["record_id"] != second["record_id"]
    assert len(list_megatrends(database)) == 2


def test_rejects_non_https_evidence_source():
    try:
        normalize_megatrend(sample(evidence=[{
            "source_url": "http://example.com/source",
            "evidence_type": "REPORT",
            "evidence_tier": 2,
            "verification_status": "CORROBORATED",
            "published_at": "2026-11-01T13:00:00Z",
            "retrieved_at": "2026-11-02T09:00:00Z",
            "summary": "Independent industry report.",
        }]))
    except ValueError as exc:
        assert "HTTPS" in str(exc)
    else:
        raise AssertionError("HTTP source must be rejected")


def test_rejects_naive_evidence_timestamp():
    evidence = sample()["evidence"]
    evidence[0]["published_at"] = "2026-11-01T13:00:00"
    try:
        normalize_megatrend(sample(evidence=evidence))
    except ValueError as exc:
        assert "timezone" in str(exc)
    else:
        raise AssertionError("Naive timestamp must be rejected")


def test_rejects_out_of_range_score():
    scores = sample()["scores"]
    scores["structural_demand_strength"] = 101
    try:
        normalize_megatrend(sample(scores=scores))
    except ValueError as exc:
        assert "between 0 and 100" in str(exc)
    else:
        raise AssertionError("Out-of-range score must be rejected")
