import pytest

from assurance_cli.azure.cli import build_resource_graph_query, validate_az_command
from assurance_cli.azure.markdown import azure_check_markdown, azure_snapshot_markdown, function_apps_markdown
from assurance_cli.exceptions import UnsafeCommandError


def test_validate_allows_read_only_az_command() -> None:
    validate_az_command(["az", "resource", "list", "--resource-group", "rg"])


def test_validate_blocks_mutating_az_command() -> None:
    with pytest.raises(UnsafeCommandError):
        validate_az_command(["az", "functionapp", "restart", "--name", "app"])


def test_validate_blocks_unlisted_az_command() -> None:
    with pytest.raises(UnsafeCommandError):
        validate_az_command(["az", "ad", "user", "list"])


def test_resource_graph_query() -> None:
    query = build_resource_graph_query(
        query="booking",
        resource_type="microsoft.web/sites",
        resource_group="rg-example",
        tags=("Project=example",),
        limit=10,
    )
    assert "name contains 'booking'" in query
    assert "type =~ 'microsoft.web/sites'" in query
    assert "tags['Project']" in query
    assert "| limit 10" in query


def test_azure_check_markdown() -> None:
    markdown = azure_check_markdown(
        account={"name": "Example Subscription", "id": "sub", "tenantDisplayName": "Example Tenant", "user": {"name": "user@example.com"}},
        az_path="/opt/homebrew/bin/az",
        command="az account show -o json",
    )
    assert "# Azure CLI Check" in markdown
    assert "Example Subscription" in markdown


def test_azure_snapshot_markdown_counts_resource_types() -> None:
    markdown = azure_snapshot_markdown(
        resource_group="rg",
        resources=[
            {"name": "a", "type": "Microsoft.Web/sites", "resourceGroup": "rg", "location": "uksouth"},
            {"name": "b", "type": "Microsoft.Web/sites", "resourceGroup": "rg", "location": "uksouth"},
        ],
        command="az resource list",
    )
    assert "- `Microsoft.Web/sites`: 2" in markdown


def test_function_apps_markdown_is_concise_and_reports_setting_errors() -> None:
    markdown = function_apps_markdown(
        apps=[
            {
                "name": "func",
                "resourceGroup": "rg",
                "location": "UK South",
                "state": "Running",
                "sku": "FlexConsumption",
                "httpsOnly": True,
                "publicNetworkAccess": "Disabled",
                "functionAppConfig": {
                    "runtime": {"name": "node", "version": "22"},
                    "deployment": {"storage": {"type": "blobContainer"}},
                    "scaleAndConcurrency": {"maximumInstanceCount": 50},
                },
                "identity": {"type": "SystemAssigned, UserAssigned", "userAssignedIdentities": {"id": {}}},
                "serverFarmId": "/plans/asp",
                "id": "/sites/func",
            }
        ],
        settings_by_app={},
        setting_errors={"func": "AuthorizationFailed"},
        show_values=False,
        command="az functionapp list",
        scope="rg",
    )
    assert "Runtime: `node 22`" in markdown
    assert "User-assigned identities: `1`" in markdown
    assert "AuthorizationFailed" in markdown
    assert "customDomainVerificationId" not in markdown
