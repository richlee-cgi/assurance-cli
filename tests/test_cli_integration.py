from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from typer.testing import CliRunner

from assurance_cli.azure.cli import AzureCommandResult
from assurance_cli.dataverse.pac import PacCommandResult
from assurance_cli.exceptions import AssuranceError
from assurance_cli.main import _fields_with_team_field, app


def _set_atlassian_env(monkeypatch) -> None:
    monkeypatch.setenv("ATLASSIAN_BASE_URL", "https://example.atlassian.net")
    monkeypatch.setenv("ATLASSIAN_EMAIL", "user@example.com")
    monkeypatch.setenv("ATLASSIAN_API_TOKEN", "token")
    monkeypatch.setenv("ATLASSIAN_DEFAULT_CONFLUENCE_SPACE", "SPACE")
    monkeypatch.setenv("ATLASSIAN_DEFAULT_JIRA_PROJECT", "ABC")


def test_fields_with_team_field_adds_default_team_field() -> None:
    assert _fields_with_team_field("summary,status", "Team") == "summary,status,Team"


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


def test_report_evidence_pack_merges_additional_queries(monkeypatch, tmp_path: Path) -> None:
    _set_atlassian_env(monkeypatch)
    fetched_pages: list[str] = []
    fetched_issues: list[str] = []
    confluence_cqls: list[str] = []
    jira_jqls: list[str] = []

    def fake_confluence_search(**kwargs):
        confluence_cqls.append(kwargs["cql"])
        if "ADLI" in kwargs["cql"]:
            return {
                "cql": kwargs["cql"],
                "results": [
                    {"id": "456", "title": "Shared design"},
                    {"id": "789", "title": "ADLI decision"},
                ],
            }
        return {
            "cql": kwargs["cql"],
            "results": [
                {"id": "123", "title": "Delivery design"},
                {"id": "456", "title": "Shared design"},
            ],
        }

    def fake_fetch_page(**kwargs):
        fetched_pages.append(kwargs["page_id"])
        return {"page": _confluence_page_payload(kwargs["page_id"])}

    def fake_jira_search(**kwargs):
        jira_jqls.append(kwargs["jql"])
        if "ADLI" in kwargs["jql"]:
            return {"jql": kwargs["jql"], "issues": [{"key": "ABC-456"}, {"key": "ABC-789"}]}
        return {"jql": kwargs["jql"], "issues": [{"key": "ABC-123"}, {"key": "ABC-456"}]}

    def fake_fetch_issue(**kwargs):
        fetched_issues.append(kwargs["issue_key"])
        return _jira_issue_payload(kwargs["issue_key"])

    monkeypatch.setattr("assurance_cli.main._fetch_confluence_search", fake_confluence_search)
    monkeypatch.setattr("assurance_cli.main._fetch_confluence_page", fake_fetch_page)
    monkeypatch.setattr("assurance_cli.main._fetch_jira_search", fake_jira_search)
    monkeypatch.setattr("assurance_cli.main._fetch_jira_issue", fake_fetch_issue)
    output = tmp_path / "pack.md"

    result = CliRunner().invoke(
        app,
        [
            "report",
            "evidence-pack",
            "dvla result",
            "--query",
            "ADLI",
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
    assert len(confluence_cqls) == 2
    assert len(jira_jqls) == 2
    assert fetched_pages == ["123", "456", "789"]
    assert fetched_issues == ["ABC-123", "ABC-456", "ABC-789"]
    assert "- `dvla result`" in text
    assert "- `ADLI`" in text
    assert "Results from repeated source searches are merged and deduplicated" in text
    assert text.count("## ABC-456: Booking work") == 1


def test_report_evidence_pack_applies_configured_exclusions(monkeypatch, tmp_path: Path) -> None:
    _set_atlassian_env(monkeypatch)

    monkeypatch.setattr(
        "assurance_cli.main._fetch_confluence_search",
        lambda **kwargs: {
            "cql": kwargs["cql"],
            "results": [
                {"id": "123", "title": "Product architecture", "ancestors": []},
                {"id": "456", "title": "Assurance notes", "ancestors": [{"id": "983238177"}]},
            ],
        },
    )
    monkeypatch.setattr("assurance_cli.main._fetch_confluence_page", lambda **kwargs: {"page": _confluence_page_payload(kwargs["page_id"])})
    monkeypatch.setattr(
        "assurance_cli.main._fetch_jira_search",
        lambda **kwargs: {"jql": kwargs["jql"], "issues": [{"key": "ABC-123"}, {"key": "ABC-456"}]},
    )

    def fake_fetch_issue(**kwargs):
        issue = _jira_issue_payload(kwargs["issue_key"])
        if kwargs["issue_key"] == "ABC-456":
            issue["fields"]["customfield_12345"] = {"value": "DSP Assurance"}
            issue["fields"]["summary"] = "Assurance process ticket"
        else:
            issue["fields"]["customfield_12345"] = {"value": "Product Team"}
        return issue

    monkeypatch.setattr("assurance_cli.main._fetch_jira_issue", fake_fetch_issue)
    output = tmp_path / "pack.md"

    result = CliRunner().invoke(
        app,
        [
            "report",
            "evidence-pack",
            "booking",
            "--confluence-space",
            "SPACE",
            "--jira-project",
            "ABC",
            "--exclude-confluence-parent",
            "983238177",
            "--jira-team-field",
            "customfield_12345",
            "--exclude-jira-team",
            "DSP Assurance",
            "--out",
            str(output),
        ],
    )

    text = output.read_text(encoding="utf-8")
    assert result.exit_code == 0
    assert "Excluded Confluence results: `1`" in text
    assert "Excluded Jira issues: `1`" in text
    assert "Confluence parent exclusions: `983238177`" in text
    assert "Jira team exclusions: `DSP Assurance`" in text
    assert "ABC-123" in text
    assert "ABC-456" not in text


def test_code_repos_and_search_cli(tmp_path: Path) -> None:
    repo = tmp_path / "booking-service"
    repo.mkdir()
    (repo / "README.md").write_text("Booking allocation evidence.\n", encoding="utf-8")
    subprocess_result = subprocess.run(["git", "init", str(repo)], capture_output=True, text=True)
    assert subprocess_result.returncode == 0

    repos_result = CliRunner().invoke(app, ["code", "repos", "--repo-root", str(tmp_path)])
    search_result = CliRunner().invoke(app, ["code", "search", "Booking", "--repo-root", str(tmp_path), "--repo", "booking-service"])

    assert repos_result.exit_code == 0
    assert "booking-service" in repos_result.output
    assert search_result.exit_code == 0
    assert "Code Evidence" in search_result.output
    assert "README.md" in search_result.output


def test_report_evidence_pack_includes_code(monkeypatch, tmp_path: Path) -> None:
    _set_atlassian_env(monkeypatch)
    repo = tmp_path / "booking-service"
    repo.mkdir()
    (repo / "app.py").write_text("booking allocation implementation\n", encoding="utf-8")
    subprocess_result = subprocess.run(["git", "init", str(repo)], capture_output=True, text=True)
    assert subprocess_result.returncode == 0
    output = tmp_path / "pack.md"

    result = CliRunner().invoke(
        app,
        [
            "report",
            "evidence-pack",
            "booking",
            "--skip-confluence",
            "--skip-jira",
            "--include-code",
            "--repo-root",
            str(tmp_path),
            "--repo",
            "booking-service",
            "--out",
            str(output),
        ],
    )

    text = output.read_text(encoding="utf-8")
    assert result.exit_code == 0
    assert "Code: `yes`" in text
    assert "booking-service" in text
    assert "app.py" in text


def test_report_evidence_pack_code_only_does_not_require_atlassian_env(monkeypatch, tmp_path: Path) -> None:
    for name in ("ATLASSIAN_BASE_URL", "ATLASSIAN_EMAIL", "ATLASSIAN_API_TOKEN"):
        monkeypatch.delenv(name, raising=False)
    repo = tmp_path / "booking-service"
    repo.mkdir()
    (repo / "app.py").write_text("booking allocation implementation\n", encoding="utf-8")
    subprocess_result = subprocess.run(["git", "init", str(repo)], capture_output=True, text=True)
    assert subprocess_result.returncode == 0
    output = tmp_path / "pack.md"

    result = CliRunner().invoke(
        app,
        [
            "report",
            "evidence-pack",
            "booking",
            "--skip-confluence",
            "--skip-jira",
            "--include-code",
            "--repo-root",
            str(tmp_path),
            "--repo",
            "booking-service",
            "--out",
            str(output),
        ],
    )

    text = output.read_text(encoding="utf-8")
    assert result.exit_code == 0
    assert "Code: `yes`" in text
    assert "booking-service" in text


def test_report_evidence_pack_code_only_uses_pr_topic(monkeypatch, tmp_path: Path) -> None:
    for name in ("ATLASSIAN_BASE_URL", "ATLASSIAN_EMAIL", "ATLASSIAN_API_TOKEN"):
        monkeypatch.delenv(name, raising=False)
    repo = tmp_path / "booking-service"
    repo.mkdir()
    (repo / "README.md").write_text("booking allocation implementation\n", encoding="utf-8")
    subprocess_result = subprocess.run(["git", "init", str(repo)], capture_output=True, text=True)
    assert subprocess_result.returncode == 0
    output = tmp_path / "pack.md"

    class FakePr:
        url = "https://github.com/org/repo/pull/123"
        title = "Booking PR"
        state = "OPEN"
        author = "alice"
        head_ref = "feature"
        base_ref = "main"
        merge_state = "BLOCKED"
        changed_files = 3
        diff = "diff --git a/README.md b/README.md"
        diff_truncated = False
        error = ""

    monkeypatch.setattr("assurance_cli.main.get_pull_request_evidence", lambda *args, **kwargs: FakePr())

    result = CliRunner().invoke(
        app,
        [
            "report",
            "evidence-pack",
            "https://github.com/org/repo/pull/123",
            "--skip-confluence",
            "--skip-jira",
            "--include-code",
            "--repo-root",
            str(tmp_path),
            "--repo",
            "booking-service",
            "--include-prs",
            "--include-diffs",
            "--out",
            str(output),
        ],
    )

    text = output.read_text(encoding="utf-8")
    assert result.exit_code == 0
    assert "Booking PR" in text
    assert "diff --git" in text


def test_code_pr_cli_uses_mocked_github(monkeypatch, tmp_path: Path) -> None:
    repo = tmp_path / "booking-service"
    repo.mkdir()
    (repo / "README.md").write_text("https://github.com/org/repo/pull/123\n", encoding="utf-8")
    subprocess_result = subprocess.run(["git", "init", str(repo)], capture_output=True, text=True)
    assert subprocess_result.returncode == 0

    class FakePr:
        url = "https://github.com/org/repo/pull/123"
        title = "Booking PR"
        state = "MERGED"
        author = "alice"
        head_ref = "feature"
        base_ref = "main"
        merge_state = "CLEAN"
        changed_files = 2
        diff = ""
        diff_truncated = False
        error = ""

    monkeypatch.setattr("assurance_cli.main.get_pull_request_evidence", lambda *args, **kwargs: FakePr())

    result = CliRunner().invoke(
        app,
        [
            "code",
            "pr",
            "https://github.com/org/repo/pull/123",
            "--repo-root",
            str(tmp_path),
            "--repo",
            "booking-service",
        ],
    )

    assert result.exit_code == 0
    assert "Booking PR" in result.output
    assert "MERGED" in result.output
    assert "booking-service" in result.output
    assert "README.md" in result.output


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
