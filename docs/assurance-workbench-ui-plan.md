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
- [ ] Confirm code evidence source design in [assurance-code-evidence-spec.md](assurance-code-evidence-spec.md).
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
  - [x] delivery
  - [x] operations
  - [x] dataverse
  - [x] performance
  - [x] risk
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
- [x] Output folder preview.
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
- [x] Stream stdout/stderr to UI.
- [x] Save `stdout.log`.
- [x] Save `stderr.log`.
- [x] Save `evidence-pack.md`.
- [x] Capture exit code.
- [x] Support cancellation.
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
- [x] Add “open output folder” action.
- [x] Add “open in VS Code” action if feasible.

Acceptance:

- [x] User can inspect a completed evidence pack in the browser.
- [x] User can navigate to saved files.

## Phase 6 - Previous Runs

Goal: browse existing Workbench evidence runs.

- [x] Scan configured runs folder.
- [x] Parse `request.json`.
- [x] Parse run status from exit code/log files.
- [x] List previous runs.
- [x] Filter by topic.
- [x] Filter by preset/source.
- [x] Open previous run.
- [x] Re-run from previous `request.json`.

Acceptance:

- [ ] User can find and reopen previous evidence runs.
- [ ] User can re-run a previous request.

## Phase 7 - Code Repository Evidence

Goal: add local repository evidence as an optional evidence-pack source, with GitHub/PR retrieval as an explicit fallback.

CLI prerequisites:

- [x] Add `assurance code repos`.
- [x] Add `assurance code search`.
- [x] Add `assurance code pr` for supplied GitHub PR URLs.
- [x] Add local repo discovery under configured roots.
- [x] Add bounded local content search.
- [x] Add bounded commit/log evidence.
- [x] Add read-only `gh` PR metadata retrieval.
- [x] Add opt-in bounded diff retrieval.
- [x] Add redaction and truncation markers for code snippets.
- [x] Add `--include-code` to `assurance report evidence-pack`.
- [x] Add `--repo-root`, `--repo`, `--repo-file`.
- [x] Add `--include-prs`, `--include-diffs`, `--github-fallback`.
- [x] Add Code Evidence section to combined evidence packs.

UI work:

- [x] Add default repo roots in settings.
- [x] Add repo discovery action.
- [x] Add repository subset field.
- [ ] Add repository filter.
- [x] Add Code repositories source checkbox.
- [x] Add Include PR metadata checkbox.
- [x] Add Include bounded diffs checkbox.
- [x] Add GitHub fallback checkbox.
- [x] Add code flags to command preview and run execution.
- [x] Preserve repo roots and selected repos in `request.json`.
- [x] Show Code repositories in source coverage.
- [x] Add previous-run filter for Code repositories.
- [x] Display local/GitHub provider status and code evidence gaps.

Acceptance:

- [x] User can select local repos for a run.
- [x] Evidence pack includes bounded local code evidence when requested.
- [x] GitHub PR evidence is opt-in and read-only.
- [x] Missing repos, missing `gh` auth and truncated diffs are visible as gaps.

## Phase 8 - Evidence Signals

Goal: add explainable non-GenAI signals from retrieved evidence content.

Design: [assurance-evidence-signals-spec.md](assurance-evidence-signals-spec.md).

Implementation order:

### Phase 8A - Ruleset Files And Parser

- [ ] Add built-in Markdown ruleset files:
  - [ ] Architecture.
  - [ ] Delivery.
  - [ ] Operations.
  - [ ] Security and privacy.
  - [ ] Testing and quality.
  - [ ] Risk.
- [ ] Define and implement supported ruleset Markdown format:
  - [ ] YAML front matter metadata.
  - [ ] Required any terms.
  - [ ] Required all terms.
  - [ ] Positive terms.
  - [ ] Negative terms.
  - [ ] Applies-to presets.
  - [ ] Applies-to sources.
- [ ] Add parser tests for valid and invalid rulesets.
- [ ] Add validation warnings for unsupported ruleset syntax.

### Phase 8B - Evidence Section Parser And Matcher

- [ ] Parse `evidence-pack.md` into Markdown sections.
- [ ] Implement term matching:
  - [ ] Case-insensitive words and phrases.
  - [ ] Per-section match counts.
  - [ ] Matched and missing term reporting.
- [ ] Add tests for heading parsing, phrase matching and missing-term reporting.

### Phase 8C - Built-In Signal Generation

- [ ] Implement initial content signal rules:
  - [ ] Delivery risk markers.
  - [ ] Operational readiness term gaps.
  - [ ] Architecture decision/trade-off term gaps.
  - [ ] Security/privacy review markers.
  - [ ] Testing/quality term gaps.
  - [ ] Known risk terms without mitigation/owner/decision markers.
- [ ] Write `analysis.json`.
- [ ] Write `analysis.md`.
- [ ] Add tests for representative evidence packs and generated signal JSON.

### Phase 8D - Run Integration

- [ ] Run evidence-signal generation after a successful evidence-pack run.
- [ ] Preserve signal generation warnings without failing the evidence run.
- [ ] Load existing `analysis.json` and `analysis.md` for previous runs.
- [ ] Add a manual regenerate action if analysis files are missing or stale.

### Phase 8E - Result View

- [ ] Display Assurance Signals in the result view:
  - [ ] Group by high, medium and info.
  - [ ] Show rule ID and ruleset.
  - [ ] Show matched or missing terms.
  - [ ] Show follow-up question.
- [ ] Add route/rendering tests for signal groups and empty-state behaviour.

### Phase 8F - User-Tunable Rules

- [ ] Add settings value for optional local ruleset override directory.
- [ ] Show active built-in and override ruleset paths in the Guide or Settings page.
- [ ] Load override rulesets after built-ins.
- [ ] Ensure local override files are never written to Git-managed locations automatically.

Acceptance:

- [ ] UI produces repeatable, explainable signals without GenAI.
- [ ] Signals are grounded in retrieved evidence content, not tool-performance assumptions.
- [ ] Each signal has rule ID, ruleset, severity, source/section, explanation, evidence terms and follow-up question.
- [ ] Users can read the Markdown rulesets and understand why a signal was raised.

## Phase 9 - Polish And Packaging

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
