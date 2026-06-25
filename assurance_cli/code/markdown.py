from __future__ import annotations

from collections import defaultdict

from assurance_cli.code.github import PullRequestEvidence
from assurance_cli.code.local import CodeSearchResult, Repository
from assurance_cli.markdown import document_header, markdown_table


def repositories_markdown(repositories: list[Repository], *, roots: list[str]) -> str:
    body = document_header("Code Repositories", "Local Git", "assurance code repos", ", ".join(roots))
    body += "## Repository Roots\n\n"
    if roots:
        body += "\n".join(f"- `{root}`" for root in roots) + "\n\n"
    else:
        body += "_No repository roots supplied._\n\n"
    body += "## Discovered Repositories\n\n"
    rows = [
        [repo.name, str(repo.path), repo.branch, "dirty" if repo.dirty else "clean"]
        for repo in repositories
    ]
    body += markdown_table(["Repository", "Path", "Branch", "Status"], rows)
    if not repositories:
        body += "_No local Git repositories found._\n"
    return body


def code_search_markdown(result: CodeSearchResult, *, pull_requests: list[PullRequestEvidence] | None = None) -> str:
    body = document_header("Code Evidence", "Local Git", "assurance code search", result.query)
    body += _code_search_body(result, pull_requests=pull_requests or [])
    return body


def code_evidence_section_markdown(
    result: CodeSearchResult | None,
    *,
    requested: bool,
    pull_requests: list[PullRequestEvidence] | None = None,
) -> str:
    if not requested:
        return "_Not requested._\n"
    if result is None:
        return "_No code evidence returned._\n"
    return _code_search_body(result, pull_requests=pull_requests or [])


def _code_search_body(result: CodeSearchResult, *, pull_requests: list[PullRequestEvidence]) -> str:
    body = "### Repository Scope\n\n"
    if result.repositories:
        body += markdown_table(
            ["Repository", "Path", "Branch", "Status"],
            [[repo.name, str(repo.path), repo.branch, "dirty" if repo.dirty else "clean"] for repo in result.repositories],
        )
    else:
        body += "_No repositories selected._\n"
    body += "\n### Local Repository Search\n\n"
    if result.matches:
        grouped = defaultdict(list)
        for match in result.matches:
            grouped[match.repo.name].append(match)
        for repo_name, matches in grouped.items():
            body += f"#### {repo_name}\n\n"
            rows = [
                [str(match.file_path), match.line_number, match.line]
                for match in matches
            ]
            body += markdown_table(["File", "Line", "Match"], rows, max_cell_chars=180)
            body += "\n"
    else:
        body += "_No local code matches found._\n\n"
    if result.truncated:
        body += "_Code search results were truncated at the configured limit._\n\n"
    body += "### Matching Commit Summaries\n\n"
    if result.commits:
        rows = [[commit.repo.name, commit.sha, commit.summary] for commit in result.commits]
        body += markdown_table(["Repository", "Commit", "Summary"], rows, max_cell_chars=180)
    else:
        body += "_No matching commit summaries found._\n"
    body += "\n### Pull Requests\n\n"
    if pull_requests:
        rows = [
            [
                pr.url,
                pr.title,
                pr.state,
                pr.author,
                f"{pr.head_ref} -> {pr.base_ref}".strip(),
                pr.merge_state,
                pr.changed_files if pr.changed_files is not None else "",
                pr.error,
            ]
            for pr in pull_requests
        ]
        body += markdown_table(["URL", "Title", "State", "Author", "Branches", "Merge", "Files", "Error"], rows, max_cell_chars=160)
        for pr in pull_requests:
            if pr.diff:
                body += f"\n#### Diff: {pr.url}\n\n```diff\n{pr.diff}\n```\n"
                if pr.diff_truncated:
                    body += "\n_Diff output was truncated at the configured line limit._\n"
    else:
        body += "_No pull request metadata requested or found._\n"
    body += "\n"
    body += "### Code Evidence Gaps\n\n"
    if result.gaps:
        body += "\n".join(f"- {gap}" for gap in result.gaps) + "\n"
    else:
        body += "_No local code evidence gaps identified._\n"
    return body
