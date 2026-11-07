from __future__ import annotations

import argparse
import json
import os
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import httpx

DEFAULT_SUPABASE_URL = "https://ouzayspfyhkhktntonxd.supabase.co"
MAX_AGE_DAYS = 14


def normalize_cftc_rows(rows: Any, today: date | None = None) -> dict[str, Any]:
    today = today or date.today()
    if not isinstance(rows, list):
        rows = []
    by_key: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        key = str(row.get("asset_key", ""))
        if not key.startswith(("cftc:disaggregated_futures_only:", "cftc:tff_futures_only:")):
            continue
        try:
            data_date = date.fromisoformat(str(row.get("data_as_of", ""))[:10])
        except ValueError:
            continue
        age = (today - data_date).days
        if age < 0 or age > MAX_AGE_DAYS:
            continue
        extra = row.get("extra")
        if not isinstance(extra, dict) or not isinstance(extra.get("categories"), dict):
            continue
        categories = extra["categories"]
        valid_categories = {}
        for name, values in categories.items():
            if not isinstance(values, dict):
                continue
            net = _number(values.get("net"))
            weekly = _number(values.get("weekly_net_change"))
            percentile = _number(values.get("historical_percentile"))
            if net is None or weekly is None:
                continue
            valid_categories[name] = {
                "label_fa": str(values.get("label_fa") or name),
                "net": net,
                "weekly_net_change": weekly,
                "historical_percentile": percentile,
                "historical_z_score": _number(values.get("historical_z_score")),
            }
        if not valid_categories:
            continue
        clean = {
            "symbol": str(row.get("symbol") or ""),
            "name": str(row.get("name") or row.get("symbol") or ""),
            "asset_key": key,
            "data_as_of": data_date.isoformat(),
            "report_type": str(extra.get("report_type") or ""),
            "source_url": str(extra.get("source_url") or "https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm"),
            "categories": valid_categories,
        }
        old = by_key.get(key)
        if old is None or clean["data_as_of"] > old["data_as_of"]:
            by_key[key] = clean
    items = sorted(by_key.values(), key=lambda item: (item["report_type"], item["symbol"]))
    status = "FULL" if len(items) >= 6 else "PARTIAL" if items else "UNAVAILABLE"
    return {
        "schema_version": 1,
        "status": status,
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "items": items,
        "source": "CFTC Commitments of Traders — Futures Only",
        "caveat": "Weekly futures-only positioning; not real-time flow, not options positioning, and not a complete view of fund portfolios.",
    }


def _number(value: Any) -> float | None:
    try:
        number = float(value)
        return number if number == number and abs(number) != float("inf") else None
    except (TypeError, ValueError):
        return None


def fetch_cftc_context(
    supabase_url: str | None = None,
    service_role_key: str | None = None,
    client: Any = httpx,
) -> dict[str, Any]:
    url = (supabase_url or os.getenv("SUPABASE_URL") or DEFAULT_SUPABASE_URL).rstrip("/")
    key = (service_role_key or os.getenv("SUPABASE_SERVICE_ROLE_KEY") or "").strip()
    if not key:
        return {"schema_version": 1, "status": "UNAVAILABLE", "retrieved_at": datetime.now(timezone.utc).isoformat(), "items": [], "error_type": "MissingServiceRoleConfiguration"}
    response = client.get(
        f"{url}/rest/v1/grios_market_observations",
        params={
            "select": "symbol,name,asset_key,data_as_of,extra",
            "asset_class": "eq.futures_positioning",
            "provider": "eq.CFTC",
            "order": "data_as_of.desc,observed_at.desc",
            "limit": "40",
        },
        headers={"apikey": key, "Authorization": f"Bearer {key}", "Accept": "application/json"},
        timeout=15.0,
    )
    response.raise_for_status()
    payload = normalize_cftc_rows(response.json())
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Load the latest verified CFTC futures-only positioning from GRIOS Supabase")
    parser.add_argument("--output-json", default="reports/cftc-positioning-latest.json")
    args = parser.parse_args()
    try:
        payload = fetch_cftc_context()
    except Exception as exc:
        payload = {"schema_version": 1, "status": "UNAVAILABLE", "retrieved_at": datetime.now(timezone.utc).isoformat(), "items": [], "error_type": type(exc).__name__}
    path = Path(args.output_json)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"CFTC_CONTEXT_STATUS={payload['status']}")
    print(f"CFTC_CONTEXT_CONTRACTS={len(payload.get('items', []))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
