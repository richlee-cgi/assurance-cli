from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

REDACTION_MARKER = "[REDACTED]"

SENSITIVE_KEY_RE = re.compile(
    r"(api[_-]?token|authorization|bearer|client[_-]?secret|connection[_-]?string|"
    r"password|secret|token|private[_-]?key|access[_-]?key|account[_-]?key|key)",
    re.IGNORECASE,
)
SENSITIVE_VALUE_RE = re.compile(
    r"(?i)(Bearer\s+)[A-Za-z0-9._~+/=-]+|"
    r"(Basic\s+)[A-Za-z0-9._~+/=-]+|"
    r"([?&](?:token|key|sig|client_secret)=)[^&\s]+"
)


def redact_text(value: str) -> str:
    def repl(match: re.Match[str]) -> str:
        prefix = next((g for g in match.groups() if g), "")
        return f"{prefix}{REDACTION_MARKER}"

    return SENSITIVE_VALUE_RE.sub(repl, value)


def redact(value: Any) -> Any:
    if isinstance(value, Mapping):
        redacted: dict[str, Any] = {}
        for key, item in value.items():
            key_text = str(key)
            redacted[key_text] = REDACTION_MARKER if SENSITIVE_KEY_RE.search(key_text) else redact(item)
        return redacted
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
        return [redact(item) for item in value]
    return value

