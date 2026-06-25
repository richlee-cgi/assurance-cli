from __future__ import annotations

from typing import Any

from assurance_cli.atlassian.markdown import confluence_page_markdown, jira_issue_markdown
from assurance_cli.markdown import document_header


def confluence_evidence_pack_markdown(
    *,
    topic: str,
    cql: str,
    search_results: dict[str, Any],
    pages: list[dict[str, Any]],
    base_url: str,
    max_page_chars: int,
) -> str:
    body = document_header(
        f"Confluence Evidence Pack: {topic}",
        "Confluence",
        "assurance confluence evidence-pack",
        cql,
    )
    body += "## Search Summary\n\n"
    body += f"- Topic: `{topic}`\n"
    body += f"- CQL: `{cql}`\n"
    body += f"- Pages retrieved: `{len(pages)}` of `{len(search_results.get('results', []))}` search results\n\n"
    body += "## Confluence Evidence\n\n"
    if not pages:
        body += "_No Confluence pages found._\n"
        return body
    body += "\n".join(
        confluence_page_markdown(page, base_url, max_page_chars).strip()
        for page in pages
    )
    body += "\n"
    return body


def jira_evidence_pack_markdown(
    *,
    topic: str,
    jql: str,
    search_results: dict[str, Any],
    issues: list[dict[str, Any]],
    base_url: str,
    comment_limit: int,
) -> str:
    body = document_header(
        f"Jira Evidence Pack: {topic}",
        "Jira",
        "assurance jira evidence-pack",
        jql,
    )
    body += "## Search Summary\n\n"
    body += f"- Topic: `{topic}`\n"
    body += f"- JQL: `{jql}`\n"
    body += f"- Issues retrieved: `{len(issues)}` of `{len(search_results.get('issues', []))}` search results\n\n"
    body += jira_status_summary(issues)
    body += "\n## Jira Evidence\n\n"
    if not issues:
        body += "_No Jira issues found._\n"
        return body
    body += "\n".join(jira_issue_markdown(issue, base_url, comment_limit).strip() for issue in issues)
    body += "\n"
    return body


def combined_evidence_pack_markdown(
    *,
    topic: str,
    confluence_markdown: str | None,
    jira_markdown: str | None,
    azure_markdown: str | None,
    dataverse_markdown: str | None,
    code_markdown: str | None,
    azure_requested: bool,
    dataverse_requested: bool,
    code_requested: bool,
    gaps: list[str],
) -> str:
    body = document_header(
        f"Evidence Pack: {topic}",
        "Confluence/Jira/Azure/Dataverse/Code",
        "assurance report evidence-pack",
        topic,
    )
    body += "## Scope\n\n"
    body += f"- Topic: `{topic}`\n\n"
    body += "## Sources Queried\n\n"
    body += f"- Confluence: `{'yes' if confluence_markdown is not None else 'no'}`\n"
    body += f"- Jira: `{'yes' if jira_markdown is not None else 'no'}`\n"
    body += f"- Azure: `{'yes' if azure_markdown is not None else ('requested, no evidence returned' if azure_requested else 'no')}`\n"
    body += f"- Dataverse: `{'yes' if dataverse_markdown is not None else ('requested, no evidence returned' if dataverse_requested else 'no')}`\n"
    body += f"- Code: `{'yes' if code_markdown is not None else ('requested, no evidence returned' if code_requested else 'no')}`\n\n"
    body += "## Confluence Evidence\n\n"
    body += _strip_embedded_header(confluence_markdown) if confluence_markdown else "_Not queried._\n"
    body += "\n## Jira Evidence\n\n"
    body += _strip_embedded_header(jira_markdown) if jira_markdown else "_Not queried._\n"
    body += "\n## Azure Evidence\n\n"
    body += _strip_embedded_header(azure_markdown) if azure_markdown else ("_No Azure evidence returned._\n" if azure_requested else "_Not requested._\n")
    body += "\n## Dataverse Evidence\n\n"
    body += _strip_embedded_header(dataverse_markdown) if dataverse_markdown else ("_No Dataverse evidence returned._\n" if dataverse_requested else "_Not requested._\n")
    body += "\n## Code Evidence\n\n"
    body += _strip_embedded_header(code_markdown) if code_markdown else ("_No code evidence returned._\n" if code_requested else "_Not requested._\n")
    body += "\n## Gaps / Follow-up Questions\n\n"
    if gaps:
        body += "\n".join(f"- {gap}" for gap in gaps) + "\n"
    else:
        body += "_No mechanical gaps identified by the retrieval commands._\n"
    body += "\n## Appendix: Commands Run\n\n"
    body += "- `assurance confluence evidence-pack ...`\n" if confluence_markdown is not None else ""
    body += "- `assurance jira evidence-pack ...`\n" if jira_markdown is not None else ""
    body += "- `assurance azure resource-search ...`\n" if azure_markdown is not None else ""
    body += "- `assurance dataverse snapshot`\n" if dataverse_markdown is not None else ""
    body += "- `assurance code search ...`\n" if code_markdown is not None else ""
    return body


def jira_status_summary(issues: list[dict[str, Any]]) -> str:
    counts: dict[str, int] = {}
    for issue in issues:
        status = issue.get("fields", {}).get("status", {}).get("name") or "Unknown"
        counts[status] = counts.get(status, 0) + 1
    if not counts:
        return "## Status Summary\n\n_No issues to summarise._\n"
    lines = ["## Status Summary", ""]
    for status, count in sorted(counts.items()):
        lines.append(f"- `{status}`: {count}")
    return "\n".join(lines) + "\n"


def _strip_embedded_header(markdown: str | None) -> str:
    if not markdown:
        return ""
    marker = "\n---\n\n"
    if marker in markdown:
        return markdown.split(marker, 1)[1]
    return markdown
