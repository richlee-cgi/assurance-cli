from typer.testing import CliRunner

from assurance_cli.main import app


def test_help() -> None:
    result = CliRunner().invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "confluence" in result.output
    assert "jira" in result.output
    assert "report" in result.output


def test_azure_check_dry_run() -> None:
    result = CliRunner().invoke(app, ["azure", "check", "--dry-run"])
    assert result.exit_code == 0
    assert "Azure CLI Check" in result.output


def test_evidence_pack_help() -> None:
    result = CliRunner().invoke(app, ["report", "evidence-pack", "--help"])
    assert result.exit_code == 0
    assert "--confluence-space" in result.output
    assert "--jira-project" in result.output
    assert "--azure-resource-group" in result.output
