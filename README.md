# assurance-cli

Read-only Python CLI for gathering assurance evidence from Confluence, Jira, Azure, and Dataverse/Power Platform, with Markdown-first output.

Command groups:

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
- `assurance cache list`
- `assurance cache show`
- `assurance cache clear`

## Install for local development

```bash
cd assurance-cli
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e ".[dev]"
```

## Shell completion

The CLI uses Typer, so shell completion is available after local installation.

Install completion for your current shell:

```bash
assurance --install-completion
```

Or generate completion script text for a specific shell:

```bash
assurance --show-completion zsh
assurance --show-completion bash
assurance --show-completion fish
```

Restart the shell after installation. Completion should then work for command groups and options, for example:

```bash
assurance <TAB>
assurance jira <TAB>
assurance report evidence-pack --<TAB>
```

## Agent usage

For VS Code Copilot agents or local model workflows, see [docs/assurance-cli-skill.md](docs/assurance-cli-skill.md). It describes when and how an agent should use the CLI to gather read-only assurance evidence.

For a proposed local web UI wrapper that keeps the CLI standalone, see [docs/assurance-workbench-ui-spec.md](docs/assurance-workbench-ui-spec.md).

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

### Corporate TLS / Zscaler

Some corporate networks intercept TLS traffic through tools such as Zscaler. If Atlassian commands fail before authentication with an error like `CERTIFICATE_VERIFY_FAILED` or `unable to get local issuer certificate`, point Python/httpx at a CA bundle that trusts your network.

Atlassian HTTP calls use the virtual environment's `certifi` bundle by default so a broken ambient `SSL_CERT_FILE` does not accidentally break the CLI. If your organisation provides a custom CA bundle, set `ASSURANCE_CA_BUNDLE` to that approved bundle:

```bash
export ASSURANCE_CA_BUNDLE="$HOME/.certs/company-ca-bundle.pem"
assurance confluence search "test" --limit 1
assurance jira search "test" --limit 1
```

If you need to force the `certifi` bundle from a shell:

```bash
export ASSURANCE_CA_BUNDLE="$(pwd)/.venv/lib/python*/site-packages/certifi/cacert.pem"
```

Do not disable TLS verification.

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
assurance confluence evidence-pack "booking allocation" --space SPACE --limit 10 --out evidence/confluence-pack.md
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
assurance azure resource-search "booking" --raw
```

## Command notes

Most commands support `--out` for Markdown/JSON files. Remote Atlassian responses are cached under `.assurance-cache/`; use `--refresh` to bypass an existing cache entry, `--no-cache` to avoid reading or writing cache for one run, and `--cache-dir` to use a different cache directory.

Confluence search accepts either a simple text query or explicit CQL:

```bash
assurance confluence search "booking allocation" --space SPACE --type page --updated-after 2026-01-01
assurance confluence search --cql 'space = "SPACE" AND type = page AND text ~ "booking"'
```

Confluence page retrieval can use a page ID or a URL. Include comments, child pages, or attachments only when they are useful; they make the result larger:

```bash
assurance confluence get --url "https://example.atlassian.net/wiki/spaces/SPACE/pages/123456789/Architecture"
assurance confluence get --id 123456789 --include-comments --include-children --max-body-chars 12000
```

Jira search accepts either a text query plus filters or explicit JQL:

```bash
assurance jira search "scaling timeout" --project ABC --status "In Progress" --issue-type Bug --label performance
assurance jira search --jql 'project = ABC AND text ~ "scaling timeout" ORDER BY updated DESC' --fields key,summary,status,assignee
```

Jira issue retrieval accepts one or more keys. Comments, changelog, and extra fields are opt-in:

```bash
assurance jira get ABC-123 ABC-456 --include-comments --comment-limit 5
assurance jira get ABC-123 --include-changelog --fields key,summary,status,description,comment
```

Azure commands support `--dry-run` to print the allowed `az` command without calling Azure. Resource Graph searches can be focused by subscription, type, resource group, tags, or a query file:

```bash
assurance azure resource-search "booking" --type microsoft.web/sites --resource-group rg-example-dev --tag Project=example
assurance azure resource-search --query-file queries/resources.kql --subscription 00000000-0000-0000-0000-000000000000 --raw
assurance azure resource-get --id "/subscriptions/.../resourceGroups/rg-example-dev/providers/Microsoft.Web/sites/app-example"
```

Function app settings are listed by name only unless `--show-setting-values` is explicitly provided:

```bash
assurance azure functions --resource-group rg-example-dev --include-settings
assurance azure functions --name app-example --include-settings --show-setting-values --out evidence/function-settings.md
```

APIM and role-assignment commands need explicit scoping when you want more than the summary:

```bash
assurance azure apim --resource-group rg-example-dev --include-apis
assurance azure role-assignments --scope "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg-example-dev"
```

Dataverse commands use the current `pac` authentication profile. Use `--environment` when listing solutions for a non-default environment:

```bash
assurance dataverse solutions --environment https://example.crm11.dynamics.com
assurance dataverse connections --raw
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
assurance cache list --verbose
assurance cache list --raw
assurance cache show atlassian/jira/search/<hash>
assurance cache show atlassian/jira/search/<hash> --metadata-only
assurance cache clear atlassian/jira/search/<hash>
assurance cache clear --all
```

## Safety

The implemented commands use read-only retrieval only. Jira and Confluence search use Atlassian retrieval endpoints and do not create, update, delete, transition, comment, label, publish, sync, or mutate remote systems.

Azure commands are wrapped through an allowlisted `az` runner. Mutating verbs such as `create`, `update`, `delete`, `set`, `restart`, `deploy`, `publish`, `import`, and `sync` are blocked.

Dataverse commands are wrapped through an allowlisted `pac` runner. Mutating operations such as solution import/export/publish/sync and environment changes are blocked.

## License

Licensed under the MIT License. See [LICENSE](LICENSE).
