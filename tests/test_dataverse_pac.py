import pytest

from assurance_cli.dataverse.markdown import dataverse_check_markdown, render_pac_payload
from assurance_cli.dataverse.pac import validate_pac_command
from assurance_cli.exceptions import UnsafeCommandError


def test_validate_allows_read_only_pac_command() -> None:
    validate_pac_command(["pac", "auth", "list"])


def test_validate_blocks_mutating_pac_command() -> None:
    with pytest.raises(UnsafeCommandError):
        validate_pac_command(["pac", "solution", "import", "--path", "solution.zip"])


def test_validate_blocks_unlisted_pac_command() -> None:
    with pytest.raises(UnsafeCommandError):
        validate_pac_command(["pac", "admin", "list"])


def test_render_pac_payload_text_fallback() -> None:
    markdown = render_pac_payload("No profiles were found")
    assert "```text" in markdown
    assert "No profiles were found" in markdown


def test_render_pac_payload_dict_list() -> None:
    markdown = render_pac_payload([{"DisplayName": "QA", "EnvironmentId": "123", "Url": "https://example"}])
    assert "| DisplayName | EnvironmentId | Url |" in markdown
    assert "| QA | 123 | https://example |" in markdown


def test_render_pac_payload_preserves_complex_values() -> None:
    markdown = render_pac_payload([{"DisplayName": "QA", "Settings": {"enabled": True}}])

    assert "Complex Values" in markdown
    assert '"enabled": true' in markdown


def test_dataverse_check_markdown() -> None:
    markdown = dataverse_check_markdown(
        pac_path="/Users/rich/.dotnet/tools/pac",
        auth_result="No profiles were found",
        command="pac auth list",
    )
    assert "# Dataverse CLI Check" in markdown
    assert "Power Platform CLI path" in markdown
