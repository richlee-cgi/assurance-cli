from __future__ import annotations

import re
from typing import Any

from assurance_cli.atlassian.client import AtlassianClient


def build_cql(
    query: str | None,
    *,
    cql: str | None,
    space: str | None,
    content_type: str,
    updated_after: str | None = None,
    updated_before: str | None = None,
) -> str:
    if cql:
        return cql
    clauses = []
    if space:
        clauses.append(f"space = {_quote_cql_value(space)}")
    clauses.append(f"type = {content_type}")
    if query:
        escaped = query.replace('"', r'\"')
        clauses.append(f'text ~ "{escaped}"')
    if updated_after:
        clauses.append(f'lastmodified >= "{updated_after}"')
    if updated_before:
        clauses.append(f'lastmodified <= "{updated_before}"')
    return " AND ".join(clauses) + " ORDER BY lastmodified DESC"


def _quote_cql_value(value: str) -> str:
    if value.replace("_", "").isalnum():
        return value
    return '"' + value.replace('"', r'\"') + '"'


def search_confluence(
    client: AtlassianClient,
    *,
    cql: str,
    limit: int,
    expand: str,
    page_size: int,
) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    start = 0
    while len(results) < limit:
        batch_limit = min(page_size, limit - len(results))
        data = client.get(
            "/wiki/rest/api/content/search",
            params={"cql": cql, "limit": batch_limit, "start": start, "expand": expand},
        )
        batch = data.get("results", [])
        results.extend(batch)
        if len(batch) < batch_limit:
            break
        start += len(batch)
    return {"cql": cql, "results": results[:limit]}


def get_page(
    client: AtlassianClient,
    *,
    page_id: str,
    body_format: str,
    include_comments: bool,
    include_children: bool,
    include_attachments: bool,
) -> dict[str, Any]:
    expand_parts = [
        f"body.{body_format}",
        "space",
        "version",
        "history",
        "ancestors",
        "metadata.labels",
    ]
    data = client.get(f"/wiki/rest/api/content/{page_id}", params={"expand": ",".join(expand_parts)})
    extras: dict[str, Any] = {}
    if include_children:
        extras["children"] = client.get(f"/wiki/rest/api/content/{page_id}/child/page", params={"limit": 100})
    if include_attachments:
        extras["attachments"] = client.get(f"/wiki/rest/api/content/{page_id}/child/attachment", params={"limit": 100})
    if include_comments:
        extras["comments"] = client.get(f"/wiki/rest/api/content/{page_id}/child/comment", params={"limit": 100})
    return {"page": data, **extras}


def page_id_from_url(url: str) -> str | None:
    patterns = [
        r"/pages/(\d+)",
        r"[?&]pageId=(\d+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None
