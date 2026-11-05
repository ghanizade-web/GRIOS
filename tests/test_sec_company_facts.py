from sec_company_facts import (
    build_company_series,
    extract_report_facts,
    render_persian_report,
    select_latest_period_filing,
)


def submissions_payload():
    return {
        "name": "Example Corporation",
        "filings": {
            "recent": {
                "form": ["10-Q", "8-K", "10-K"],
                "filingDate": ["2026-08-01", "2026-08-10", "2026-03-01"],
                "reportDate": ["2026-06-30", "2026-08-10", "2025-12-31"],
                "accessionNumber": ["0000000001-26-000001", "0000000001-26-000002", "0000000001-26-000003"],
            }
        },
    }


def companyfacts_payload():
    accession = "0000000001-26-000001"
    return {
        "facts": {
            "us-gaap": {
                "RevenueFromContractWithCustomerExcludingAssessedTax": {
                    "units": {
                        "USD": [
                            {"accn": accession, "form": "10-Q", "end": "2026-06-30", "start": "2026-01-01", "filed": "2026-08-01", "val": 1000000000},
                            {"accn": "0000000001-25-000001", "form": "10-Q", "end": "2026-06-30", "start": "2026-01-01", "filed": "2025-08-01", "val": 800000000},
                        ]
                    }
                },
                "Assets": {
                    "units": {
                        "USD": [
                            {"accn": accession, "form": "10-Q", "end": "2026-06-30", "filed": "2026-08-01", "val": 5000000000}
                        ]
                    }
                },
                "EarningsPerShareDiluted": {
                    "units": {
                        "USD/shares": [
                            {"accn": accession, "form": "10-Q", "end": "2026-06-30", "start": "2026-04-01", "filed": "2026-08-01", "val": 2.15}
                        ]
                    }
                },
            }
        }
    }


def test_select_latest_original_period_filing_skips_8k():
    filing = select_latest_period_filing(submissions_payload())
    assert filing["form"] == "10-Q"
    assert filing["report_date"] == "2026-06-30"
    assert filing["accession_number"] == "0000000001-26-000001"


def test_extract_report_facts_matches_exact_accession_and_period():
    filing = select_latest_period_filing(submissions_payload())
    facts = extract_report_facts(companyfacts_payload(), filing)
    assert len(facts) == 3
    revenue = next(item for item in facts if item["metric"] == "revenue")
    assert revenue["value"] == 1000000000
    assert revenue["period_start"] == "2026-01-01"
    assert revenue["period_end"] == "2026-06-30"
    assert not any(item["value"] == 800000000 for item in facts)


def test_build_company_series_preserves_filing_period_and_accession():
    series = build_company_series(
        {"symbol": "EXM", "cik": "1", "name": "Example"},
        submissions_payload(),
        companyfacts_payload(),
        observed_at="2026-08-02T00:00:00+00:00",
    )
    assert series["data_as_of"] == "2026-06-30"
    assert series["extra"]["filing_date"] == "2026-08-01"
    assert series["extra"]["form"] == "10-Q"
    assert "year-to-date" in series["caveat"]


def test_persian_report_discloses_period_and_no_consensus():
    series = build_company_series(
        {"symbol": "EXM", "cik": "1", "name": "Example"},
        submissions_payload(),
        companyfacts_payload(),
        observed_at="2026-08-02T00:00:00+00:00",
    )
    report = render_persian_report(
        [series],
        generated_at="2026-08-02T00:00:00+00:00",
        publish_result={"status": "DIRECT_SUPABASE", "accepted": 1},
    )
    assert "گزارش بنیادی شرکت‌ها" in report
    assert "دوره گزارش" in report
    assert "اجماع تحلیلگران" in report
    assert "https://farcaster.xyz/drghanizade" in report
