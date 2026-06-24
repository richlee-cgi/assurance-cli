import httpx
import respx

from assurance_cli.atlassian.client import AtlassianClient
from assurance_cli.atlassian.confluence import search_confluence
from assurance_cli.atlassian.jira import get_issue, search_jira
from assurance_cli.config import AtlassianConfig


def _client() -> AtlassianClient:
    return AtlassianClient(
        AtlassianConfig(
            base_url="https://example.atlassian.net",
            email="user@example.com",
            api_token="token",
            default_confluence_space=None,
            default_jira_project=None,
            page_size=2,
            max_results=10,
        )
    )


@respx.mock
def test_confluence_search_pages_through_mocked_http() -> None:
    first = respx.get("https://example.atlassian.net/wiki/rest/api/content/search").mock(
        side_effect=[
            httpx.Response(200, json={"results": [{"id": "1"}, {"id": "2"}]}),
            httpx.Response(200, json={"results": [{"id": "3"}]}),
        ]
    )
    client = _client()

    try:
        result = search_confluence(client, cql="type = page", limit=3, expand="space", page_size=2)
    finally:
        client.close()

    assert [item["id"] for item in result["results"]] == ["1", "2", "3"]
    assert first.call_count == 2


@respx.mock
def test_jira_search_pages_through_mocked_http() -> None:
    route = respx.get("https://example.atlassian.net/rest/api/3/search/jql").mock(
        side_effect=[
            httpx.Response(200, json={"issues": [{"key": "ABC-1"}, {"key": "ABC-2"}], "nextPageToken": "next"}),
            httpx.Response(200, json={"issues": [{"key": "ABC-3"}]}),
        ]
    )
    client = _client()

    try:
        result = search_jira(client, jql="project = ABC", fields="key,summary", limit=3, page_size=2)
    finally:
        client.close()

    assert [item["key"] for item in result["issues"]] == ["ABC-1", "ABC-2", "ABC-3"]
    assert route.call_count == 2


@respx.mock
def test_jira_get_issue_includes_comments_from_mocked_http() -> None:
    respx.get("https://example.atlassian.net/rest/api/3/issue/ABC-1").mock(
        return_value=httpx.Response(200, json={"key": "ABC-1", "fields": {"summary": "Example"}})
    )
    comments = respx.get("https://example.atlassian.net/rest/api/3/issue/ABC-1/comment").mock(
        return_value=httpx.Response(200, json={"comments": [{"id": "10000"}]})
    )
    client = _client()

    try:
        issue = get_issue(client, issue_key="ABC-1", fields="key,summary", include_comments=True, include_changelog=False)
    finally:
        client.close()

    assert issue["comment"]["comments"][0]["id"] == "10000"
    assert comments.called
