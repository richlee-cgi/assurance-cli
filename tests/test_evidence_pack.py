from assurance_cli.reports.evidence_pack import (
    combined_evidence_pack_markdown,
    confluence_evidence_pack_markdown,
    jira_evidence_pack_markdown,
)


def test_confluence_evidence_pack_markdown() -> None:
    search = {"results": [{"id": "123", "title": "Architecture"}]}
    pages = [
        {
            "page": {
                "id": "123",
                "title": "Architecture",
                "space": {"key": "DSP"},
                "version": {"when": "2026-06-01T10:00:00Z"},
                "_links": {"webui": "/wiki/spaces/DSP/pages/123/Architecture"},
                "body": {"storage": {"value": "<p>Useful evidence</p>"}},
            }
        }
    ]

    markdown = confluence_evidence_pack_markdown(
        topic="booking",
        cql='space = DSP AND type = page AND text ~ "booking"',
        search_results=search,
        pages=pages,
        base_url="https://example.atlassian.net",
        max_page_chars=8000,
    )

    assert "# Confluence Evidence Pack: booking" in markdown
    assert "Useful evidence" in markdown
    assert "Pages retrieved: `1` of `1`" in markdown


def test_jira_evidence_pack_markdown_status_summary() -> None:
    issue = {
        "key": "ABC-123",
        "fields": {
            "summary": "Booking work",
            "status": {"name": "In Progress"},
            "issuetype": {"name": "Story"},
            "priority": {"name": "Medium"},
            "assignee": None,
            "reporter": {"displayName": "Reporter"},
            "updated": "2026-06-01T10:00:00Z",
            "labels": ["architecture"],
            "components": [{"name": "Booking"}],
            "description": {
                "type": "doc",
                "content": [{"type": "paragraph", "content": [{"type": "text", "text": "ADF body"}]}],
            },
        },
    }

    markdown = jira_evidence_pack_markdown(
        topic="booking",
        jql='project = ABC AND text ~ "booking"',
        search_results={"issues": [{"key": "ABC-123"}]},
        issues=[issue],
        base_url="https://example.atlassian.net",
        comment_limit=5,
    )

    assert "# Jira Evidence Pack: booking" in markdown
    assert "- `In Progress`: 1" in markdown
    assert "ABC-123: Booking work" in markdown


def test_combined_evidence_pack_markdown_gaps() -> None:
    markdown = combined_evidence_pack_markdown(
        topic="booking",
        confluence_markdown="# Embedded\n\n---\n\n## Confluence Evidence\n",
        jira_markdown=None,
        azure_markdown="# Azure\n\n---\n\n## Azure Resource Search\n",
        dataverse_markdown=None,
        code_markdown="# Code\n\n---\n\n### Local Repository Search\n",
        azure_requested=True,
        dataverse_requested=False,
        code_requested=True,
        gaps=["Jira was skipped."],
    )

    assert "# Evidence Pack: booking" in markdown
    assert "## Confluence Evidence" in markdown
    assert "## Azure Resource Search" in markdown
    assert "### Local Repository Search" in markdown
    assert "Jira was skipped." in markdown
    assert "`yes`" in markdown


def test_combined_evidence_pack_markdown_requested_but_empty() -> None:
    markdown = combined_evidence_pack_markdown(
        topic="booking",
        confluence_markdown=None,
        jira_markdown=None,
        azure_markdown=None,
        dataverse_markdown=None,
        code_markdown=None,
        azure_requested=True,
        dataverse_requested=True,
        code_requested=True,
        gaps=[],
    )

    assert "Azure: `requested, no evidence returned`" in markdown
    assert "Dataverse: `requested, no evidence returned`" in markdown
    assert "Code: `requested, no evidence returned`" in markdown
    assert "_No Azure evidence returned._" in markdown
    assert "_No Dataverse evidence returned._" in markdown
    assert "_No code evidence returned._" in markdown
