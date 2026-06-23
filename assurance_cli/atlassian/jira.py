from __future__ import annotations

from typing import Any

from assurance_cli.atlassian.client import AtlassianClient


DEFAULT_FIELDS = (
    "summary,status,issuetype,priority,assignee,reporter,updated,created,labels,"
    "components,fixVersions,description,parent,issuelinks"
)


def build_jql(
    query: str | None,
    *,
    jql: str | None,
    project: str | None,
    status: str | None,
    issue_type: str | None,
    labels: tuple[str, ...],
    components: tuple[str, ...],
    updated_after: str | None,
    updated_before: str | None,
    order_by: str,
) -> str:
    if jql:
        return jql
    clauses = []
    if project:
        clauses.append(f"project = {_quote_jql_value(project)}")
    if query:
        escaped = query.replace('"', r'\"')
        clauses.append(f'text ~ "{escaped}"')
    if status:
        clauses.append(f'status = "{status}"')
    if issue_type:
        clauses.append(f'issuetype = "{issue_type}"')
    for label in labels:
        clauses.append(f"labels = {label}")
    for component in components:
        clauses.append(f'component = "{component}"')
    if updated_after:
        clauses.append(f'updated >= "{updated_after}"')
    if updated_before:
        clauses.append(f'updated <= "{updated_before}"')
    base = " AND ".join(clauses) if clauses else "ORDER BY updated DESC"
    if "ORDER BY" not in base.upper():
        base = f"{base} ORDER BY {order_by}"
    return base


def search_jira(
    client: AtlassianClient,
    *,
    jql: str,
    fields: str,
    limit: int,
    page_size: int,
) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    next_page_token: str | None = None
    while len(issues) < limit:
        max_results = min(page_size, limit - len(issues))
        data = client.get(
            "/rest/api/3/search/jql",
            params={
                "jql": jql,
                "fields": fields,
                "maxResults": max_results,
                "nextPageToken": next_page_token,
            },
        )
        batch = data.get("issues", [])
        issues.extend(batch)
        next_page_token = data.get("nextPageToken")
        if len(batch) < max_results or not next_page_token:
            break
    return {"jql": jql, "issues": issues[:limit]}


def get_issue(
    client: AtlassianClient,
    *,
    issue_key: str,
    fields: str,
    include_comments: bool,
    include_changelog: bool,
) -> dict[str, Any]:
    expand = []
    if include_changelog:
        expand.append("changelog")
    data = client.get(
        f"/rest/api/3/issue/{issue_key}",
        params={"fields": fields, "expand": ",".join(expand) if expand else None},
    )
    if include_comments:
        comments = client.get(f"/rest/api/3/issue/{issue_key}/comment", params={"orderBy": "-created", "maxResults": 100})
        data["comment"] = comments
    return data


def _quote_jql_value(value: str) -> str:
    if value.replace("_", "").isalnum():
        return value
    return '"' + value.replace('"', r'\"') + '"'
