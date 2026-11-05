from __future__ import annotations

import argparse
import json
import math
import os
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from data_coverage import publish_market_series

API_ROOT = "https://publicreporting.cftc.gov/resource"
LEGACY_FUTURES_ONLY_DATASET = "6dca-aqww"
USER_AGENT = "GRIOS-Research/15.0 (CFTC public data ingestion)"
FIELDS = (
    "id,market_and_exchange_names,report_date_as_yyyy_mm_dd,"
    "cftc_contract_market_code,open_interest_all,"
    "noncomm_positions_long_all,noncomm_positions_short_all,"
    "comm_positions_long_all,comm_positions_short_all"
)


def _number(value: Any, field: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid numeric CFTC field: {field}") from exc
    if not math.isfinite(number) or number < 0:
        raise ValueError(f"Invalid numeric CFTC field: {field}")
    return number


def normalize_rows(rows: Any, *, contract_code: str, market_label: str) -> list[dict[str, Any]]:
    if not isinstance(rows, list):
        raise ValueError("CFTC response must be a JSON array.")
    normalized: list[dict[str, Any]] = []
    seen_dates: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("CFTC row must be an object.")
        code = str(row.get("cftc_contract_market_code") or "").strip()
        if code != contract_code:
            raise ValueError("CFTC response contains a different contract market code.")
        report_date = str(row.get("report_date_as_yyyy_mm_dd") or "")[:10]
        try:
            datetime.strptime(report_date, "%Y-%m-%d")
        except ValueError as exc:
            raise ValueError("CFTC row has an invalid report date.") from exc
        if report_date in seen_dates:
            continue
        seen_dates.add(report_date)
        noncomm_long = _number(row.get("noncomm_positions_long_all"), "noncomm_positions_long_all")
        noncomm_short = _number(row.get("noncomm_positions_short_all"), "noncomm_positions_short_all")
        comm_long = _number(row.get("comm_positions_long_all"), "comm_positions_long_all")
        comm_short = _number(row.get("comm_positions_short_all"), "comm_positions_short_all")
        open_interest = _number(row.get("open_interest_all"), "open_interest_all")
        normalized.append({
            "report_date": report_date,
            "market": str(row.get("market_and_exchange_names") or market_label),
            "contract_market_code": code,
            "open_interest": open_interest,
            "noncommercial_long": noncomm_long,
            "noncommercial_short": noncomm_short,
            "noncommercial_net": noncomm_long - noncomm_short,
            "commercial_long": comm_long,
            "commercial_short": comm_short,
            "commercial_net": comm_long - comm_short,
        })
    return sorted(normalized, key=lambda item: item["report_date"])


def positioning_stats(values: list[float]) -> dict[str, float | None]:
    if not values:
        return {"percentile": None, "z_score": None}
    current = values[-1]
    percentile = 100.0 * sum(value <= current for value in values) / len(values)
    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values) / len(values)
    stddev = math.sqrt(variance)
    z_score = (current - mean) / stddev if stddev else 0.0
    return {"percentile": round(percentile, 2), "z_score": round(z_score, 4)}


def fetch_contract(
    contract: dict[str, str],
    *,
    limit: int = 260,
    timeout: int = 30,
) -> list[dict[str, Any]]:
    code = str(contract.get("contract_market_code", "")).strip()
    label = str(contract.get("market", "")).strip()
    if not code or not code.isalnum() or len(code) > 12 or not label:
        raise ValueError("Each CFTC watchlist item requires a market label and alphanumeric contract_market_code.")
    if not 2 <= limit <= 520:
        raise ValueError("CFTC history limit must be between 2 and 520 weekly observations.")
    query = {
        "$select": FIELDS,
        "$where": f"cftc_contract_market_code='{code}'",
        "$order": "report_date_as_yyyy_mm_dd DESC",
        "$limit": str(limit),
    }
    url = f"{API_ROOT}/{LEGACY_FUTURES_ONLY_DATASET}.json?{urllib.parse.urlencode(query)}"
    request = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
    rows = normalize_rows(payload, contract_code=code, market_label=label)
    if not rows:
        raise ValueError(f"No CFTC Legacy Futures Only observations returned for {label} ({code}).")
    return rows


def build_market_series(contract: dict[str, str], rows: list[dict[str, Any]]) -> dict[str, Any]:
    latest = rows[-1]
    previous = rows[-2] if len(rows) > 1 else None
    noncomm_values = [item["noncommercial_net"] for item in rows]
    comm_values = [item["commercial_net"] for item in rows]
    noncomm_stats = positioning_stats(noncomm_values)
    comm_stats = positioning_stats(comm_values)
    observed_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return {
        "key": f"cftc:legacy_futures_only:{latest['contract_market_code']}",
        "symbol": str(contract.get("symbol") or latest["contract_market_code"]).upper(),
        "name": latest["market"],
        "asset_class": "futures_positioning",
        "instrument": "CFTC Legacy Futures Only",
        "provider": "CFTC",
        "feed_class": "Weekly regulatory positioning disclosure; Tuesday report date",
        "currency": "contracts",
        "observed_at": observed_at,
        "data_as_of": latest["report_date"],
        "caveat": (
            "Weekly reported positions, not transaction records or real-time fund flows. "
            "Publication timestamp is not provided by this dataset; report date is the Tuesday position date."
        ),
        "observations": [
            {
                "date": item["report_date"],
                "open_interest": item["open_interest"],
                "noncommercial_net": item["noncommercial_net"],
                "commercial_net": item["commercial_net"],
            }
            for item in rows
        ],
        "extra": {
            "report_type": "Legacy Futures Only",
            "report_date": latest["report_date"],
            "publication_date": None,
            "contract_market_code": latest["contract_market_code"],
            "open_interest": latest["open_interest"],
            "noncommercial": {
                "long": latest["noncommercial_long"],
                "short": latest["noncommercial_short"],
                "net": latest["noncommercial_net"],
                "weekly_net_change": (
                    latest["noncommercial_net"] - previous["noncommercial_net"] if previous else None
                ),
                "historical_percentile": noncomm_stats["percentile"],
                "historical_z_score": noncomm_stats["z_score"],
                "lookback_observations": len(rows),
            },
            "commercial": {
                "long": latest["commercial_long"],
                "short": latest["commercial_short"],
                "net": latest["commercial_net"],
                "weekly_net_change": (
                    latest["commercial_net"] - previous["commercial_net"] if previous else None
                ),
                "historical_percentile": comm_stats["percentile"],
                "historical_z_score": comm_stats["z_score"],
                "lookback_observations": len(rows),
            },
            "source_url": f"https://publicreporting.cftc.gov/Commitments-of-Traders/Legacy-Futures-Only/{LEGACY_FUTURES_ONLY_DATASET}",
            "methodology": "Net = long - short; percentile is empirical rank within retrieved weekly history; z-score uses population standard deviation.",
        },
    }


def run(
    watchlist_path: str | Path,
    output_path: str | Path,
    *,
    history_limit: int = 260,
    publish: bool = True,
    source_revision: str | None = None,
) -> dict[str, Any]:
    config = json.loads(Path(watchlist_path).read_text(encoding="utf-8"))
    contracts = config.get("contracts") if isinstance(config, dict) else None
    if not isinstance(contracts, list) or not contracts:
        raise ValueError("CFTC watchlist must contain a non-empty contracts array.")
    series: list[dict[str, Any]] = []
    results = []
    for contract in contracts:
        if not isinstance(contract, dict):
            raise ValueError("CFTC watchlist contracts must be objects.")
        rows = fetch_contract(contract, limit=history_limit)
        item = build_market_series(contract, rows)
        series.append(item)
        results.append({
            "market": item["name"],
            "symbol": item["symbol"],
            "report_date": item["data_as_of"],
            "open_interest": item["extra"]["open_interest"],
            "noncommercial_net": item["extra"]["noncommercial"]["net"],
            "noncommercial_percentile": item["extra"]["noncommercial"]["historical_percentile"],
            "history_count": len(rows),
        })
    publish_result = publish_market_series(series, source_revision or os.getenv("GITHUB_SHA", "UNKNOWN")) if publish else {
        "status": "SKIPPED", "accepted": 0, "error": None
    }
    payload = {
        "schema_version": "1.0",
        "source": "CFTC Public Reporting Environment",
        "report_type": "Legacy Futures Only",
        "retrieved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "history_limit": history_limit,
        "status": "PUBLISHED" if publish_result["status"] in {"DIRECT_SUPABASE", "CONNECTED"} else publish_result["status"],
        "publish": publish_result,
        "contracts": results,
        "limitations": [
            "COT positions are weekly exposures, not trade records or real-time capital flows.",
            "The report date is the Tuesday position date; this dataset does not provide the public release timestamp.",
            "Legacy participant classes are commercial and non-commercial; they are not equivalent to named institutions.",
            "Only configured futures-only contracts are included; options-combined and TFF classifications are not mixed into this feed.",
        ],
    }
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch and publish CFTC Legacy Futures Only positioning.")
    parser.add_argument("--watchlist", default="config/cftc_watchlist.json")
    parser.add_argument("--output", default="reports/cftc-positioning-latest.json")
    parser.add_argument("--history-limit", type=int, default=260)
    parser.add_argument("--no-publish", action="store_true")
    args = parser.parse_args()
    result = run(args.watchlist, args.output, history_limit=args.history_limit, publish=not args.no_publish)
    print(json.dumps({
        "status": result["status"],
        "contract_count": len(result["contracts"]),
        "publish": result["publish"],
        "output": args.output,
    }, ensure_ascii=False))
    return 0 if result["status"] in {"PUBLISHED", "SKIPPED"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
