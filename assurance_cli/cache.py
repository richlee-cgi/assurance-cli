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

    def key_for_path(self, path: Path) -> str:
        return path.relative_to(self.root).with_suffix("").as_posix()

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

    def read_envelope(self, cache_key: str) -> dict[str, Any]:
        path = self.path_for(cache_key)
        if not path.exists():
            raise FileNotFoundError(cache_key)
        with path.open("r", encoding="utf-8") as handle:
            envelope = json.load(handle)
        return envelope if isinstance(envelope, dict) else {"data": envelope}

    def metadata_for_path(self, path: Path) -> dict[str, Any]:
        with path.open("r", encoding="utf-8") as handle:
            envelope = json.load(handle)
        cache_key = envelope.get("cache_key") or self.key_for_path(path)
        metadata = envelope.get("metadata") if isinstance(envelope.get("metadata"), dict) else {}
        return {
            "cache_key": cache_key,
            "timestamp": envelope.get("timestamp"),
            "source": metadata.get("source"),
            "endpoint": metadata.get("endpoint"),
            "path": str(path),
            "size_bytes": path.stat().st_size,
        }

    def clear(self, cache_key: str) -> bool:
        path = self.path_for(cache_key)
        if not path.exists():
            return False
        path.unlink()
        for parent in path.parents:
            if parent == self.root or not parent.exists():
                break
            try:
                parent.rmdir()
            except OSError:
                break
        return True

    def clear_all(self) -> int:
        entries = self.list_entries()
        for path in entries:
            path.unlink()
        for path in sorted((p for p in self.root.rglob("*") if p.is_dir()), reverse=True):
            try:
                path.rmdir()
            except OSError:
                pass
        return len(entries)
