from assurance_cli.atlassian.confluence import build_cql, page_id_from_url
from assurance_cli.atlassian.jira import build_jql


def test_confluence_cql_simple_query_with_space() -> None:
    assert build_cql("Dataverse", cql=None, space="DSP", content_type="page") == (
        'space = DSP AND type = page AND text ~ "Dataverse" ORDER BY lastmodified DESC'
    )


def test_confluence_cql_quotes_space_names() -> None:
    assert build_cql("Dataverse", cql=None, space="Driver Service Platform - Beta", content_type="page") == (
        'space = "Driver Service Platform - Beta" AND type = page AND text ~ "Dataverse" ORDER BY lastmodified DESC'
    )


def test_confluence_page_id_from_url() -> None:
    assert page_id_from_url("https://example/wiki/spaces/DSP/pages/123456789/Page") == "123456789"


def test_jira_jql_simple_query_with_project() -> None:
    assert build_jql(
        "Dataverse",
        jql=None,
        project="ABC",
        status=None,
        issue_type=None,
        labels=(),
        components=(),
        updated_after=None,
        updated_before=None,
        order_by="updated DESC",
    ) == 'project = ABC AND text ~ "Dataverse" ORDER BY updated DESC'


def test_jira_jql_quotes_project_names_with_hyphens() -> None:
    assert build_jql(
        "Dataverse",
        jql=None,
        project="DSP-Beta",
        status=None,
        issue_type=None,
        labels=(),
        components=(),
        updated_after=None,
        updated_before=None,
        order_by="updated DESC",
    ) == 'project = "DSP-Beta" AND text ~ "Dataverse" ORDER BY updated DESC'
