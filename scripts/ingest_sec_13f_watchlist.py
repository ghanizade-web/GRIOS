from __future__ import annotations

import argparse
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from sec_13f_data_hub import GriosDataHubClient
from sec_13f_ingestion import ingest_13f_report_period
from sec_edgar_client import SecEdgarClient, normalize_cik


def load_watchlist(path: str | Path) -> list[dict[str, Any]]:
    source = Path(path)
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Unable to read SEC 13F watchlist JSON: {exc}") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("watchlist"), list):
        raise ValueError("Watchlist file must contain a top-level 'watchlist' array.")

    entries: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, raw in enumerate(payload["watchlist"]):
        if not isinstance(raw, dict):
            raise ValueError(f"Watchlist entry {index} must be an object.")
        raw_cik = raw.get("cik")
        if not isinstance(raw_cik, str) or not raw_cik.isdigit() or not 1 <= len(raw_cik) <= 10:
            raise ValueError(f"Watchlist entry {index} must have a 1-10 digit string CIK.")
        cik = normalize_cik(raw_cik)
        if cik in seen:
            raise ValueError(f"Duplicate CIK in SEC 13F watchlist: {cik}.")
        seen.add(cik)

        name = raw.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"Watchlist entry {index} must have a non-empty name.")
        enabled = raw.get("enabled", True)
        if not isinstance(enabled, bool):
            raise ValueError(f"Watchlist entry {index} enabled must be a boolean.")
        reference_url = raw.get("reference_url")
        if reference_url is not None:
            parsed = urlparse(reference_url) if isinstance(reference_url, str) else None
            if parsed is None or parsed.scheme != "https" or parsed.hostname not in {"sec.gov", "www.sec.gov"}:
                raise ValueError(f"Watchlist entry {index} reference_url must be an HTTPS SEC.gov URL.")

        entries.append({
            "cik": cik,
            "name": name.strip(),
            "enabled": enabled,
            "reference_url": reference_url,
        })
    if not any(item["enabled"] for item in entries):
        raise ValueError("SEC 13F watchlist has no enabled filers.")
    return entries


def run_watchlist(
    report_period: str,
    *,
    watchlist_path: str | Path,
    output_dir: str | Path,
    registry_path: str | Path,
    summary_path: str | Path,
    environ: dict[str, str] | None = None,
) -> dict[str, Any]:
    try:
        period = datetime.strptime(report_period, "%Y-%m-%d").date().isoformat()
    except (TypeError, ValueError) as exc:
        raise ValueError("report_period must use YYYY-MM-DD.") from exc

    env = os.environ if environ is None else environ
    user_agent = env.get("SEC_USER_AGENT", "").strip()
    data_hub_url = env.get("GRIOS_DATA_HUB_URL", "").strip()
    token = env.get("GRIOS_INGEST_TOKEN", "").strip()
    source_revision = env.get("GITHUB_SHA", "").strip() or None
    missing = [
        name for name, value in (
            ("SEC_USER_AGENT", user_agent),
            ("GRIOS_DATA_HUB_URL", data_hub_url),
            ("GRIOS_INGEST_TOKEN", token),
        ) if not value
    ]
    if missing:
        raise RuntimeError(
            "Missing required GitHub Actions variables/secrets: " + ", ".join(missing)
        )

    entries = load_watchlist(watchlist_path)
    # One shared SEC client is essential: request pacing then applies across
    # every filer in this batch rather than resetting for each CIK.
    sec = SecEdgarClient(user_agent=user_agent)
    hub = GriosDataHubClient(data_hub_url, token)
    reports_dir = Path(output_dir)
    reports_dir.mkdir(parents=True, exist_ok=True)
    results = []

    for entry in entries:
        if not entry["enabled"]:
            results.append({
                "cik": entry["cik"],
                "name": entry["name"],
                "status": "SKIPPED_DISABLED",
            })
            continue
        try:
            retrieved_at = datetime.now().astimezone().isoformat(timespec="seconds")
            report = ingest_13f_report_period(
                sec,
                entry["cik"],
                period,
                retrieved_at=retrieved_at,
                include_historical=True,
                database=str(registry_path),
                data_hub_client=hub,
                source_revision=source_revision,
            )
            artifact = reports_dir / f"{entry['cik']}_{period}.json"
            artifact.write_text(
                json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            results.append({
                "cik": entry["cik"],
                "name": entry["name"],
                "status": "PUBLISHED",
                "snapshot_id": report.get("data_hub_publish", {}).get("snapshot_id"),
                "holdings_count": report.get("holdings_count"),
                "filings_count": report.get("discovered_filing_count"),
                "artifact": str(artifact),
            })
        except Exception as exc:  # continue the batch; report failures explicitly
            results.append({
                "cik": entry["cik"],
                "name": entry["name"],
                "status": "FAILED",
                "error_type": type(exc).__name__,
                "error": str(exc),
            })

    failed = sum(item["status"] == "FAILED" for item in results)
    published = sum(item["status"] == "PUBLISHED" for item in results)
    summary = {
        "schema_version": "1.0",
        "report_period": period,
        "watchlist_path": str(watchlist_path),
        "source_revision": source_revision,
        "status": "SUCCESS" if failed == 0 else "PARTIAL_FAILURE",
        "filers_total": len(entries),
        "filers_published": published,
        "filers_failed": failed,
        "filers_skipped": sum(item["status"] == "SKIPPED_DISABLED" for item in results),
        "results": results,
    }
    destination = Path(summary_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Ingest a configured SEC 13F institutional-manager watchlist."
    )
    parser.add_argument("--report-period", required=True, help="13F report period in YYYY-MM-DD.")
    parser.add_argument("--watchlist", default="config/sec_13f_watchlist.json")
    parser.add_argument("--output-dir", default="artifacts/sec-13f-watchlist/reports")
    parser.add_argument("--database", default="artifacts/sec-13f-watchlist/registry.sqlite3")
    parser.add_argument("--summary", default="artifacts/sec-13f-watchlist/summary.json")
    args = parser.parse_args()

    summary = run_watchlist(
        args.report_period,
        watchlist_path=args.watchlist,
        output_dir=args.output_dir,
        registry_path=args.database,
        summary_path=args.summary,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 1 if summary["filers_failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
