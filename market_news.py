from __future__ import annotations

import argparse
import html
import json
import re
import time
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx

USER_AGENT = "GRIOS Research Intelligence/15.0 (https://github.com/ghanizade-web/GRIOS)"
WINDOW_HOURS = 72
MAX_ITEMS = 80

# Tier 1: primary official sources. Tier 2: established financial journalism.
FEEDS: tuple[dict[str, str], ...] = (
    {"name": "Federal Reserve — Monetary Policy", "url": "https://www.federalreserve.gov/feeds/press_monetary.xml", "tier": "TIER_1", "kind": "official", "focus": "macro"},
    {"name": "SEC — Press Releases", "url": "https://www.sec.gov/news/pressreleases.rss", "tier": "TIER_1", "kind": "official", "focus": "regulation"},
    {"name": "EIA — Today in Energy", "url": "https://www.eia.gov/rss/todayinenergy.xml", "tier": "TIER_1", "kind": "official", "focus": "energy"},
    {"name": "BIS — Media Releases", "url": "https://www.bis.org/doclist/all_pressrels.rss", "tier": "TIER_1", "kind": "official", "focus": "macro"},
    # BLS feed URLs are linked directly from the agency's official RSS directory.
    {"name": "BLS — Employment Situation", "url": "https://www.bls.gov/feed/empsit.rss", "tier": "TIER_1", "kind": "official", "focus": "labor"},
    {"name": "BLS — Consumer Price Index", "url": "https://www.bls.gov/feed/cpi.rss", "tier": "TIER_1", "kind": "official", "focus": "inflation"},
    {"name": "BLS — Producer Price Index", "url": "https://www.bls.gov/feed/ppi.rss", "tier": "TIER_1", "kind": "official", "focus": "inflation"},
    {"name": "BLS — Job Openings and Labor Turnover Survey", "url": "https://www.bls.gov/feed/jolts.rss", "tier": "TIER_1", "kind": "official", "focus": "labor"},
    {"name": "Bloomberg — Markets", "url": "https://feeds.bloomberg.com/markets/news.rss", "tier": "TIER_2", "kind": "news", "focus": "markets"},
    {"name": "Bloomberg — Technology", "url": "https://feeds.bloomberg.com/technology/news.rss", "tier": "TIER_2", "kind": "news", "focus": "technology"},
    {"name": "CNBC — Investing", "url": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=15839069", "tier": "TIER_2", "kind": "news", "focus": "markets"},
    {"name": "Wall Street Journal — Markets", "url": "https://feeds.content.dowjones.io/public/rss/RSSMarketsMain", "tier": "TIER_2", "kind": "news", "focus": "markets"},
    {"name": "Financial Times — Global", "url": "https://www.ft.com/rss/home", "tier": "TIER_2", "kind": "news", "focus": "global"},
    {"name": "Reuters — Markets (Google News index)", "url": "https://news.google.com/rss/search?q=when:3d+site:reuters.com/markets&hl=en-US&gl=US&ceid=US:en", "tier": "TIER_2", "kind": "news_index", "focus": "markets"},
    {"name": "Reuters — Technology (Google News index)", "url": "https://news.google.com/rss/search?q=when:3d+site:reuters.com/technology&hl=en-US&gl=US&ceid=US:en", "tier": "TIER_2", "kind": "news_index", "focus": "technology"},
    {"name": "Reuters — World (Google News index)", "url": "https://news.google.com/rss/search?q=when:3d+site:reuters.com/world&hl=en-US&gl=US&ceid=US:en", "tier": "TIER_2", "kind": "news_index", "focus": "geopolitics"},
    {"name": "Associated Press — Business (Google News index)", "url": "https://news.google.com/rss/search?q=when:3d+site:apnews.com/hub/business&hl=en-US&gl=US&ceid=US:en", "tier": "TIER_2", "kind": "news_index", "focus": "markets"},
    {"name": "Bloomberg — Crypto", "url": "https://feeds.bloomberg.com/crypto/news.rss", "tier": "TIER_2", "kind": "news", "focus": "crypto"},
    {"name": "Reuters — Crypto (Google News index)", "url": "https://news.google.com/rss/search?q=when:3d+site:reuters.com+bitcoin+OR+cryptocurrency&hl=en-US&gl=US&ceid=US:en", "tier": "TIER_2", "kind": "news_index", "focus": "crypto"},
    {"name": "The Block — Digital Assets", "url": "https://www.theblock.co/rss.xml", "tier": "TIER_3", "kind": "specialist", "focus": "crypto"},
    {"name": "CoinDesk — Digital Assets", "url": "https://www.coindesk.com/arc/outboundfeeds/rss/", "tier": "TIER_3", "kind": "specialist", "focus": "crypto"},
)

TOPIC_RULES: dict[str, tuple[str, ...]] = {
    "geopolitics": ("iran", "israel", "ukraine", "war ", "warfare", "sanction", "strait of hormuz", "red sea", "middle east", "taiwan", "tariff", "trade war", "election", "export control", "beijing", "opec+"),
    "monetary_policy": ("federal reserve", "fomc", "fed rate", "interest rate", "ecb", "boj", "boe", "rba", "central bank", "treasury yield", "treasury yields", "bond yield", "bond yields", "inflation", "consumer price", "cpi", "pce", "payroll", "jobs report"),
    "ai_semiconductors": ("artificial intelligence", " ai ", "semiconductor", "chipmaker", "chip demand", "tsmc", "data center", "datacenter", "hyperscaler", "cloud capex", "gpu", "advanced packaging"),
    "energy": ("crude oil", "oil price", " oil ", "brent", "wti", "natural gas", "lng", "petroleum", "eia", "opec", "refinery", "pipeline", "electricity", "power grid", "uranium"),
    "metals": ("precious metals", "metals", "gold", "silver", "copper", "aluminium", "aluminum", "lithium", "nickel", "critical minerals", "iron ore"),
    "crypto": ("bitcoin", "ethereum", "crypto", "digital asset", "stablecoin", "tokenization", "spot etf", "blockchain"),
    "fx": ("dollar", "euro", "yen", "sterling", "pound", "forex", "currency", "exchange rate"),
    "corporate_earnings": ("earnings", "quarterly results", "revenue", "profit", "guidance", "buyback", "dividend", "merger", "acquisition", "ipo", "shares fell", "shares rose"),
    "global_growth": ("recession", "gdp", "manufacturing", "pmi", "retail sales", "consumer spending", "china economy", "industrial production", "trade data", "employment situation", "job openings", "jolts", "unemployment", "nonfarm payroll", "labor force", "wage growth", "jobless claims"),
    "regulation": ("sec", "regulator", "regulation", "antitrust", "lawsuit", "court ruling", "congress", "legislation", "compliance"),
    "politics": ("election", "midterm", "president", "presidential", "white house", "government", "parliament", "fiscal policy", "federal budget", "government shutdown", "tax policy", "congressional", "political party"),
}


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].split(":")[-1].lower()


def _child_text(node: ET.Element, names: set[str]) -> str:
    for child in node.iter():
        if child is node:
            continue
        if _local(child.tag) in names and child.text:
            return html.unescape(re.sub(r"<[^>]+>", " ", child.text)).strip()
    return ""


def _entry_link(node: ET.Element) -> str:
    for child in list(node):
        if _local(child.tag) == "link":
            href = child.attrib.get("href")
            if href:
                return href.strip()
            if child.text:
                return child.text.strip()
    return ""


def _parse_time(value: str) -> datetime | None:
    if not value:
        return None
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError, OverflowError):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except (TypeError, ValueError):
            return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def classify_topics(title: str, summary: str = "", min_matches: int = 1) -> list[str]:
    text = f" {title} {summary} ".lower()
    def matches(term: str) -> bool:
        pattern = r"(?<![a-z0-9])" + re.escape(term.strip().lower()) + r"(?![a-z0-9])"
        return re.search(pattern, text) is not None
    output = []
    market_link_terms = (
        "oil", "gas", "energy", "sanction", "shipping", "strait", "trade", "tariff", "export",
        "supply", "port", "pipeline", "nuclear", "currency", "market", "economy", "economic",
        "company", "deal", "robotics", "semiconductor", "chip", "supply chain", "war",
    )
    for topic, terms in TOPIC_RULES.items():
        count = sum(1 for term in terms if matches(term))
        if count < min_matches:
            continue
        if topic == "geopolitics" and not any(matches(term) for term in market_link_terms):
            continue
        output.append(topic)
    return output


def _publisher(node: ET.Element, feed: dict[str, str]) -> tuple[str, str]:
    for child in list(node):
        if _local(child.tag) == "source":
            name = (child.text or "").strip()
            source_url = child.attrib.get("url", "")
            domain = urlparse(source_url).netloc.lower().removeprefix("www.") if source_url else ""
            if name:
                return name, domain
    domain = urlparse(feed["url"]).netloc.lower().removeprefix("www.")
    return feed["name"], domain


def _parse_feed(xml_text: str, feed: dict[str, str], now: datetime) -> list[dict[str, Any]]:
    root = ET.fromstring(xml_text)
    entries = [node for node in root.iter() if _local(node.tag) in {"item", "entry"}]
    cutoff = now - timedelta(hours=WINDOW_HOURS)
    output: list[dict[str, Any]] = []
    for node in entries:
        title = _child_text(node, {"title"})
        link = _entry_link(node)
        summary = _child_text(node, {"description", "summary", "encoded", "content"})
        raw_date = _child_text(node, {"pubdate", "published", "updated", "date"})
        published = _parse_time(raw_date)
        if not title or not link or not published or published < cutoff or published > now + timedelta(hours=6):
            continue
        if title.strip().lower().startswith("transcript") or len(title.strip()) < 24:
            continue
        publisher, domain = _publisher(node, feed)
        topics = list(dict.fromkeys(classify_topics(title) + classify_topics(summary, min_matches=2)))
        if not topics:
            focus = feed.get("focus", "")
            focus_topics = {"crypto": "crypto", "energy": "energy", "regulation": "regulation", "labor": "global_growth", "inflation": "monetary_policy"}
            if focus in focus_topics or feed.get("kind") == "specialist":
                mapped = focus_topics.get(focus, focus)
                topics = [mapped] if mapped in TOPIC_RULES else []
        if not topics:
            continue
        output.append({
            "title": re.sub(r"\s+", " ", title).strip(),
            "summary": re.sub(r"\s+", " ", summary).strip()[:900],
            "url": link,
            "publisher": publisher or feed["name"],
            "domain": domain,
            "published_at": published.isoformat(),
            "evidence_tier": feed["tier"],
            "source_type": feed["kind"],
            "topics": topics,
            "feed": feed["name"],
        })
    return output


def _fetch_one(feed: dict[str, str], now: datetime) -> tuple[str, list[dict[str, Any]], str | None]:
    try:
        response = httpx.get(feed["url"], headers={"User-Agent": USER_AGENT, "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml"}, timeout=12.0, follow_redirects=True)
        response.raise_for_status()
        items = _parse_feed(response.text, feed, now)
        return feed["name"], items, None
    except Exception as exc:
        return feed["name"], [], type(exc).__name__


def collect_news(now: datetime | None = None, feeds: tuple[dict[str, str], ...] = FEEDS) -> dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    now = now.astimezone(timezone.utc)
    collected: list[dict[str, Any]] = []
    feed_health: list[dict[str, str]] = []
    with ThreadPoolExecutor(max_workers=min(8, len(feeds) or 1)) as pool:
        futures = [pool.submit(_fetch_one, feed, now) for feed in feeds]
        for future in as_completed(futures):
            name, items, error = future.result()
            feed_health.append({"feed": name, "status": "OK" if error is None else "ERROR", **({"error_type": error} if error else {})})
            collected.extend(items)
    unique: dict[str, dict[str, Any]] = {}
    for item in collected:
        key = re.sub(r"[^a-z0-9]+", "", item["title"].lower())
        if not key:
            continue
        current = unique.get(key)
        if current is None or (item["evidence_tier"], item["published_at"]) < (current["evidence_tier"], current["published_at"]):
            unique[key] = item
    items = list(unique.values())
    tier_rank = {"TIER_1": 0, "TIER_2": 1, "TIER_3": 2}
    items.sort(key=lambda x: (tier_rank.get(x["evidence_tier"], 9), -datetime.fromisoformat(x["published_at"]).timestamp()))
    items = items[:MAX_ITEMS]
    domains = {x["domain"] for x in items if x.get("domain")}
    official = any(x["evidence_tier"] == "TIER_1" for x in items)
    status = "FULL" if len(items) >= 8 and len(domains) >= 4 and official else "PARTIAL" if items else "UNAVAILABLE"
    return {
        "schema_version": 1,
        "status": status,
        "retrieved_at": now.isoformat(),
        "window_hours": WINDOW_HOURS,
        "items": items,
        "feed_health": sorted(feed_health, key=lambda x: x["feed"]),
        "coverage": {"unique_items": len(items), "independent_domains": len(domains), "official_source_present": official},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect source-attributed GRIOS market news")
    parser.add_argument("--output-json", default="reports/news-intelligence-latest.json")
    args = parser.parse_args()
    started = time.monotonic()
    try:
        payload = collect_news()
    except Exception as exc:
        payload = {"schema_version": 1, "status": "UNAVAILABLE", "retrieved_at": datetime.now(timezone.utc).isoformat(), "items": [], "feed_health": [], "error_type": type(exc).__name__}
    path = Path(args.output_json)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"NEWS_INTELLIGENCE_STATUS={payload['status']}")
    print(f"NEWS_INTELLIGENCE_ITEMS={len(payload.get('items', []))}")
    print(f"NEWS_INTELLIGENCE_ELAPSED_SECONDS={time.monotonic() - started:.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
