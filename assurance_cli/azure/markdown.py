from __future__ import annotations

import json
from collections import Counter
from typing import Any

from assurance_cli.markdown import document_header, fenced_json, markdown_table
from assurance_cli.util.redaction import redact


def azure_check_markdown(*, account: dict[str, Any] | None, az_path: str | None, command: str) -> str:
    body = document_header("Azure CLI Check", "Azure", command, "Current Azure CLI context")
    if not account:
        rows = [["Azure CLI path", az_path or "not found"], ["Current account", "not logged in or unavailable"]]
    else:
        rows = [
            ["Azure CLI path", az_path or "not found"],
            ["Subscription", account.get("name")],
            ["Subscription ID", account.get("id")],
            ["Tenant", account.get("tenantDisplayName") or account.get("tenantId")],
            ["User", account.get("user", {}).get("name")],
        ]
    return body + markdown_table(["Field", "Value"], rows)


def azure_resources_markdown(*, title: str, data: Any, command: str, scope: str) -> str:
    body = document_header(title, "Azure", command, scope)
    resources = _as_list(data)
    if not resources:
        return body + "_No Azure resources found._\n"
    body += _resource_overview_table(resources)
    body += "\n"
    for resource in resources:
        body += resource_markdown(resource)
    return body


def resource_markdown(resource: dict[str, Any]) -> str:
    body = f"## {resource.get('name') or resource.get('id')}\n\n"
    rows = [
        ["Type", resource.get("type", "")],
        ["Resource group", resource.get("resourceGroup") or resource.get("resourceGroupName") or ""],
        ["Location", resource.get("location", "")],
    ]
    if resource.get("subscriptionId"):
        rows.append(["Subscription", resource.get("subscriptionId")])
    if resource.get("id"):
        rows.append(["ID", resource.get("id")])
    body += markdown_table(["Field", "Value"], rows, max_cell_chars=180)
    tags = resource.get("tags")
    if tags:
        body += "\n### Tags\n\n"
        body += markdown_table(["Tag", "Value"], [[key, value] for key, value in sorted(tags.items())])
    selected = {
        key: value
        for key, value in resource.items()
        if key not in {"name", "type", "resourceGroup", "resourceGroupName", "location", "subscriptionId", "id", "tags"}
    }
    if selected:
        body += "\n### Properties\n\n"
        body += fenced_json(redact(selected)) + "\n"
    body += "\n"
    return body


def azure_snapshot_markdown(*, resource_group: str, resources: list[dict[str, Any]], command: str) -> str:
    body = document_header("Azure Resource Group Snapshot", "Azure", command, resource_group)
    body += "## Summary\n\n"
    body += f"- Resource group: `{resource_group}`\n"
    body += f"- Resource count: `{len(resources)}`\n"
    type_counts = Counter(resource.get("type", "Unknown") for resource in resources)
    if type_counts:
        body += "\n### Resource Types\n\n"
        body += markdown_table(["Type", "Count"], [[resource_type, count] for resource_type, count in sorted(type_counts.items())])
    body += "\n## Resources\n\n"
    if not resources:
        body += "_No resources found._\n"
        return body
    for resource in resources:
        body += resource_markdown(resource)
    return body


def function_apps_markdown(
    *,
    apps: list[dict[str, Any]],
    settings_by_app: dict[str, list[dict[str, Any]]],
    setting_errors: dict[str, str],
    show_values: bool,
    command: str,
    scope: str,
) -> str:
    body = document_header("Azure Function Apps", "Azure", command, scope)
    if not apps:
        return body + "_No Function Apps found._\n"
    for app in apps:
        name = app.get("name")
        config = app.get("functionAppConfig") or {}
        runtime = config.get("runtime") or {}
        deployment = config.get("deployment") or {}
        storage = deployment.get("storage") or {}
        scale = config.get("scaleAndConcurrency") or {}
        identity = app.get("identity") or {}
        user_assigned = identity.get("userAssignedIdentities") or {}
        body += f"## {name}\n\n"
        rows = [
            ["Resource group", app.get("resourceGroup")],
            ["Location", app.get("location")],
            ["State", app.get("state")],
            ["Runtime", f"{runtime.get('name', '')} {runtime.get('version', '')}".strip()],
            ["SKU", app.get("sku")],
            ["HTTPS only", app.get("httpsOnly")],
            ["Public network access", app.get("publicNetworkAccess")],
            ["Storage deployment type", storage.get("type")],
            ["Maximum instances", scale.get("maximumInstanceCount")],
            ["Identity type", identity.get("type")],
            ["User-assigned identities", len(user_assigned)],
        ]
        if app.get("serverFarmId"):
            rows.append(["App Service plan", app.get("serverFarmId")])
        if app.get("virtualNetworkSubnetId"):
            rows.append(["VNet subnet", app.get("virtualNetworkSubnetId")])
        if app.get("id"):
            rows.append(["ID", app.get("id")])
        body += markdown_table(["Field", "Value"], rows, max_cell_chars=180)
        if name in setting_errors:
            body += "\n### App Settings\n\n"
            body += f"_Unable to retrieve app settings: {setting_errors[name]}_\n"
        elif name in settings_by_app:
            body += "\n" + app_settings_markdown(name=name, settings=settings_by_app[name], show_values=show_values)
        body += "\n"
    return body


def app_settings_markdown(*, name: str, settings: list[dict[str, Any]], show_values: bool) -> str:
    body = f"### App Settings: `{name}`\n\n"
    if not settings:
        return body + "_No app settings returned._\n"
    rows = [[setting.get("name"), setting.get("value") if show_values else "[REDACTED]"] for setting in settings]
    return body + markdown_table(["Setting", "Value"], rows, max_cell_chars=180)


def raw_json_section(title: str, data: Any) -> str:
    return f"## {title}\n\n```json\n{json.dumps(redact(data), indent=2, sort_keys=True, ensure_ascii=False)}\n```\n"


def _as_list(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, dict) and isinstance(data.get("data"), list):
        return data["data"]
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return [data]
    return []


def _resource_overview_table(resources: list[dict[str, Any]]) -> str:
    rows = [
        [
            resource.get("name") or "",
            resource.get("type") or "",
            resource.get("resourceGroup") or resource.get("resourceGroupName") or "",
            resource.get("location") or "",
        ]
        for resource in resources
    ]
    return markdown_table(["Name", "Type", "Resource group", "Location"], rows)
