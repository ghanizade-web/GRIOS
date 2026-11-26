from __future__ import annotations
import json
from datetime import datetime, timezone
from scripts.build_daily_outputs import build_capital_flows_report, build_trading_brief, validate_candidate

def candidate(**changes):
    item={"instrument":"BTC/USD","asset_class":"crypto","direction":"WATCH","price":90000,"price_type":"spot","provider":"test","timestamp":datetime.now(timezone.utc).isoformat(),"catalyst":"Official protocol event","catalyst_date":"2026-11-26","transmission":"Changes supply expectations","trigger":"Wait for confirmed daily close","invalidation":"Event cancellation","horizon":"1-5 sessions","risk":"high","evidence_grade":"B","sources":["https://example.com/source"]}
    return {**item,**changes}

def test_candidate_contract_rejects_equities_and_weak_directional_claims():
    assert validate_candidate(candidate())==(True,"valid")
    assert validate_candidate(candidate(asset_class="equity"))[1]=="ineligible_asset_class"
    assert validate_candidate(candidate(evidence_grade="C",direction="LONG"))[1]=="grade_c_must_be_watch"
    assert validate_candidate(candidate(sources=["http://example.com"))[1]=="sources_must_be_https"

def test_trading_brief_fails_closed_without_validated_candidate_file(tmp_path):
    report,audit=build_trading_brief(tmp_path/"missing.json","2026-11-26")
    assert "No confirmed trade; monitor only." in report
    assert audit["accepted_count"]==0
    assert audit["status"]=="NO_CONFIRMED_TRADE"

def test_capital_flow_report_is_honest_when_no_sources_exist(tmp_path):
    report,evidence=build_capital_flows_report(tmp_path/"missing.json",tmp_path/"no-13f","2026-11-26",now=datetime(2026,11,26,tzinfo=timezone.utc))
    assert "No SEC 13F watchlist snapshot" in report
    assert "quarterly, delayed holdings snapshots" in report
    assert "This is not proof that no activity occurred." in report
    assert evidence["sec_13f_reports"]==[]

def test_capital_flow_report_filters_stale_items_and_labels_reported_claims(tmp_path):
    now=datetime(2026,11,26,tzinfo=timezone.utc); news=tmp_path/"news.json"
    news.write_text(json.dumps({"status":"FULL","retrieved_at":now.isoformat(),"window_hours":72,"items":[
      {"title":"Copper mine expansion receives a new offtake agreement","summary":"Long-term supply agreement for copper concentrate.","url":"https://example.com/copper","publisher":"Example","published_at":now.isoformat(),"evidence_tier":"TIER_2"},
      {"title":"Old lithium mine expansion","summary":"Historical announcement.","url":"https://example.com/old","publisher":"Example","published_at":"2026-11-20T00:00:00+00:00","evidence_tier":"TIER_2"}]}),encoding="utf-8")
    report,evidence=build_capital_flows_report(news,tmp_path/"none","2026-11-26",now=now)
    assert "Copper mine expansion" in report
    assert "execution not independently established" in report
    assert "Old lithium mine expansion" not in report
    assert len(evidence["selected_news"])==1

def test_13f_is_reported_as_holdings_snapshot_not_recent_buy(tmp_path):
    d=tmp_path/"13f"; d.mkdir()
    (d/"manager.json").write_text(json.dumps({"filer_name":"Example Manager","report_period":"2026-09-30","latest_filed_at":"2026-11-14","holdings_count":10,"holdings":[{"issuer":"Example Issuer","value_usd":123456}],"applied_filings":[{"source_url":"https://www.sec.gov/Archives/edgar/data/example"}]}),encoding="utf-8")
    report,evidence=build_capital_flows_report(tmp_path/"missing-news.json",d,"2026-11-26",now=datetime(2026,11,26,tzinfo=timezone.utc))
    assert "Example Manager" in report
    assert "Top disclosed position" in report
    assert "do not identify trade dates" in report
    assert evidence["sec_13f_reports"][0]["source_urls"]==["https://www.sec.gov/Archives/edgar/data/example"]
