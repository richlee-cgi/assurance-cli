# Assurance Code Evidence Spec

This spec defines repository and GitHub evidence gathering for `assurance-cli`.

The source name should be `code`, not `github`. GitHub is one provider for code evidence; local checked-out repositories are the preferred provider.

## Purpose

Add code/repository evidence to assurance evidence packs so reviewers can connect delivery evidence from Jira and Confluence with implementation evidence from local repositories and, where needed, GitHub pull requests.

The feature should:

- Prefer local repository search.
- Use GitHub only as an explicit fallback or when following PR/commit links.
- Keep retrieval read-only.
- Keep evidence bounded, reviewable and safe to include in Markdown.
- Support selecting a subset of repositories for a given evidence run.

## Non-Goals

- Do not mutate local repositories.
- Do not push, pull, fetch or checkout automatically in the first version.
- Do not create GitHub comments, reviews, issues, branches, commits or pull requests.
- Do not dump full source files or unbounded diffs into evidence packs.
- Do not require GitHub access for local repository evidence.
- Do not replace normal code review tools.

## Terminology

- `code source`: the evidence source shown in reports and UI.
- `local provider`: search and inspect local Git repositories using filesystem and `git` commands.
- `github provider`: use read-only `gh` commands for GitHub PRs, commits and remote metadata.
- `repo root`: a directory containing one or more checked-out Git repositories.
- `repo selector`: a selected repository name or path for the current run.

## Provider Order

Default behavior should be:

1. Search selected local repositories.
2. Follow local Git metadata where useful.
3. Use GitHub only when explicitly requested or when resolving supplied PR/commit URLs.

The CLI should clearly report when GitHub was not used.

## CLI Commands

Add a top-level command group:

```bash
assurance code ...
```

Initial commands:

```bash
assurance code repos --repo-root /path/to/dev

assurance code search "booking allocation" \
  --repo-root /path/to/dev \
  --repo service-a \
  --repo service-b \
  --limit 30

assurance code pr https://github.com/org/repo/pull/123 \
  --include-diff
```

Combined report integration:

```bash
assurance report evidence-pack "booking allocation" \
  --include-code \
  --repo-root /path/to/dev \
  --repo service-a \
  --repo service-b \
  --out evidence/booking-allocation.md
```

## Combined Report Options

Add options to `assurance report evidence-pack`:

- `--include-code`: include code evidence.
- `--repo-root PATH`: root directory to scan for local Git repositories. Repeatable.
- `--repo NAME_OR_PATH`: selected repository. Repeatable.
- `--repo-file PATH`: newline-delimited repository selectors.
- `--include-prs`: include PR metadata when PR links are discovered in Jira/Confluence evidence or supplied directly.
- `--include-diffs`: include bounded diffs. Defaults to false.
- `--github-fallback`: allow `gh` lookup when local evidence is missing or a PR URL cannot be resolved locally.
- `--max-file-bytes N`: cap file excerpt reads.
- `--max-diff-lines N`: cap diff output.

`--include-code` should be opt-in initially.

## Local Provider

The local provider should discover Git repositories under configured roots without recursing into ignored build/cache directories.

Recommended commands:

- `git -C <repo> rev-parse --show-toplevel`
- `git -C <repo> status --short --branch`
- `git -C <repo> grep -n --break --heading <query>`
- `git -C <repo> log --oneline --decorate --max-count <n> --grep <query>`
- `git -C <repo> show --stat --summary <commit>`

`rg` may be used for content search when it gives better results, but output should still be grouped by repository and file path.

The local provider must not run:

- `git pull`
- `git fetch`
- `git checkout`
- `git switch`
- `git merge`
- `git rebase`
- `git commit`
- `git push`
- destructive clean/reset commands

## GitHub Provider

The GitHub provider should use the GitHub CLI (`gh`) only for read-only retrieval.

Allowed initial operations:

- `gh pr view`
- `gh pr diff`
- `gh api repos/{owner}/{repo}/pulls/{number}/files`
- `gh api repos/{owner}/{repo}/commits/{sha}`

The provider must not use mutating `gh` commands such as `pr comment`, `pr review`, `issue edit`, `repo edit`, `workflow run`, or any write-capable API endpoint.

GitHub access failures should be reported as gaps, not fatal errors, when local evidence was still collected.

## Jira And Confluence Link Handling

When `--include-prs` is enabled, the report layer may extract GitHub PR or commit links from gathered Jira/Confluence Markdown and attempt to resolve them.

Rules:

- Local repository evidence remains the default.
- Only GitHub URLs should be followed by the GitHub provider.
- Unknown links should be listed as unresolved links.
- PR metadata should include title, state, author, branch names, merge status where available, and changed-file summary.
- PR diffs should require `--include-diffs` and must be capped.

## Evidence Pack Output

Combined evidence packs should add:

```markdown
## Code Evidence

### Repository Scope

### Local Repository Search

### Pull Requests

### Diffs

### Code Evidence Gaps
```

Repository search output should include:

- Repository name/path.
- Current branch.
- Dirty/clean working tree status.
- Matched files and line numbers.
- Short bounded snippets.
- Matching commit summaries where useful.

Diff output should include:

- PR or commit identifier.
- File list.
- Bounded diff excerpt.
- Truncation marker when capped.

## Request Metadata

Evidence run `request.json` should capture:

```json
{
  "sources": {
    "code": true
  },
  "repo_roots": ["/path/to/dev"],
  "repos": ["service-a", "service-b"],
  "include_prs": true,
  "include_diffs": false,
  "github_fallback": false,
  "max_file_bytes": 20000,
  "max_diff_lines": 500
}
```

## Cache

Local repository evidence should not be cached by default because it is already local and may change frequently.

GitHub provider responses may be cached under `.assurance-cache/github/...` with metadata and redaction. Cached GitHub evidence should include enough command metadata to diagnose stale results.

## Safety And Redaction

- Treat source code and diffs as sensitive until reviewed.
- Redact obvious secrets from snippets and diffs using the existing redaction utilities.
- Limit output by default.
- Always mark truncated snippets/diffs.
- Include commands run in the appendix.
- Report dirty working trees so reviewers know evidence may include uncommitted local changes.

## Acceptance Criteria

- User can list discovered local repositories.
- User can search selected local repositories and get bounded Markdown evidence.
- User can include selected local repository evidence in `report evidence-pack`.
- User can resolve a supplied GitHub PR URL using `gh` when authenticated.
- GitHub failures are reported as gaps unless GitHub evidence was the only requested operation.
- Mutating Git and GitHub operations are not exposed.
- Evidence packs show whether code evidence came from local repositories, GitHub, or both.
