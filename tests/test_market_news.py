from __future__ import annotations

from datetime import datetime, timedelta, timezone

import market_news


def test_parse_feed_extracts_source_date_topics_and_link():
    now = datetime.now(timezone.utc)
    published = (now - timedelta(hours=2)).strftime("%a, %d %b %Y %H:%M:%S GMT")
    xml = f"""<?xml version='1.0'?>
    <rss version='2.0'><channel><item>
      <title>Federal Reserve signals rate outlook as inflation cools</title>
      <link>https://example.com/story</link>
      <description>Policy makers discuss interest rates and inflation.</description>
      <pubDate>{published}</pubDate>
      <source url='https://www.federalreserve.gov/'>Federal Reserve</source>
    </item></channel></rss>"""
    feed = {"name": "Test Fed", "url": "https://example.com/feed", "tier": "TIER_1", "kind": "official", "focus": "macro"}
    items = market_news._parse_feed(xml, feed, now)
    assert len(items) == 1
    assert items[0]["publisher"] == "Federal Reserve"
    assert items[0]["domain"] == "federalreserve.gov"
    assert "monetary_policy" in items[0]["topics"]
    assert items[0]["url"] == "https://example.com/story"


def test_old_and_undated_news_are_rejected():
    now = datetime.now(timezone.utc)
    old = (now - timedelta(days=8)).strftime("%a, %d %b %Y %H:%M:%S GMT")
    xml = f"""<rss><channel>
    <item><title>Old oil market story</title><link>https://example.com/old</link><pubDate>{old}</pubDate></item>
    <item><title>Undated bitcoin story</title><link>https://example.com/none</link></item>
    </channel></rss>"""
    feed = {"name": "Test", "url": "https://example.com/feed", "tier": "TIER_2", "kind": "news", "focus": "markets"}
    assert market_news._parse_feed(xml, feed, now) == []


def test_topic_classifier_detects_multiple_cross_asset_channels():
    topics = market_news.classify_topics("Iran tensions lift oil as Treasury yields rise and bitcoin weakens")
    assert "geopolitics" in topics
    assert "energy" in topics
    assert "monetary_policy" in topics
    assert "crypto" in topics


def test_collect_news_deduplicates_and_preserves_official_source(monkeypatch):
    now = datetime.now(timezone.utc)
    item = {"title": "Fed policy outlook", "summary": "", "url": "https://federalreserve.gov/a", "publisher": "Federal Reserve", "domain": "federalreserve.gov", "published_at": now.isoformat(), "evidence_tier": "TIER_1", "source_type": "official", "topics": ["monetary_policy"], "feed": "Fed"}
    def fake_fetch(feed, current):
        return feed["name"], [item], None
    monkeypatch.setattr(market_news, "_fetch_one", fake_fetch)
    feeds = (
        {"name": "Fed A", "url": "https://a", "tier": "TIER_1", "kind": "official", "focus": "macro"},
        {"name": "Fed B", "url": "https://b", "tier": "TIER_1", "kind": "official", "focus": "macro"},
    )
    result = market_news.collect_news(now=now, feeds=feeds)
    assert result["status"] == "PARTIAL"
    assert len(result["items"]) == 1
    assert result["coverage"]["official_source_present"] is True


def test_topic_classifier_avoids_substring_false_positives():
    topics = market_news.classify_topics("Goldman Sachs discusses corporate strategy")
    assert "metals" not in topics
    assert "energy" not in topics


def test_classifier_rejects_geopolitical_headlines_without_market_transmission():
    assert "geopolitics" not in market_news.classify_topics("Iran executes militant after attack on police station")


def test_classifier_recognizes_precious_metals_and_multi_asset_summary():
    topics = market_news.classify_topics("Precious Metals Post Weekly Gains")
    assert "metals" in topics



def test_official_bls_macro_feeds_are_registered_and_classified():
    names = {feed["name"] for feed in market_news.FEEDS}
    assert "BLS — Employment Situation" in names
    assert "BLS — Consumer Price Index" in names
    assert "BLS — Producer Price Index" in names
    assert "BLS — Job Openings and Labor Turnover Survey" in names

    now = datetime.now(timezone.utc)
    published = (now - timedelta(hours=1)).strftime("%a, %d %b %Y %H:%M:%S GMT")
    xml = f"""<rss><channel><item>
      <title>Employment Situation Summary</title>
      <link>https://www.bls.gov/news.release/empsit.htm</link>
      <description>Monthly labor market release.</description>
      <pubDate>{published}</pubDate>
    </item></channel></rss>"""
    feed = {"name": "BLS — Employment Situation", "url": "https://www.bls.gov/feed/empsit.rss", "tier": "TIER_1", "kind": "official", "focus": "labor"}
    items = market_news._parse_feed(xml, feed, now)
    assert len(items) == 1
    assert "global_growth" in items[0]["topics"]
