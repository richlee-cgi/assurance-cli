from __future__ import annotations

from typing import Any

from assurance_cli.markdown import adf_to_markdown, html_to_md


def confluence_search_markdown(data: dict[str, Any], base_url: str) -> str:
    lines = []
    for item in data.get("results", []):
        lines.append(_confluence_page_summary(item, base_url))
    return "\n".join(lines) or "_No Confluence pages found._\n"


def confluence_page_markdown(data: dict[str, Any], base_url: str, max_body_chars: int) -> str:
    page = data["page"]
    lines = [_confluence_page_summary(page, base_url)]
    body = _page_body(page, base_url)
    if max_body_chars and len(body) > max_body_chars:
        body = body[:max_body_chars].rstrip() + "\n\n_[Body truncated]_"
    if body:
        lines.extend(["### Body", body])
    labels = page.get("metadata", {}).get("labels", {}).get("results", [])
    if labels:
        lines.append("### Labels\n\n" + ", ".join(f"`{label.get('name')}`" for label in labels))
    if "attachments" in data:
        lines.append("### Attachments\n\n" + _simple_child_list(data["attachments"]))
    if "children" in data:
        lines.append("### Children\n\n" + _simple_child_list(data["children"]))
    if "comments" in data:
        lines.append("### Comments\n\n" + _simple_child_list(data["comments"]))
    return "\n\n".join(lines).strip() + "\n"


def jira_search_markdown(data: dict[str, Any], base_url: str) -> str:
    lines = []
    for issue in data.get("issues", []):
        lines.append(_jira_issue_summary(issue, base_url, include_description=True))
    return "\n".join(lines) or "_No Jira issues found._\n"


def jira_issue_markdown(issue: dict[str, Any], base_url: str, comment_limit: int) -> str:
    lines = [_jira_issue_summary(issue, base_url, include_description=True)]
    comments = issue.get("comment", {}).get("comments", [])
    if comments:
        rendered = []
        for comment in comments[:comment_limit]:
            author = comment.get("author", {}).get("displayName", "Unknown")
            created = comment.get("created", "")
            body = adf_to_markdown(comment.get("body")).strip() or "_No comment body._"
            rendered.append(f"#### {author} - {created}\n\n{body}")
        lines.append("### Comments\n\n" + "\n\n".join(rendered))
    links = issue.get("fields", {}).get("issuelinks", [])
    if links:
        rendered_links = []
        for link in links:
            link_type = link.get("type", {}).get("name", "Linked")
            other = link.get("outwardIssue") or link.get("inwardIssue") or {}
            if other:
                rendered_links.append(f"- `{link_type}`: `{other.get('key')}` {other.get('fields', {}).get('summary', '')}")
        if rendered_links:
            lines.append("### Linked Issues\n\n" + "\n".join(rendered_links))
    return "\n\n".join(lines).strip() + "\n"


def _confluence_page_summary(item: dict[str, Any], base_url: str) -> str:
    title = item.get("title", "Untitled")
    space = item.get("space", {}).get("key", "")
    page_id = item.get("id", "")
    updated = item.get("version", {}).get("when") or item.get("history", {}).get("lastUpdated", {}).get("when", "")
    webui = item.get("_links", {}).get("webui")
    url = f"{base_url}{webui}" if webui else f"{base_url}/wiki/pages/{page_id}"
    excerpt = html_to_md(item.get("excerpt"))
    lines = [
        f"## {title}",
        "",
        f"- Space: `{space}`",
        "- Type: `page`",
        f"- Updated: `{updated}`",
        f"- URL: {url}",
        f"- ID: `{page_id}`",
    ]
    ancestors = item.get("ancestors", [])
    if ancestors:
        lines.append("- Ancestors: " + " / ".join(a.get("title", "") for a in ancestors if a.get("title")))
    if excerpt:
        lines.extend(["", "### Excerpt", "", excerpt])
    return "\n".join(lines)


def _page_body(page: dict[str, Any], base_url: str) -> str:
    body = page.get("body", {})
    for key in ("storage", "view", "export_view", "anonymous_export_view"):
        value = body.get(key, {}).get("value")
        if value:
            return html_to_md(value, base_url=base_url)
    return ""


def _simple_child_list(data: dict[str, Any]) -> str:
    results = data.get("results", [])
    if not results:
        return "_None found._"
    return "\n".join(f"- {item.get('title') or item.get('id')}" for item in results)


def _jira_issue_summary(issue: dict[str, Any], base_url: str, *, include_description: bool) -> str:
    fields = issue.get("fields", {})
    key = issue.get("key", "")
    summary = fields.get("summary", "")
    assignee = (fields.get("assignee") or {}).get("displayName") or "Unassigned"
    components = ", ".join(f"`{c.get('name')}`" for c in fields.get("components", []) or []) or "None"
    labels = ", ".join(f"`{label}`" for label in fields.get("labels", []) or []) or "None"
    lines = [
        f"## {key}: {summary}",
        "",
        f"- Status: `{(fields.get('status') or {}).get('name', '')}`",
        f"- Type: `{(fields.get('issuetype') or {}).get('name', '')}`",
        f"- Priority: `{(fields.get('priority') or {}).get('name', '')}`",
        f"- Assignee: `{assignee}`",
        f"- Reporter: `{(fields.get('reporter') or {}).get('displayName', '')}`",
        f"- Updated: `{fields.get('updated', '')}`",
        f"- Labels: {labels}",
        f"- Components: {components}",
        f"- URL: {base_url}/browse/{key}",
    ]
    if include_description:
        description = adf_to_markdown(fields.get("description")).strip()
        lines.extend(["", "### Description", "", description or "_No description._"])
    return "\n".join(lines)
