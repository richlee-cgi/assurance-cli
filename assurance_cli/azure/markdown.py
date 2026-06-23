from __future__ import annotations

import json
from collections import Counter
from typing import Any

from assurance_cli.markdown import document_header, fenced_json
from assurance_cli.util.redaction import redact


def azure_check_markdown(*, account: dict[str, Any] | None, az_path: str | None, command: str) -> str:
    body = document_header("Azure CLI Check", "Azure", command, "Current Azure CLI context")
    body += f"- Azure CLI path: `{az_path or 'not found'}`\n"
    if not account:
        body += "- Current account: `not logged in or unavailable`\n"
        return body
    body += f"- Subscription: `{account.get('name')}`\n"
    body += f"- Subscription ID: `{account.get('id')}`\n"
    body += f"- Tenant: `{account.get('tenantDisplayName') or account.get('tenantId')}`\n"
    body += f"- User: `{account.get('user', {}).get('name')}`\n"
    return body


def azure_resources_markdown(*, title: str, data: Any, command: str, scope: str) -> str:
    body = document_header(title, "Azure", command, scope)
    resources = _as_list(data)
    if not resources:
        return body + "_No Azure resources found._\n"
    for resource in resources:
        body += resource_markdown(resource)
    return body


def resource_markdown(resource: dict[str, Any]) -> str:
    body = f"## {resource.get('name') or resource.get('id')}\n\n"
    body += f"- Type: `{resource.get('type', '')}`\n"
    body += f"- Resource group: `{resource.get('resourceGroup') or resource.get('resourceGroupName') or ''}`\n"
    body += f"- Location: `{resource.get('location', '')}`\n"
    if resource.get("subscriptionId"):
        body += f"- Subscription: `{resource.get('subscriptionId')}`\n"
    if resource.get("id"):
        body += f"- ID: `{resource.get('id')}`\n"
    tags = resource.get("tags")
    if tags:
        body += "\n### Tags\n\n"
        body += "\n".join(f"- `{key}`: `{value}`" for key, value in sorted(tags.items())) + "\n"
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
        body += "\n".join(f"- `{resource_type}`: {count}" for resource_type, count in sorted(type_counts.items())) + "\n"
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
        body += f"- Resource group: `{app.get('resourceGroup')}`\n"
        body += f"- Location: `{app.get('location')}`\n"
        body += f"- State: `{app.get('state')}`\n"
        body += f"- Runtime: `{runtime.get('name', '')} {runtime.get('version', '')}`\n"
        body += f"- SKU: `{app.get('sku')}`\n"
        body += f"- HTTPS only: `{app.get('httpsOnly')}`\n"
        body += f"- Public network access: `{app.get('publicNetworkAccess')}`\n"
        body += f"- Storage deployment type: `{storage.get('type')}`\n"
        body += f"- Maximum instances: `{scale.get('maximumInstanceCount')}`\n"
        body += f"- Identity type: `{identity.get('type')}`\n"
        body += f"- User-assigned identities: `{len(user_assigned)}`\n"
        if app.get("serverFarmId"):
            body += f"- App Service plan: `{app.get('serverFarmId')}`\n"
        if app.get("virtualNetworkSubnetId"):
            body += f"- VNet subnet: `{app.get('virtualNetworkSubnetId')}`\n"
        if app.get("id"):
            body += f"- ID: `{app.get('id')}`\n"
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
    for setting in settings:
        key = setting.get("name")
        value = setting.get("value") if show_values else "[REDACTED]"
        body += f"- `{key}`: `{value}`\n"
    return body


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
