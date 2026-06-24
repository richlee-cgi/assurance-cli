# assurance-cli

Read-only Python CLI for gathering assurance evidence from Confluence, Jira, Azure, and Dataverse/Power Platform, with Markdown-first output.

Implemented so far:

- `assurance confluence search`
- `assurance confluence get`
- `assurance confluence evidence-pack`
- `assurance jira search`
- `assurance jira get`
- `assurance jira evidence-pack`
- `assurance report evidence-pack`
- `assurance azure check`
- `assurance azure resource-search`
- `assurance azure resource-get`
- `assurance azure functions`
- `assurance azure apim`
- `assurance azure role-assignments`
- `assurance azure snapshot`
- `assurance dataverse check`
- `assurance dataverse environments`
- `assurance dataverse solutions`
- `assurance dataverse connectors`
- `assurance dataverse connections`
- `assurance dataverse snapshot`
- `assurance presets list`
- `assurance presets show`
- cache helpers

## Install for local development

```bash
cd assurance-cli
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e ".[dev]"
```

## Configure

Create environment variables in your shell, or copy `.env.example` to `.env` and fill in local values:

```bash
export ATLASSIAN_BASE_URL="https://example.atlassian.net"
export ATLASSIAN_EMAIL="you@example.com"
export ATLASSIAN_API_TOKEN="..."
export ATLASSIAN_DEFAULT_CONFLUENCE_SPACE="SPACE"
export ATLASSIAN_DEFAULT_JIRA_PROJECT="PROJ"
```

Secrets are never intentionally printed or cached. The API token is used only for HTTP Basic Auth.

Azure commands wrap the installed Azure CLI. Install and sign in before use:

```bash
brew install azure-cli
az login
az account show
```

Dataverse commands wrap the Microsoft Power Platform CLI. The .NET global tool is supported:

```bash
dotnet tool install --global Microsoft.PowerApps.CLI.Tool --version 1.43.6
export PATH="$PATH:$HOME/.dotnet/tools"
pac auth create --name example --deviceCode
pac auth list
```

## Examples

```bash
assurance confluence search "booking allocation" --space SPACE --limit 20
assurance confluence get --id 123456789 --out evidence/page.md
assurance confluence evidence-pack "booking allocation" --space DSP --limit 10 --out evidence/confluence-pack.md
assurance jira search "Dataverse" --project ABC --limit 30
assurance jira get ABC-123 --include-comments --comment-limit 5
assurance jira evidence-pack "Dataverse" --project ABC --include-comments --out evidence/jira-pack.md
assurance report evidence-pack "booking allocation Dataverse" --confluence-space SPACE --jira-project ABC --out evidence/pack.md
assurance presets list
assurance presets show dataverse
assurance report evidence-pack --preset dataverse --confluence-space SPACE --jira-project ABC --out evidence/dataverse-pack.md
assurance report evidence-pack --preset scaling --include-azure --azure-resource-group rg-example-dev --limit 20 --out evidence/scaling-pack.md
assurance azure check
assurance azure resource-search "booking" --limit 20
assurance azure snapshot --resource-group rg-example-dev --out evidence/azure-snapshot.md
assurance dataverse check
assurance dataverse environments
assurance dataverse snapshot --out evidence/dataverse-snapshot.md
```

Raw JSON can be emitted where useful:

```bash
assurance jira search --jql "project = ABC ORDER BY updated DESC" --raw
```

## Combined reports

`assurance report evidence-pack` queries Confluence and Jira by default. Add `--include-azure` to run a bounded Azure Resource Graph search for the topic, and add `--include-dataverse` to include a Dataverse snapshot from the current `pac` profile.

Built-in presets provide common assurance search topics and inclusion defaults:

```bash
assurance presets list
assurance presets show architecture
assurance report evidence-pack --preset architecture --confluence-space SPACE --jira-project PROJ --out evidence/architecture-pack.md
```

Passing a topic with `--preset` overrides only the preset search text; the preset still supplies its inclusion defaults.

Use `--azure-resource-group` when possible to keep Azure evidence focused:

```bash
assurance report evidence-pack "Reservations API" \
  --include-azure \
  --azure-resource-group rg-example-dev \
  --include-dataverse \
  --limit 3 \
  --out evidence/reservations-api-pack.md
```

Dataverse snapshots call several `pac` commands and may take around a minute depending on the environment.

## Cache

Raw responses are cached under `.assurance-cache/` by default, with sensitive-looking fields redacted before writing.

```bash
assurance cache list
assurance cache show atlassian/jira/search/<hash>
```

## Safety

The implemented commands use read-only retrieval only. Jira and Confluence search use Atlassian retrieval endpoints and do not create, update, delete, transition, comment, label, publish, sync, or mutate remote systems.

Azure commands are wrapped through an allowlisted `az` runner. Mutating verbs such as `create`, `update`, `delete`, `set`, `restart`, `deploy`, `publish`, `import`, and `sync` are blocked.

Dataverse commands are wrapped through an allowlisted `pac` runner. Mutating operations such as solution import/export/publish/sync and environment changes are blocked.
