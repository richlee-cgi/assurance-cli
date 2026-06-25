# Assurance Evidence Exclusions Spec

This spec describes configurable evidence exclusions for `assurance-cli` and the Workbench UI.

## Purpose

Evidence searches can pick up assurance governance pages or tickets about the review process itself. Those can dilute the evidence pack when the user is trying to review the product, service or delivery evidence.

Exclusions should let users intentionally remove known governance/self-reference areas while keeping the decision visible in the output.

## Initial Exclusions

### Confluence Parent Exclusions

Users can exclude Confluence pages under one or more parent pages.

Supported input:

- Page IDs.
- Confluence page URLs that contain `/pages/<id>/`.

CLI flags:

```bash
--exclude-confluence-parent 983238177
--exclude-confluence-parent https://example.atlassian.net/wiki/spaces/DSPBeta/pages/983238177/Assurance
```

The CLI should:

- Search Confluence as normal.
- Use expanded `ancestors` metadata where available.
- Drop search results whose ancestor IDs include an excluded parent ID.
- Record how many results were excluded.

### Jira Team Exclusions

Users can exclude Jira issues assigned to one or more teams.

CLI flags:

```bash
--jira-team-field customfield_12345
--exclude-jira-team "DSP Assurance"
```

The default field label can be `Team`, but Jira instances often use custom field IDs. Users should be able to configure the field used by their instance.

The CLI should:

- Search Jira as normal.
- Fetch issue details as normal.
- Drop issues whose configured team field matches an excluded team.
- Record how many issues were excluded.

## Output Transparency

Evidence packs should include a visible exclusions section:

```text
## Search Exclusions

- Confluence parent exclusions: `983238177`
- Jira team exclusions: `DSP Assurance`
- Jira team field: `customfield_12345`
- Excluded Confluence results: `4`
- Excluded Jira issues: `7`
```

If no exclusions are configured, the section should say that no search exclusions were applied.

## Workbench UI

Add Settings fields:

- Exclude Confluence from parent
  - Multiline list.
  - Accept page IDs and page URLs.
- Jira team field
  - Text input.
  - Defaults to `Team`.
  - Users can set a Jira custom field ID if needed.
- Exclude Jira from Team
  - Multiline list.
  - Exact team names.

The UI should:

- Pass repeated CLI flags from settings.
- Preserve exclusions in `request.json`.
- Explain exclusions in the browser Guide.

## Non-Goals

- Do not hard-code DVSA/DSP-specific page IDs or team names.
- Do not silently hide exclusions from generated evidence.
- Do not mutate Confluence or Jira content.
- Do not require users to know JQL/CQL to use exclusions.

