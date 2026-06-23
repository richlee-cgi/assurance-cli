from __future__ import annotations

import json
from typing import Any

from assurance_cli.markdown import document_header, fenced_json
from assurance_cli.util.redaction import redact


def dataverse_check_markdown(*, pac_path: str | None, auth_result: Any, command: str) -> str:
    body = document_header("Dataverse CLI Check", "Dataverse/Power Platform", command, "Current pac context")
    body += f"- Power Platform CLI path: `{pac_path or 'not found'}`\n"
    body += "\n## Auth Profiles\n\n"
    body += render_pac_payload(auth_result)
    return body


def dataverse_list_markdown(*, title: str, payload: Any, command: str, scope: str) -> str:
    body = document_header(title, "Dataverse/Power Platform", command, scope)
    body += render_pac_payload(payload)
    return body


def dataverse_snapshot_markdown(
    *,
    auth_profiles: Any,
    environments: Any,
    solutions: Any,
    connectors: Any,
    connection_refs: Any,
    warnings: list[str],
    command: str,
) -> str:
    body = document_header("Dataverse Snapshot", "Dataverse/Power Platform", command, "Current pac profile")
    if warnings:
        body += "## Warnings\n\n"
        body += "\n".join(f"- {warning}" for warning in warnings) + "\n\n"
    body += "## Auth Profiles\n\n" + render_pac_payload(auth_profiles)
    body += "\n## Environments\n\n" + render_pac_payload(environments)
    body += "\n## Solutions\n\n" + render_pac_payload(solutions)
    body += "\n## Connectors\n\n" + render_pac_payload(connectors)
    body += "\n## Connections\n\n" + render_pac_payload(connection_refs)
    return body


def render_pac_payload(payload: Any) -> str:
    if payload is None:
        return "_No data returned._\n"
    if isinstance(payload, str):
        if not payload.strip():
            return "_No data returned._\n"
        return f"```text\n{payload.strip()}\n```\n"
    if isinstance(payload, list):
        if not payload:
            return "_No items returned._\n"
        if all(isinstance(item, dict) for item in payload):
            return _dict_list_markdown(payload)
    if isinstance(payload, dict):
        return fenced_json(redact(payload)) + "\n"
    return f"```json\n{json.dumps(redact(payload), indent=2, sort_keys=True, ensure_ascii=False)}\n```\n"


def _dict_list_markdown(items: list[dict[str, Any]]) -> str:
    lines = []
    for item in items:
        name = item.get("DisplayName") or item.get("displayName") or item.get("FriendlyName") or item.get("name") or item.get("Name") or item.get("EnvironmentId") or item.get("Id") or "Item"
        lines.append(f"### {name}")
        for key, value in sorted(item.items()):
            if isinstance(value, (dict, list)):
                continue
            lines.append(f"- `{key}`: `{value}`")
        complex_values = {key: value for key, value in item.items() if isinstance(value, (dict, list))}
        if complex_values:
            lines.append("")
            lines.append(fenced_json(redact(complex_values)))
        lines.append("")
    return "\n".join(lines).strip() + "\n"

