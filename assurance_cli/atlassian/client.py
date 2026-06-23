from __future__ import annotations

from typing import Any

import httpx

from assurance_cli.config import AtlassianConfig
from assurance_cli.exceptions import AssuranceError


class AtlassianClient:
    def __init__(self, config: AtlassianConfig, timeout: float = 30.0) -> None:
        self.config = config
        self._client = httpx.Client(
            base_url=config.base_url,
            auth=(config.email, config.api_token),
            timeout=timeout,
            headers={"Accept": "application/json"},
        )

    def close(self) -> None:
        self._client.close()

    def get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        try:
            response = self._client.get(path, params={k: v for k, v in (params or {}).items() if v is not None})
        except httpx.RequestError as exc:
            raise AssuranceError(f"Atlassian request failed before receiving a response: {exc}") from exc
        return self._handle(response)

    def post(self, path: str, json_payload: dict[str, Any]) -> dict[str, Any]:
        try:
            response = self._client.post(path, json=json_payload)
        except httpx.RequestError as exc:
            raise AssuranceError(f"Atlassian request failed before receiving a response: {exc}") from exc
        return self._handle(response)

    def _handle(self, response: httpx.Response) -> dict[str, Any]:
        if response.status_code in {401, 403}:
            raise AssuranceError(
                f"Atlassian request failed: {response.status_code} {response.reason_phrase}. "
                "Check ATLASSIAN_EMAIL and ATLASSIAN_API_TOKEN and confirm access."
            )
        if response.status_code >= 400:
            raise AssuranceError(f"Atlassian request failed: {response.status_code} {response.reason_phrase}.")
        return response.json()
