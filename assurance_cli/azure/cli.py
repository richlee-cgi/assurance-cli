from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from typing import Any

from assurance_cli.exceptions import AssuranceError, UnsafeCommandError
from assurance_cli.util.redaction import redact_text

ALLOWED_PREFIXES: tuple[tuple[str, ...], ...] = (
    ("az", "account", "show"),
    ("az", "account", "list"),
    ("az", "group", "list"),
    ("az", "resource", "list"),
    ("az", "resource", "show"),
    ("az", "graph", "query"),
    ("az", "functionapp", "list"),
    ("az", "functionapp", "show"),
    ("az", "functionapp", "config", "appsettings", "list"),
    ("az", "webapp", "list"),
    ("az", "webapp", "show"),
    ("az", "apim", "list"),
    ("az", "apim", "show"),
    ("az", "apim", "api", "list"),
    ("az", "storage", "account", "list"),
    ("az", "servicebus", "namespace", "list"),
    ("az", "eventgrid", "topic", "list"),
    ("az", "monitor", "diagnostic-settings", "list"),
    ("az", "role", "assignment", "list"),
)

BLOCKED_TOKENS = {
    "add",
    "apply",
    "assign",
    "create",
    "delete",
    "deploy",
    "import",
    "publish",
    "remove",
    "restart",
    "set",
    "start",
    "stop",
    "sync",
    "update",
}


@dataclass(frozen=True)
class AzureCommandResult:
    command: list[str]
    data: Any
    stderr: str


def az_available() -> str | None:
    return shutil.which("az")


def validate_az_command(command: list[str]) -> None:
    if not command or command[0] != "az":
        raise UnsafeCommandError("Blocked unsafe command: Azure wrapper only runs az commands.")
    tokens = {part.lower() for part in command[1:] if not part.startswith("-")}
    blocked = sorted(tokens & BLOCKED_TOKENS)
    if blocked:
        raise UnsafeCommandError(
            f"Blocked unsafe command: {' '.join(command)}\n"
            f"Blocked token(s): {', '.join(blocked)}. Only read-only Azure CLI commands are allowed."
        )
    if not any(_starts_with(command, prefix) for prefix in ALLOWED_PREFIXES):
        raise UnsafeCommandError(
            f"Blocked unsafe command: {' '.join(command)}\n"
            "Only explicitly allowlisted Azure CLI commands are allowed in v1."
        )


def run_az_json(command: list[str], *, dry_run: bool = False) -> AzureCommandResult:
    validate_az_command(command)
    normalized = _ensure_json_output(command)
    if dry_run:
        return AzureCommandResult(command=normalized, data={"dry_run": True, "command": normalized}, stderr="")
    if not az_available():
        raise AssuranceError("Azure CLI not found on PATH. Install Azure CLI or run without Azure commands.")
    completed = subprocess.run(normalized, capture_output=True, text=True, check=False)
    stderr = redact_text(completed.stderr.strip())
    if completed.returncode != 0:
        message = stderr or redact_text(completed.stdout.strip()) or f"az exited with {completed.returncode}"
        raise AssuranceError(f"Azure CLI command failed: {message}")
    stdout = completed.stdout.strip()
    if not stdout:
        data: Any = None
    else:
        try:
            data = json.loads(stdout)
        except json.JSONDecodeError as exc:
            raise AssuranceError("Azure CLI did not return valid JSON.") from exc
    return AzureCommandResult(command=normalized, data=data, stderr=stderr)


def build_resource_graph_query(
    *,
    query: str | None,
    resource_type: str | None,
    resource_group: str | None,
    tags: tuple[str, ...],
    limit: int,
) -> str:
    lines = ["Resources"]
    if query:
        escaped = query.replace("'", "\\'")
        lines.append(f"| where name contains '{escaped}'")
    if resource_type:
        escaped_type = resource_type.replace("'", "\\'")
        lines.append(f"| where type =~ '{escaped_type}'")
    if resource_group:
        escaped_rg = resource_group.replace("'", "\\'")
        lines.append(f"| where resourceGroup =~ '{escaped_rg}'")
    for tag in tags:
        if "=" not in tag:
            raise AssuranceError(f"Invalid --tag value '{tag}'. Expected KEY=VALUE.")
        key, value = tag.split("=", 1)
        key = key.replace("'", "\\'")
        value = value.replace("'", "\\'")
        lines.append(f"| where tostring(tags['{key}']) =~ '{value}'")
    lines.append("| project name, type, resourceGroup, location, id, subscriptionId, tags")
    lines.append("| order by name asc")
    lines.append(f"| limit {limit}")
    return "\n".join(lines)


def _ensure_json_output(command: list[str]) -> list[str]:
    if "-o" in command or "--output" in command:
        return command
    return [*command, "-o", "json"]


def _starts_with(command: list[str], prefix: tuple[str, ...]) -> bool:
    return tuple(command[: len(prefix)]) == prefix

