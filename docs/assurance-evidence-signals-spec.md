# Assurance Evidence Signals Spec

This spec describes deterministic, non-GenAI signals derived from retrieved evidence.

The aim is to help reviewers notice potentially important patterns in evidence packs. Signals are not conclusions, approvals or risk ratings. They are review prompts backed by visible evidence.

## Purpose

Evidence packs can become large. The first analysis layer should make them easier to review by highlighting:

- Risk markers found in the retrieved evidence.
- Expected assurance themes that are weak or absent in the retrieved evidence.
- Content patterns that suggest follow-up questions.

The implementation must remain:

- Deterministic.
- Explainable.
- Local.
- Editable by users.
- Independent of local LLMs, embeddings, vector databases or RAG.

## Non-Goals

- Do not claim a system is safe, unsafe, compliant or non-compliant.
- Do not infer facts not visible in retrieved evidence.
- Do not score teams, projects or individuals.
- Do not replace human review.
- Do not require NLP models, cloud AI services or local model downloads.

## Inputs

Initial inputs should be files already saved in a Workbench run folder:

```text
runs/<run-id>/
  request.json
  evidence-pack.md
  stdout.log
  stderr.log
```

Future versions may also consume structured sidecar files from `assurance-cli` if we add them, but the first useful version should work from `evidence-pack.md` and run metadata.

## Outputs

Signals should be written beside the evidence pack:

```text
runs/<run-id>/
  analysis.json
  analysis.md
```

`analysis.json` is the structured source of truth for the UI.

`analysis.md` is a human-readable summary that can be copied into assurance notes.

Example JSON:

```json
{
  "version": 1,
  "ruleset_version": "2026-06-25",
  "generated_at": "2026-06-25T14:30:00+01:00",
  "signals": [
    {
      "rule_id": "operations.readiness_terms_missing",
      "ruleset": "operations",
      "severity": "medium",
      "source": "Evidence pack",
      "title": "Operational readiness terms were not found",
      "detail": "The retrieved evidence did not contain monitoring, alerting, rollback or runbook terms.",
      "evidence": {
        "section": "Confluence Evidence",
        "matched_terms": [],
        "missing_terms": ["monitoring", "alert", "rollback", "runbook"]
      },
      "follow_up": "Ask the team where operational readiness evidence is recorded."
    }
  ]
}
```

## Rule Definition Files

Rulesets should be defined in Markdown so users can read and amend them without editing Python code.

Suggested location:

```text
assurance-workbench-ui/
  app/rulesets/
    architecture.md
    delivery.md
    operations.md
    security.md
    testing.md
    risk.md
```

Later, allow a user override directory from settings:

```text
Workbench/
  00 Config/
    assurance-rulesets/
      risk.md
      operations.md
```

The built-in rulesets should remain versioned in Git. User overrides should remain local and ignored.

## Rule Markdown Format

Use a simple Markdown format with YAML front matter per rule. This keeps rules editable while still machine-readable.

Example:

```markdown
---
id: operations.readiness_terms_missing
ruleset: operations
severity: medium
applies_to_presets:
  - architecture
  - operations
applies_to_sources:
  - confluence
  - jira
  - azure
description: No operational readiness terms were found in retrieved evidence.
follow_up: Ask the team where monitoring, alerting, rollback and runbook evidence is recorded.
---

# Operational Readiness Terms Missing

## Required Any Terms

- monitoring
- alert
- alerting
- dashboard
- runbook
- rollback
- on-call
- support model

## Negative Terms

- no monitoring
- not monitored
- manual workaround
- temporary
- to be confirmed
- tbc
- todo

## Match Strategy

Raise a medium signal when none of the required terms appear in the selected evidence sections.
Raise a high signal when one or more negative terms appear.
```

The first implementation does not need a fully generic rule language. It can support a small subset:

- Front matter metadata.
- `Required Any Terms`.
- `Required All Terms`.
- `Negative Terms`.
- `Positive Terms`.
- `Applies to presets`.
- `Applies to sources`.
- Match strategy values implemented in Python.

If a rule uses unsupported syntax, it should be skipped with a visible warning rather than guessed.

## Initial Rulesets

### Delivery

Signals to consider:

- Unresolved blocker, incident, defect or security terms.
- Delivery evidence mentions blocked, workaround, dependency or delayed.
- Implementation evidence exists but no test/UAT terms are found.
- Many Jira comments contain risk or uncertainty markers.

Example terms:

```text
blocked, blocker, incident, defect, bug, workaround, dependency, delayed, overdue, risk, issue, unresolved
```

### Operations

Signals to consider:

- No monitoring, alerting, dashboard, runbook, rollback or support terms.
- Negative operational markers are present.
- Evidence mentions deployment/runtime resources but no ownership or support model.

Example terms:

```text
monitoring, alert, dashboard, runbook, rollback, support, on-call, incident, sla, slo
```

### Architecture

Signals to consider:

- Integrations or dependencies are mentioned but decision/trade-off terms are absent.
- Architecture evidence lacks ADR, decision, alternative, constraint or failure-mode terms.
- Security/privacy terms appear in architecture evidence and should be reviewed.

Example terms:

```text
adr, decision, trade-off, alternative, constraint, dependency, integration, failure mode, boundary
```

### Security And Privacy

Signals to consider:

- Evidence contains personal data, PII, permission, role, token, credential or secret terms.
- Negative markers such as shared account, manual access or not encrypted appear.
- Security terms are absent for topics that appear to involve user/customer data.

Example terms:

```text
personal data, pii, permission, role, access, encryption, audit, token, credential, secret
```

### Testing And Quality

Signals to consider:

- Delivery evidence exists but no testing terms are found.
- Performance preset was used but no performance/load test terms are found.
- Risk or defect terms appear without mitigation or regression-test terms.

Example terms:

```text
test, tested, uat, acceptance criteria, integration test, regression, performance test, load test
```

### Risk

Signals to consider:

- Known-bad terms appear: risk, blocker, incident, defect, vulnerability, unsupported, failed, warning, unresolved.
- Risk terms appear without mitigation, owner or decision terms.
- Temporary/workaround language appears repeatedly.

Example terms:

```text
risk, blocker, incident, defect, vulnerability, unsupported, mitigation, warning, failed, unresolved, workaround, temporary
```

## Matching Model

The first implementation should be simple and auditable:

1. Split `evidence-pack.md` into sections using Markdown headings.
2. Normalize text to lowercase.
3. Match terms as case-insensitive words or phrases.
4. Count matches by section and source.
5. Raise signals from rule strategies.

Avoid stemming, lemmatization or topic expansion initially. Source systems such as Confluence and Jira already apply their own search behaviour, and rule matching should stay predictable.

## Presentation

In the UI result view, show an Assurance Signals panel before the rendered evidence pack.

Suggested grouping:

- High attention.
- Medium attention.
- Information.

Each signal should show:

- Title.
- Severity.
- Rule ID.
- Source or evidence section.
- Explanation.
- Matched or missing terms where relevant.
- Suggested follow-up question.

Use careful language:

- Prefer "No monitoring terms were found in the retrieved evidence."
- Avoid "There is no monitoring."

## Implementation Phases

### Phase A - Ruleset Files And Parser

- Add built-in Markdown rulesets.
- Implement the supported Markdown/front-matter parser.
- Validate unsupported sections without guessing.
- Add parser tests before signal rules.

### Phase B - Evidence Section Parser And Matcher

- Parse `evidence-pack.md` into sections.
- Implement case-insensitive word and phrase matching.
- Report matched and missing terms per section.

### Phase C - Built-In Signal Generation

- Implement the first content-signal rules over parsed sections.
- Write `analysis.json`.
- Write `analysis.md`.
- Keep signal-generation warnings separate from evidence-run failures.

### Phase D - UI Integration

- Generate signals after successful evidence-pack runs.
- Load existing signal files for previous runs.
- Render the Assurance Signals panel in the result view.
- Add a manual regenerate action if analysis files are missing or stale.

### Phase E - User-Tunable Rules

- Add settings value for ruleset override directory.
- Load local Markdown rulesets after built-ins.
- Show active rule file paths in the UI.
- Add validation warnings for unsupported rule syntax.

### Phase F - Structured Source Enhancements

- Add optional structured source summaries from `assurance-cli`.
- Improve Jira status/priority/date signals without scraping Markdown tables.
- Improve Confluence freshness signals.
- Improve code/PR signals.

### Phase G - Optional Local LLM

Only after deterministic signals are useful, consider local LLM commentary over the signals and evidence. Any LLM output must be clearly marked as draft/unverified and must not replace deterministic signals.
