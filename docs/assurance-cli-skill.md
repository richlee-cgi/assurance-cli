---
name: Assurance CLI Operator
description: Use the read-only assurance-cli to gather Confluence, Jira, Azure, Dataverse and local code evidence for assurance reviews.
---

# Assurance CLI Operator Skill

Use this skill when an assurance review needs evidence from Confluence, Jira, Azure, Dataverse, Power Platform or local code repositories and the local `assurance` command is available.

The CLI is designed for read-only evidence gathering. Prefer it over direct browser/API exploration when collecting structured Markdown evidence for review.

## Preconditions

Before running commands, verify:

```bash
assurance --help
```

If the command is not available, ask the user to install or activate the project environment. Do not guess credentials.

For Atlassian-backed commands, the environment must provide:

```bash
ATLASSIAN_BASE_URL
ATLASSIAN_EMAIL
ATLASSIAN_API_TOKEN
```

Optional defaults may also be present:

```bash
ATLASSIAN_DEFAULT_CONFLUENCE_SPACE
ATLASSIAN_DEFAULT_JIRA_PROJECT
```

For Azure-backed commands, the user must already be logged in with `az login`.

For Dataverse-backed commands, the user must already be authenticated with `pac auth create` or equivalent.

For code-backed commands, prefer local checked-out repositories. Ask the user for the repo root and relevant repository subset when it is not obvious.

## Core Rule

Use the CLI only to gather evidence. Do not use it as justification to mutate systems. The CLI itself blocks mutating Azure and Dataverse operations, but the agent should still avoid proposing or running write actions during assurance evidence collection.

Do not print, summarize or store secrets. Treat raw output as potentially sensitive. Prefer Markdown evidence packs with redacted cache data.

## Evidence Workflow

For a normal review:

1. Identify the topic, service, feature, component or risk area.
2. Gather a combined evidence pack.
3. Inspect gaps reported in the pack.
4. Use targeted follow-up commands for missing evidence.
5. Base findings only on evidence gathered or explicitly supplied by the user.

Default combined evidence command:

```bash
assurance report evidence-pack "TOPIC" \
  --confluence-space SPACE \
  --jira-project PROJ \
  --out evidence/topic-evidence.md
```

Use presets for common review themes:

```bash
assurance presets list
assurance presets show architecture
assurance report evidence-pack --preset architecture \
  --confluence-space SPACE \
  --jira-project PROJ \
  --out evidence/architecture-pack.md
```

Useful built-in presets:

- `architecture`: architecture, design decisions, integrations and dependencies.
- `delivery`: delivery trail, implementation tickets, status, releases and blockers.
- `operations`: operational readiness, deployment, monitoring, alerting and runtime state.
- `dataverse`: Dataverse, Power Platform, solutions, connectors and connection references.
- `performance`: APIM, Functions, scaling, performance, capacity and timeout concerns.
- `risk`: known risks, blockers, incidents, defects, security concerns, unsupported dependencies and mitigations.

If the user provides a specific topic with `--preset`, the topic overrides the preset search text while the preset still supplies inclusion defaults.

Include local code evidence when implementation evidence is relevant:

```bash
assurance report evidence-pack "TOPIC" \
  --include-code \
  --repo-root /path/to/dev \
  --repo service-a \
  --out evidence/topic-pack.md
```

## Confluence Evidence

Search pages:

```bash
assurance confluence search "TOPIC" --space SPACE --limit 20
```

Use explicit CQL when the question is precise:

```bash
assurance confluence search --cql 'space = "SPACE" AND type = page AND text ~ "TOPIC"'
```

Pull a page into Markdown:

```bash
assurance confluence get --url "https://example.atlassian.net/wiki/spaces/SPACE/pages/123456789/Page" \
  --out evidence/page.md
```

Use include switches only when needed because they increase output size:

```bash
assurance confluence get --id 123456789 \
  --include-comments \
  --include-children \
  --include-attachments
```

## Jira Evidence

Search issues:

```bash
assurance jira search "TOPIC" --project PROJ --limit 30
```

Use explicit JQL when the query needs precision:

```bash
assurance jira search --jql 'project = PROJ AND text ~ "TOPIC" ORDER BY updated DESC'
```

Fetch issue details:

```bash
assurance jira get PROJ-123 --include-comments --comment-limit 5
```

Fetch multiple issues when comparing related work:

```bash
assurance jira get PROJ-123 PROJ-456 --include-comments
```

## Azure Evidence

Check current context first:

```bash
assurance azure check
```

Search resources:

```bash
assurance azure resource-search "TOPIC" \
  --resource-group rg-example-dev \
  --limit 20
```

Use `--dry-run` to inspect the underlying allowlisted `az` command without calling Azure:

```bash
assurance azure resource-search "TOPIC" --resource-group rg-example-dev --dry-run
```

Snapshot a resource group:

```bash
assurance azure snapshot --resource-group rg-example-dev \
  --out evidence/azure-snapshot.md
```

Function app settings are redacted by default:

```bash
assurance azure functions --resource-group rg-example-dev --include-settings
```

Only use `--show-setting-values` if the user explicitly asks and the output will be handled as sensitive.

## Dataverse And Power Platform Evidence

Check current `pac` context:

```bash
assurance dataverse check
```

List environments, solutions, connectors and connections:

```bash
assurance dataverse environments
assurance dataverse solutions --environment https://example.crm11.dynamics.com
assurance dataverse connectors
assurance dataverse connections
```

Build a Dataverse snapshot:

```bash
assurance dataverse snapshot --out evidence/dataverse-snapshot.md
```

Dataverse snapshots may take around a minute depending on `pac` and environment response time.

## Code Repository Evidence

List local Git repositories under a root:

```bash
assurance code repos --repo-root /path/to/dev
```

Search selected repositories:

```bash
assurance code search "TOPIC" \
  --repo-root /path/to/dev \
  --repo service-a \
  --limit 30 \
  --out evidence/code.md
```

Use `--repo-file` when the user has a saved repository subset:

```bash
assurance code search "TOPIC" --repo-root /path/to/dev --repo-file repos.txt
```

Code evidence is local-first. Do not run `git pull`, `git fetch`, `git checkout`, `git commit`, `git push`, or other mutating Git commands as part of evidence gathering unless the user explicitly asks outside this CLI workflow.

Resolve a specific GitHub pull request only when PR evidence is needed and `gh` is authenticated:

```bash
assurance code pr https://github.com/org/repo/pull/123 --include-diff --out evidence/pr.md
```

For combined evidence packs, PR metadata is opt-in and diffs are separately opt-in:

```bash
assurance report evidence-pack "TOPIC" \
  --include-code \
  --repo-root /path/to/dev \
  --repo service-a \
  --include-prs \
  --include-diffs \
  --out evidence/topic-pack.md
```

## Cache Use

The CLI caches Atlassian raw responses under `.assurance-cache/` with sensitive-looking fields redacted.

Inspect cache entries:

```bash
assurance cache list --verbose
assurance cache show atlassian/jira/search/<hash> --metadata-only
```

Use `--refresh` when evidence may have changed:

```bash
assurance jira search "TOPIC" --project PROJ --refresh
```

Use `--no-cache` for one-off sensitive retrievals that should not be cached:

```bash
assurance confluence get --id 123456789 --no-cache
```

Clear cache only when requested or when stale cache is clearly affecting evidence gathering:

```bash
assurance cache clear atlassian/jira/search/<hash>
assurance cache clear --all
```

## Output Guidance

Prefer writing evidence to files so the review can cite stable artifacts:

```bash
assurance report evidence-pack "TOPIC" --out evidence/topic-pack.md
```

Use `--raw` only for debugging or when the user needs JSON:

```bash
assurance jira search --jql 'project = PROJ ORDER BY updated DESC' --raw
```

When reporting back, summarize:

- Commands run.
- Evidence files created.
- Key evidence found.
- Missing evidence or gaps.
- Any commands that failed and why.

Do not claim evidence exists unless it appears in CLI output or user-provided material.

## Failure Handling

If Atlassian auth fails, ask the user to check `ATLASSIAN_EMAIL`, `ATLASSIAN_API_TOKEN` and site access.

If Azure commands fail, report the current `assurance azure check` context and the failing command.

If Dataverse commands fail, report `assurance dataverse check` output and whether `pac` appears authenticated.

If a command returns no results, treat that as missing evidence, not proof that the topic is absent.

## Review Integration

After gathering evidence, return to the assurance reviewer method:

- Evidence found.
- Positive findings.
- Risks and concerns.
- Missing evidence.
- Follow-up questions.
- Assurance assessment with confidence level.
