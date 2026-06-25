from typer.testing import CliRunner

from assurance_cli.main import app
from assurance_cli.presets import get_preset, list_presets


def test_builtin_presets_are_available() -> None:
    names = {preset.name for preset in list_presets()}

    assert {"architecture", "dataverse", "delivery", "operations", "performance", "risk"} <= names


def test_get_preset_reports_available_names() -> None:
    try:
        get_preset("missing")
    except ValueError as exc:
        assert "Available presets" in str(exc)
        assert "dataverse" in str(exc)
    else:
        raise AssertionError("Expected missing preset to raise ValueError")


def test_presets_list_command() -> None:
    result = CliRunner().invoke(app, ["presets", "list"])

    assert result.exit_code == 0
    assert "Evidence Presets" in result.output
    assert "`dataverse`" in result.output


def test_presets_show_raw_command() -> None:
    result = CliRunner().invoke(app, ["presets", "show", "performance", "--raw"])

    assert result.exit_code == 0
    assert '"name": "performance"' in result.output
    assert '"include_azure": true' in result.output
