from __future__ import annotations

from pathlib import Path
from typing import Any

from typer.testing import CliRunner

from assurance_cli.azure.cli import AzureCommandResult
from assurance_cli.dataverse.pac import PacCommandResult
from assurance_cli.exceptions import AssuranceError
from assurance_cli.main import app


def _set_atlassian_env(monkeypatch) -> None:
    monkeypatch.setenv("ATLASSIAN_BASE_URL", "https://example.atlassian.net")
    monkeypatch.setenv("ATLASSIAN_EMAIL", "user@example.com")
    monkeypatch.setenv("ATLASSIAN_API_TOKEN", "token")
    monkeypatch.setenv("ATLASSIAN_DEFAULT_CONFLUENCE_SPACE", "SPACE")
    monkeypatch.setenv("ATLASSIAN_DEFAULT_JIRA_PROJECT", "ABC")


def _confluence_search_payload() -> dict[str, Any]:
    return {
        "results": [
            {
                "id": "123",
                "title": "Architecture",
                "space": {"key": "SPACE"},
                "version": {"when": "2026-01-01T00:00:00Z"},
                "_links": {"webui": "/wiki/spaces/SPACE/pages/123/Architecture"},
            }
        ]
    }


def _confluence_page_payload(page_id: str = "123") -> dict[str, Any]:
    return {
        "id": page_id,
        "title": "Architecture",
        "space": {"key": "SPACE"},
        "version": {"when": "2026-01-01T00:00:00Z"},
        "_links": {"webui": f"/wiki/spaces/SPACE/pages/{page_id}/Architecture"},
        "body": {"storage": {"value": "<p>System architecture evidence.</p>"}},
        "metadata": {"labels": {"results": [{"name": "assurance"}]}},
    }


def _jira_search_payload() -> dict[str, Any]:
    return {"issues": [{"key": "ABC-123", "fields": {"summary": "Booking work"}}]}


def _jira_issue_payload(issue_key: str = "ABC-123") -> dict[str, Any]:
    return {
        "key": issue_key,
        "fields": {
            "summary": "Booking work",
            "status": {"name": "Done"},
            "issuetype": {"name": "Story"},
            "priority": {"name": "Medium"},
            "assignee": {"displayName": "Example Assignee"},
            "reporter": {"displayName": "Example Reporter"},
            "updated": "2026-01-02T00:00:00Z",
            "labels": ["assurance"],
            "components": [{"name": "api"}],
            "description": {"type": "doc", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Jira evidence."}]}]},
            "issuelinks": [],
        },
    }


def test_confluence_get_cli_uses_mocked_fetch(monkeypatch, tmp_path: Path) -> None:
    _set_atlassian_env(monkeypatch)

    def fake_fetch_page(**kwargs):
        assert kwargs["page_id"] == "123"
        return {"page": _confluence_page_payload()}

    monkeypatch.setattr("assurance_cli.main._fetch_confluence_page", fake_fetch_page)
    output = tmp_path / "page.md"

    result = CliRunner().invoke(app, ["confluence", "get", "--id", "123", "--out", str(output)])

    assert result.exit_code == 0
    assert "System architecture evidence" in output.read_text(encoding="utf-8")


def test_jira_get_cli_uses_mocked_fetch(monkeypatch) -> None:
    _set_atlassian_env(monkeypatch)

    def fake_fetch_issue(**kwargs):
        assert kwargs["include_comments"] is True
        return {
            **_jira_issue_payload(),
            "comment": {
                "comments": [
                    {
                        "author": {"displayName": "Reviewer"},
                        "created": "2026-01-03",
                        "body": {"type": "doc", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Looks good."}]}]},
                    }
                ]
            },
        }

    monkeypatch.setattr("assurance_cli.main._fetch_jira_issue", fake_fetch_issue)

    result = CliRunner().invoke(app, ["jira", "get", "ABC-123", "--include-comments"])

    assert result.exit_code == 0
    assert "ABC-123: Booking work" in result.output
    assert "Looks good." in result.output


def test_report_evidence_pack_with_preset_uses_mocked_sources(monkeypatch, tmp_path: Path) -> None:
    _set_atlassian_env(monkeypatch)

    monkeypatch.setattr(
        "assurance_cli.main._fetch_confluence_search",
        lambda **kwargs: {"cql": kwargs["cql"], **_confluence_search_payload()},
    )
    monkeypatch.setattr("assurance_cli.main._fetch_confluence_page", lambda **kwargs: {"page": _confluence_page_payload(kwargs["page_id"])})
    monkeypatch.setattr("assurance_cli.main._fetch_jira_search", lambda **kwargs: {"jql": kwargs["jql"], **_jira_search_payload()})
    monkeypatch.setattr("assurance_cli.main._fetch_jira_issue", lambda **kwargs: _jira_issue_payload(kwargs["issue_key"]))
    monkeypatch.setattr(
        "assurance_cli.main._azure_topic_evidence_markdown",
        lambda **kwargs: ("# Azure Evidence\n\n| Name | Type |\n| --- | --- |\n| app | Microsoft.Web/sites |\n", None),
    )
    output = tmp_path / "pack.md"

    result = CliRunner().invoke(
        app,
        [
            "report",
            "evidence-pack",
            "--preset",
            "architecture",
            "--confluence-space",
            "SPACE",
            "--jira-project",
            "ABC",
            "--out",
            str(output),
        ],
    )

    text = output.read_text(encoding="utf-8")
    assert result.exit_code == 0
    assert "Evidence Pack" in text
    assert "System architecture evidence" in text
    assert "Jira evidence." in text
    assert "Microsoft.Web/sites" in text


def test_azure_resource_search_cli_uses_mocked_runner(monkeypatch) -> None:
    def fake_run(command: list[str], *, dry_run: bool = False) -> AzureCommandResult:
        assert command[:3] == ["az", "graph", "query"]
        return AzureCommandResult(
            command=[*command, "-o", "json"],
            data={"data": [{"name": "app", "type": "Microsoft.Web/sites", "resourceGroup": "rg", "location": "uksouth"}]},
            stderr="",
        )

    monkeypatch.setattr("assurance_cli.main.run_az_json", fake_run)

    result = CliRunner().invoke(app, ["azure", "resource-search", "app", "--resource-group", "rg", "--limit", "5"])

    assert result.exit_code == 0
    assert "Azure Resource Search" in result.output
    assert "| app | Microsoft.Web/sites | rg | uksouth |" in result.output


def test_azure_functions_cli_fetches_settings_with_mocked_runner(monkeypatch) -> None:
    calls: list[list[str]] = []

    def fake_run(command: list[str], *, dry_run: bool = False) -> AzureCommandResult:
        calls.append(command)
        if command[:3] == ["az", "functionapp", "list"]:
            return AzureCommandResult(
                command=[*command, "-o", "json"],
                data=[{"name": "func", "resourceGroup": "rg", "functionAppConfig": {"runtime": {"name": "python", "version": "3.12"}}}],
                stderr="",
            )
        return AzureCommandResult(command=[*command, "-o", "json"], data=[{"name": "SECRET", "value": "hidden"}], stderr="")

    monkeypatch.setattr("assurance_cli.main.run_az_json", fake_run)

    result = CliRunner().invoke(app, ["azure", "functions", "--resource-group", "rg", "--include-settings"])

    assert result.exit_code == 0
    assert ["az", "functionapp", "config", "appsettings", "list", "--name", "func", "--resource-group", "rg"] in calls
    assert "| Runtime | python 3.12 |" in result.output
    assert "hidden" not in result.output


def test_dataverse_solutions_cli_uses_mocked_runner(monkeypatch) -> None:
    def fake_run(command: list[str], *, dry_run: bool = False) -> PacCommandResult:
        assert command == ["pac", "solution", "list", "--environment", "https://example.crm11.dynamics.com"]
        return PacCommandResult(
            command=command,
            data=[{"DisplayName": "Core", "Version": "1.0.0"}],
            stdout="",
            stderr="",
            parsed_json=True,
        )

    monkeypatch.setattr("assurance_cli.main.run_pac", fake_run)

    result = CliRunner().invoke(app, ["dataverse", "solutions", "--environment", "https://example.crm11.dynamics.com"])

    assert result.exit_code == 0
    assert "Dataverse Solutions" in result.output
    assert "| Core | 1.0.0 |" in result.output


def test_dataverse_snapshot_cli_handles_mocked_subprocess_warning(monkeypatch) -> None:
    def fake_run(command: list[str], *, dry_run: bool = False) -> PacCommandResult:
        if command == ["pac", "connector", "list"]:
            raise AssuranceError("connector list failed")
        return PacCommandResult(command=command, data=[{"DisplayName": command[1]}], stdout="", stderr="", parsed_json=True)

    monkeypatch.setattr("assurance_cli.main.run_pac", fake_run)

    result = CliRunner().invoke(app, ["dataverse", "snapshot"])

    assert result.exit_code == 0
    assert "connector list failed" in result.output
    assert "Dataverse Snapshot" in result.output
