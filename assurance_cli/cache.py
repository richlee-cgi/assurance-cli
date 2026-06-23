from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from assurance_cli.util.redaction import redact


@dataclass(frozen=True)
class Cache:
    root: Path
    enabled: bool = True

    def key(self, namespace: str, payload: Any) -> str:
        serialized = json.dumps(redact(payload), sort_keys=True, default=str)
        digest = hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:24]
        return f"{namespace}/{digest}"

    def path_for(self, cache_key: str) -> Path:
        return self.root.joinpath(*cache_key.split("/")).with_suffix(".json")

    def get(self, cache_key: str) -> Any | None:
        if not self.enabled:
            return None
        path = self.path_for(cache_key)
        if not path.exists():
            return None
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)["data"]

    def set(self, cache_key: str, data: Any, metadata: dict[str, Any] | None = None) -> None:
        if not self.enabled:
            return
        path = self.path_for(cache_key)
        path.parent.mkdir(parents=True, exist_ok=True)
        envelope = {
            "timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
            "cache_key": cache_key,
            "metadata": redact(metadata or {}),
            "data": redact(data),
        }
        path.write_text(json.dumps(envelope, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")

    def list_entries(self) -> list[Path]:
        if not self.root.exists():
            return []
        return sorted(self.root.rglob("*.json"))

