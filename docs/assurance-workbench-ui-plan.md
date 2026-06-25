# Assurance Workbench UI Plan

This plan tracks implementation of a local HTMX-based web UI wrapper around `assurance-cli`.

The CLI remains standalone. The UI invokes the CLI and persists evidence into the Workbench.

## Phase 0 - Decisions And Boundaries

- [x] Keep `assurance-cli` standalone.
- [x] Avoid RAG for v1.
- [x] Avoid local LLM/Ollama integration for v1.
- [x] Use the Workbench filesystem as persistence.
- [x] Start with HTMX rather than React/Vite.
- [x] Decide whether UI lives in this repo initially or a sibling repo.
- [ ] Decide default Workbench evidence root on the target machine.

## Phase 1 - Minimal Local Web App

Goal: start a local web server and render a basic UI.

- [x] Create `assurance-workbench-ui` project skeleton.
- [x] Add FastAPI dependency set.
- [x] Add Jinja templates.
- [x] Add HTMX static asset strategy.
- [x] Add simple app layout:
  - [x] Header.
  - [x] Navigation.
  - [x] Main content area.
- [x] Add local dev command.
- [x] Add README setup instructions.
- [x] Verify app starts locally.

Acceptance:

- [x] User can run one command and open the UI in a browser.
- [x] UI shows home page and basic navigation.

## Phase 2 - CLI Discovery And Settings

Goal: configure and verify the `assurance` executable without storing secrets.

- [x] Settings page.
- [x] Configure path to `assurance` executable.
- [x] Configure Workbench evidence root.
- [x] Configure default Confluence space.
- [x] Configure default Jira project.
- [x] Configure default Azure resource group.
- [x] Add `assurance --help` health check.
- [x] Add `assurance azure check` health check.
- [x] Add `assurance dataverse check` health check.
- [x] Store settings in a local ignored file.

Acceptance:

- [x] UI can verify the CLI path.
- [x] UI can show configured defaults.
- [x] No credentials are stored or displayed.

## Phase 3 - Evidence Pack Form

Goal: configure common evidence pack runs from the browser.

- [x] Topic input.
- [x] Preset dropdown:
  - [x] none
  - [x] architecture
  - [x] dataverse
  - [x] scaling
- [x] Source checkboxes:
  - [x] Confluence
  - [x] Jira
  - [x] Azure
  - [x] Dataverse
- [x] Confluence space input.
- [x] Jira project input.
- [x] Azure resource group input.
- [x] Limit input.
- [x] Include Jira comments checkbox.
- [x] Refresh cache checkbox.
- [x] No cache checkbox.
- [ ] Output folder preview.
- [x] Command preview.

Acceptance:

- [x] Form generates the expected `assurance report evidence-pack` command.
- [x] Command preview updates when inputs change.

## Phase 4 - Run Execution

Goal: run the generated CLI command and capture outputs.

- [x] Create timestamped Workbench run folder.
- [x] Write `request.json`.
- [x] Write `command.txt`.
- [x] Execute CLI via subprocess argv list, not shell string.
- [ ] Stream stdout/stderr to UI.
- [x] Save `stdout.log`.
- [x] Save `stderr.log`.
- [x] Save `evidence-pack.md`.
- [x] Capture exit code.
- [ ] Support cancellation.
- [x] Add timeout handling.

Acceptance:

- [x] User can run an evidence pack from the UI.
- [x] Result is saved under the Workbench.
- [x] Logs and command metadata are retained.
- [x] Failed runs are visible and diagnosable.

## Phase 5 - Results View

Goal: display completed evidence in an organised way.

- [x] Render Markdown evidence pack.
- [x] Show run metadata.
- [x] Show command executed.
- [x] Show source coverage:
  - [x] Confluence.
  - [x] Jira.
  - [x] Azure.
  - [x] Dataverse.
- [x] Show gaps and warnings.
- [ ] Add “open output folder” action.
- [ ] Add “open in VS Code” action if feasible.

Acceptance:

- [x] User can inspect a completed evidence pack in the browser.
- [ ] User can navigate to saved files.

## Phase 6 - Previous Runs

Goal: browse existing Workbench evidence runs.

- [x] Scan configured runs folder.
- [x] Parse `request.json`.
- [x] Parse run status from exit code/log files.
- [x] List previous runs.
- [ ] Filter by topic.
- [ ] Filter by preset/source.
- [x] Open previous run.
- [ ] Re-run from previous `request.json`.

Acceptance:

- [ ] User can find and reopen previous evidence runs.
- [ ] User can re-run a previous request.

## Phase 7 - Deterministic Analysis

Goal: add explainable non-GenAI analysis.

- [ ] Define analysis rule schema.
- [ ] Implement evidence coverage rules:
  - [ ] Confluence missing.
  - [ ] Jira missing.
  - [ ] Azure missing when requested.
  - [ ] Dataverse missing when requested.
- [ ] Implement freshness checks.
- [ ] Implement Azure risk flags:
  - [ ] Function settings unavailable.
  - [ ] Public network access appears enabled.
  - [ ] Managed identity appears missing.
- [ ] Implement Jira risk flags:
  - [ ] No issues found.
  - [ ] Stale open issues.
  - [ ] High priority issues present.
- [ ] Write `analysis.json`.
- [ ] Write `analysis.md`.
- [ ] Display analysis in results view.

Acceptance:

- [ ] UI produces repeatable, explainable findings without GenAI.
- [ ] Each finding has rule ID, severity, source, explanation and follow-up question.

## Phase 8 - Polish And Packaging

Goal: make the local UI easy to run and maintain.

- [ ] Add tests for command generation.
- [ ] Add tests for run folder creation.
- [ ] Add tests for deterministic analysis rules.
- [ ] Add basic UI route tests.
- [ ] Add setup instructions for official work Mac.
- [ ] Add screenshots if useful.
- [ ] Add `.gitignore` for local settings and run artifacts.
- [ ] Decide whether to tag first UI release.

Acceptance:

- [ ] User can install and run the UI from a clean checkout.
- [ ] Tests cover core behavior.
- [ ] Docs explain setup and operation.

## Deferred Ideas

- [ ] Ollama/Qwen local analysis, explicitly marked as draft/unverified.
- [ ] PDF export.
- [ ] Evidence run comparison.
- [ ] Configurable analysis rule packs.
- [ ] Git commit support for evidence packs.
- [ ] Library-mode integration with `assurance_cli` internals.
