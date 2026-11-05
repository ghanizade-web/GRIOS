from __future__ import annotations

from datetime import datetime
from typing import Any
from urllib.parse import urlsplit

import httpx

from sec_13f_registry import prepare_13f_data_hub_payload


class GriosDataHubClient:
    """Authenticated client for the GRIOS Data Hub SEC 13F endpoints."""

    def __init__(
        self,
        base_url: str,
        token: str,
        *,
        timeout: float = 30.0,
        client: Any | None = None,
    ) -> None:
        parsed = urlsplit(base_url)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("Data Hub base_url must be an HTTPS origin.")
        if parsed.path not in ("", "/") or parsed.query or parsed.fragment:
            raise ValueError("Data Hub base_url must not include a path, query or fragment.")
        if not isinstance(token, str) or not token.strip():
            raise ValueError("Data Hub bearer token is required.")
        self.base_url = base_url.rstrip("/")
        self.token = token.strip()
        self.timeout = timeout
        self._client = client

    def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        headers = {
            "authorization": f"Bearer {self.token}",
            "content-type": "application/json",
            "accept": "application/json",
        }
        if self._client is None:
            with httpx.Client(timeout=self.timeout) as client:
                return client.request(
                    method, self.base_url + path, headers=headers,
                    timeout=self.timeout, **kwargs,
                )
        return self._client.request(
            method, self.base_url + path, headers=headers,
            timeout=self.timeout, **kwargs,
        )

    def publish_snapshot(
        self,
        report: dict[str, Any],
        *,
        source_revision: str | None = None,
    ) -> dict[str, Any]:
        payload = prepare_13f_data_hub_payload(
            report, source_revision=source_revision
        )
        response = self._request("POST", "/v1/13f/snapshots", json=payload)
        response.raise_for_status()
        result = response.json()
        if not isinstance(result, dict) or result.get("status") != "accepted":
            raise ValueError("Data Hub did not confirm SEC 13F snapshot acceptance.")
        if result.get("snapshot_id") != payload["snapshot"]["snapshot_id"]:
            raise ValueError("Data Hub accepted a different SEC 13F snapshot identity.")
        return result

    def get_latest_snapshot(
        self,
        filer_cik: str,
        report_period: str,
    ) -> dict[str, Any] | None:
        if not isinstance(filer_cik, str) or len(filer_cik) != 10 or not filer_cik.isdigit():
            raise ValueError("filer_cik must be a zero-padded 10-digit CIK.")
        try:
            period = datetime.strptime(report_period, "%Y-%m-%d").date().isoformat()
        except (TypeError, ValueError) as exc:
            raise ValueError("report_period must use YYYY-MM-DD.") from exc
        response = self._request(
            "GET",
            "/v1/13f/latest",
            params={"cik": filer_cik, "report_period": period},
        )
        response.raise_for_status()
        result = response.json()
        if not isinstance(result, dict):
            raise ValueError("Data Hub returned an invalid SEC 13F response.")
        return result.get("snapshot")



class Supabase13FClient:
    """Publish and retrieve SEC 13F snapshots through service-role-only RPCs."""

    def __init__(
        self,
        supabase_url: str,
        service_role_key: str,
        *,
        timeout: float = 30.0,
        client: Any | None = None,
    ) -> None:
        parsed = urlsplit(supabase_url)
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.path not in ("", "/")
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("Supabase URL must be an HTTPS origin.")
        if not isinstance(service_role_key, str) or not service_role_key.strip():
            raise ValueError("Supabase service-role key is required.")
        self.base_url = supabase_url.rstrip("/")
        self.service_role_key = service_role_key.strip()
        self.timeout = timeout
        self._client = client

    def _request(self, method: str, function: str, **kwargs: Any) -> httpx.Response:
        headers = {
            "apikey": self.service_role_key,
            "authorization": f"Bearer {self.service_role_key}",
            "content-type": "application/json",
            "accept": "application/json",
        }
        url = f"{self.base_url}/rest/v1/rpc/{function}"
        if self._client is None:
            with httpx.Client(timeout=self.timeout) as client:
                return client.request(
                    method, url, headers=headers, timeout=self.timeout, **kwargs
                )
        return self._client.request(
            method, url, headers=headers, timeout=self.timeout, **kwargs
        )

    def publish_snapshot(
        self,
        report: dict[str, Any],
        *,
        source_revision: str | None = None,
    ) -> dict[str, Any]:
        payload = prepare_13f_data_hub_payload(
            report, source_revision=source_revision
        )
        snapshot = payload["snapshot"]
        response = self._request(
            "POST",
            "ingest_grios_13f_snapshot",
            json={"p_snapshot": snapshot},
        )
        response.raise_for_status()
        result = response.json()
        if not isinstance(result, dict):
            raise ValueError("Supabase did not return a valid SEC 13F acknowledgement.")
        if result.get("snapshot_id") != snapshot["snapshot_id"]:
            raise ValueError("Supabase acknowledged a different SEC 13F snapshot identity.")
        return {
            "status": "accepted",
            **result,
        }

    def get_latest_snapshot(
        self,
        filer_cik: str,
        report_period: str,
    ) -> dict[str, Any] | None:
        if not isinstance(filer_cik, str) or len(filer_cik) != 10 or not filer_cik.isdigit():
            raise ValueError("filer_cik must be a zero-padded 10-digit CIK.")
        try:
            period = datetime.strptime(report_period, "%Y-%m-%d").date().isoformat()
        except (TypeError, ValueError) as exc:
            raise ValueError("report_period must use YYYY-MM-DD.") from exc
        response = self._request(
            "POST",
            "get_grios_latest_13f_snapshot",
            json={"p_filer_cik": filer_cik, "p_report_period": period},
        )
        response.raise_for_status()
        result = response.json()
        if result is None:
            return None
        if not isinstance(result, dict):
            raise ValueError("Supabase returned an invalid SEC 13F snapshot.")
        return result
