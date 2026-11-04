from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sec_13f_data_hub import GriosDataHubClient
from sec_13f_ingestion import ingest_13f_report_period
from sec_edgar_client import SecEdgarClient


def run_ingestion(
    filer_cik: str,
    report_period: str,
    *,
    output_path: str | Path,
    registry_path: str | Path,
    environ: dict[str, str] | None = None,
) -> dict[str, Any]:
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
        raise RuntimeError("Missing required GitHub Actions variables/secrets: " + ", ".join(missing))

    sec = SecEdgarClient(user_agent=user_agent)
    hub = GriosDataHubClient(data_hub_url, token)
    retrieved_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    report = ingest_13f_report_period(
        sec,
        filer_cik,
        report_period,
        retrieved_at=retrieved_at,
        include_historical=True,
        database=str(registry_path),
        data_hub_client=hub,
        source_revision=source_revision,
    )

    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Ingest and reconcile one SEC Form 13F filer/report period."
    )
    parser.add_argument("--cik", required=True, help="10-digit SEC CIK (zero padding is applied by the client).")
    parser.add_argument("--report-period", required=True, help="13F report period in YYYY-MM-DD.")
    parser.add_argument("--output", default="artifacts/sec-13f/report.json")
    parser.add_argument("--database", default="artifacts/sec-13f/registry.sqlite3")
    args = parser.parse_args()

    report = run_ingestion(
        args.cik,
        args.report_period,
        output_path=args.output,
        registry_path=args.database,
    )
    published = report["data_hub_publish"]
    print(json.dumps({
        "status": "success",
        "filer_cik": report["filer_cik"],
        "report_period": report["report_period"],
        "holdings_count": report["holdings_count"],
        "filings_count": report["discovered_filing_count"],
        "snapshot_id": published["snapshot_id"],
        "data_hub_status": published["status"],
        "report_artifact": args.output,
        "registry_artifact": args.database,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
