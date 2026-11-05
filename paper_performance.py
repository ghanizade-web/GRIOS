from __future__ import annotations

import hashlib
import math
import os
import statistics
from datetime import date, datetime, timezone
from typing import Any

import httpx

CHECKPOINT_TOLERANCES = {1: 1, 7: 2, 30: 4, 90: 10, 365: 21}
BENCHMARK_SYMBOLS = {
    "crypto": "BTC",
    "us_equity_etf": "SPY",
    "commodity_proxy": "DBC",
}
COST_ENVIRONMENT = {
    "crypto": "GRIOS_PAPER_COST_BPS_CRYPTO",
    "us_equity_etf": "GRIOS_PAPER_COST_BPS_EQUITY",
    "commodity_proxy": "GRIOS_PAPER_COST_BPS_COMMODITY",
}
MODEL_VERSION = "grios-v15-forward-paper-v2"


class PaperJournalError(RuntimeError):
    """Sanitized failure from the persistent paper journal."""


def _number(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def resolve_round_trip_cost_bps(
    asset_class: str,
    environ: dict[str, str] | None = None,
) -> float | None:
    env = os.environ if environ is None else environ
    name = COST_ENVIRONMENT.get(asset_class)
    raw = env.get(name, "").strip() if name else ""
    if not raw:
        return None
    value = _number(raw)
    if value is None or value < 0 or value > 10000:
        raise ValueError(f"Invalid round-trip cost configuration for {asset_class}.")
    return value


def make_fingerprint(asset_key: str, data_as_of: str) -> str:
    raw = f"{asset_key}|{data_as_of[:10]}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _metrics(values: list[float]) -> dict[str, Any] | None:
    if not values:
        return None
    return {
        "sample_size": len(values),
        "mean_return_pct": round(statistics.mean(values), 3),
        "median_return_pct": round(statistics.median(values), 3),
        "win_rate_pct": round(sum(value > 0 for value in values) / len(values) * 100, 2),
        "best_return_pct": round(max(values), 3),
        "worst_return_pct": round(min(values), 3),
    }


class SupabasePaperJournal:
    """Durable, idempotent forward-performance journal backed by Supabase REST."""

    def __init__(
        self,
        supabase_url: str | None = None,
        service_role_key: str | None = None,
        *,
        timeout: float = 20.0,
    ) -> None:
        self.url = (supabase_url or os.getenv("SUPABASE_URL", "")).strip().rstrip("/")
        self.key = (service_role_key or os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")).strip()
        self.timeout = timeout
        if not self.url.startswith("https://") or not self.key:
            raise PaperJournalError("SUPABASE_JOURNAL_NOT_CONFIGURED")

    def _request(
        self,
        method: str,
        table: str,
        *,
        params: dict[str, str] | None = None,
        payload: Any = None,
        prefer: str | None = None,
    ) -> Any:
        headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Accept": "application/json",
        }
        if payload is not None:
            headers["Content-Type"] = "application/json"
        if prefer:
            headers["Prefer"] = prefer
        try:
            response = httpx.request(
                method,
                f"{self.url}/rest/v1/{table}",
                params=params,
                json=payload,
                headers=headers,
                timeout=self.timeout,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise PaperJournalError(f"SUPABASE_JOURNAL_HTTP_{exc.response.status_code}") from None
        except httpx.HTTPError as exc:
            raise PaperJournalError(
                f"SUPABASE_JOURNAL_NETWORK_{type(exc).__name__}"
            ) from None
        if not response.content:
            return []
        try:
            return response.json()
        except ValueError:
            raise PaperJournalError("SUPABASE_JOURNAL_INVALID_RESPONSE") from None

    def _get_all(self, table: str, params: dict[str, str]) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        offset = 0
        page_size = 1000
        while True:
            page_params = dict(params)
            page_params["limit"] = str(page_size)
            page_params["offset"] = str(offset)
            page = self._request("GET", table, params=page_params)
            if not isinstance(page, list):
                raise PaperJournalError("SUPABASE_JOURNAL_INVALID_ROWS")
            rows.extend(row for row in page if isinstance(row, dict))
            if len(page) < page_size:
                break
            offset += page_size
        return rows

    def _get_signal_id(self, fingerprint: str) -> str:
        rows = self._request(
            "GET",
            "grios_paper_ideas",
            params={
                "select": "id",
                "fingerprint": f"eq.{fingerprint}",
                "limit": "1",
            },
        )
        if isinstance(rows, list) and rows and rows[0].get("id"):
            return str(rows[0]["id"])
        raise PaperJournalError("SUPABASE_JOURNAL_SIGNAL_LOOKUP_FAILED")

    def record_and_evaluate(
        self,
        records: list[dict[str, Any]],
        *,
        source_revision: str,
    ) -> dict[str, int]:
        current = {
            str(item["asset_key"]): item
            for item in records
            if item.get("asset_key") and _number(item.get("price")) is not None
        }
        inserted_signals = 0

        for item in records:
            if item.get("decision") != "WATCH_ONLY":
                continue
            price = _number(item.get("price"))
            data_as_of = str(item.get("data_as_of") or "")[:10]
            asset_key = str(item.get("asset_key") or "")
            if not asset_key or not data_as_of or price is None or price <= 0:
                continue

            fingerprint = make_fingerprint(asset_key, data_as_of)
            payload = {
                "fingerprint": fingerprint,
                "asset_key": asset_key,
                "symbol": str(item.get("symbol") or ""),
                "asset_class": str(item.get("asset_class") or ""),
                "provider": str(item.get("provider") or ""),
                "data_as_of": data_as_of,
                "recorded_at": str(item.get("recorded_at") or datetime.now(timezone.utc).isoformat()),
                "entry_price": price,
                "technical_score": _number(item.get("technical_score")),
                "factor_coverage_pct": int(item.get("factor_coverage_pct") or 0),
                "decision": "WATCH_ONLY",
                "thesis": str(item.get("thesis") or ""),
                "invalidation": str(item.get("invalidation") or ""),
                "benchmark_symbol": item.get("benchmark_symbol"),
                "benchmark_asset_key": item.get("benchmark_asset_key"),
                "benchmark_entry_price": _number(item.get("benchmark_entry_price")),
                "assumed_round_trip_cost_bps": _number(item.get("assumed_round_trip_cost_bps")),
                "model_version": MODEL_VERSION,
                "source_revision": source_revision,
                "metadata": item.get("metadata") if isinstance(item.get("metadata"), dict) else {},
            }
            result = self._request(
                "POST",
                "grios_paper_ideas",
                params={"on_conflict": "fingerprint"},
                payload=payload,
                prefer="resolution=ignore-duplicates,return=representation",
            )
            if isinstance(result, list) and result:
                inserted_signals += 1

        ideas = self._get_all(
            "grios_paper_ideas",
            {
                "select": (
                    "id,asset_key,data_as_of,entry_price,benchmark_asset_key,"
                    "benchmark_entry_price,assumed_round_trip_cost_bps,decision"
                ),
                "decision": "eq.WATCH_ONLY",
                "order": "recorded_at.asc",
            },
        )
        evaluations = self._get_all(
            "grios_paper_evaluations",
            {"select": "idea_id,checkpoint_days"},
        )
        evaluated = {
            (str(row.get("idea_id")), int(row.get("checkpoint_days")))
            for row in evaluations
            if row.get("idea_id") is not None and row.get("checkpoint_days") is not None
        }

        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        pending: list[dict[str, Any]] = []
        for idea in ideas:
            asset_key = str(idea.get("asset_key") or "")
            current_item = current.get(asset_key)
            if not current_item:
                continue
            current_price = _number(current_item.get("price"))
            entry_price = _number(idea.get("entry_price"))
            if current_price is None or current_price <= 0 or entry_price is None or entry_price <= 0:
                continue
            try:
                days = (
                    date.fromisoformat(str(current_item["data_as_of"])[:10])
                    - date.fromisoformat(str(idea["data_as_of"])[:10])
                ).days
            except (KeyError, TypeError, ValueError):
                continue
            if days < 0:
                continue

            benchmark_item = current.get(str(idea.get("benchmark_asset_key") or ""))
            benchmark_entry = _number(idea.get("benchmark_entry_price"))
            benchmark_price = (
                _number(benchmark_item.get("price"))
                if benchmark_item
                and str(benchmark_item.get("data_as_of") or "")[:10]
                == str(current_item.get("data_as_of") or "")[:10]
                else None
            )
            benchmark_return = (
                (benchmark_price / benchmark_entry - 1) * 100
                if benchmark_price is not None and benchmark_entry is not None and benchmark_entry > 0
                else None
            )
            gross_return = (current_price / entry_price - 1) * 100
            cost_bps = _number(idea.get("assumed_round_trip_cost_bps"))
            cost_pct = cost_bps / 100 if cost_bps is not None else None
            net_return = gross_return - cost_pct if cost_pct is not None else None
            excess_return = gross_return - benchmark_return if benchmark_return is not None else None

            for checkpoint, tolerance in CHECKPOINT_TOLERANCES.items():
                key = (str(idea["id"]), checkpoint)
                if key in evaluated or not checkpoint <= days <= checkpoint + tolerance:
                    continue
                pending.append({
                    "idea_id": str(idea["id"]),
                    "checkpoint_days": checkpoint,
                    "evaluated_at": now,
                    "observed_at": str(current_item["data_as_of"])[:10],
                    "price": current_price,
                    "return_pct": gross_return,
                    "benchmark_price": benchmark_price,
                    "benchmark_return_pct": benchmark_return,
                    "excess_return_pct": excess_return,
                    "assumed_round_trip_cost_bps": cost_bps,
                    "estimated_cost_pct": cost_pct,
                    "net_return_pct": net_return,
                    "source_revision": source_revision,
                })
                evaluated.add(key)

        if pending:
            self._request(
                "POST",
                "grios_paper_evaluations",
                params={"on_conflict": "idea_id,checkpoint_days"},
                payload=pending,
                prefer="resolution=ignore-duplicates,return=minimal",
            )
        return {
            "ideas_seen": len(ideas),
            "signals_inserted": inserted_signals,
            "evaluations_inserted": len(pending),
        }

    def performance_summary(self) -> dict[str, Any]:
        rows = self._get_all(
            "grios_paper_evaluations",
            {
                "select": (
                    "checkpoint_days,return_pct,benchmark_return_pct,excess_return_pct,"
                    "assumed_round_trip_cost_bps,net_return_pct"
                ),
                "order": "checkpoint_days.asc,observed_at.asc",
            },
        )
        grouped: dict[int, list[dict[str, Any]]] = {}
        for row in rows:
            try:
                checkpoint = int(row["checkpoint_days"])
            except (KeyError, TypeError, ValueError):
                continue
            if checkpoint in CHECKPOINT_TOLERANCES:
                grouped.setdefault(checkpoint, []).append(row)

        checkpoints: dict[int, dict[str, Any]] = {}
        for checkpoint in sorted(CHECKPOINT_TOLERANCES):
            items = grouped.get(checkpoint, [])
            gross = [v for row in items if (v := _number(row.get("return_pct"))) is not None]
            benchmark = [v for row in items if (v := _number(row.get("benchmark_return_pct"))) is not None]
            excess = [v for row in items if (v := _number(row.get("excess_return_pct"))) is not None]
            net = [v for row in items if (v := _number(row.get("net_return_pct"))) is not None]
            gross_stats = _metrics(gross)
            if gross_stats is None:
                continue
            checkpoints[checkpoint] = {
                **gross_stats,
                "benchmark_sample_size": len(benchmark),
                "mean_benchmark_return_pct": round(statistics.mean(benchmark), 3) if benchmark else None,
                "excess_sample_size": len(excess),
                "mean_excess_return_pct": round(statistics.mean(excess), 3) if excess else None,
                "median_excess_return_pct": round(statistics.median(excess), 3) if excess else None,
                "excess_win_rate_pct": round(sum(v > 0 for v in excess) / len(excess) * 100, 2) if excess else None,
                "cost_configured_sample_size": len(net),
                "mean_net_return_pct": round(statistics.mean(net), 3) if net else None,
                "median_net_return_pct": round(statistics.median(net), 3) if net else None,
                "net_win_rate_pct": round(sum(v > 0 for v in net) / len(net) * 100, 2) if net else None,
            }
        return {
            "status": "AVAILABLE" if checkpoints else "NO_MATURED_EVALUATIONS",
            "backend": "SUPABASE_PERSISTENT",
            "total_evaluations": sum(item["sample_size"] for item in checkpoints.values()),
            "checkpoints": checkpoints,
        }
