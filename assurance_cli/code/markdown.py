from __future__ import annotations

from collections import defaultdict

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


def code_search_markdown(result: CodeSearchResult) -> str:
    body = document_header("Code Evidence", "Local Git", "assurance code search", result.query)
    body += _code_search_body(result)
    return body


def code_evidence_section_markdown(result: CodeSearchResult | None, *, requested: bool) -> str:
    if not requested:
        return "_Not requested._\n"
    if result is None:
        return "_No code evidence returned._\n"
    return _code_search_body(result)


def _code_search_body(result: CodeSearchResult) -> str:
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
    body += "### Code Evidence Gaps\n\n"
    if result.gaps:
        body += "\n".join(f"- {gap}" for gap in result.gaps) + "\n"
    else:
        body += "_No local code evidence gaps identified._\n"
    return body
