from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from assurance_cli.util.redaction import redact_text


SKIP_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "node_modules",
    ".terraform",
    "dist",
    "build",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
}

SKIP_SUFFIXES = {
    ".7z",
    ".avif",
    ".bmp",
    ".class",
    ".dll",
    ".docx",
    ".exe",
    ".gif",
    ".ico",
    ".jar",
    ".jpeg",
    ".jpg",
    ".lock",
    ".mov",
    ".mp3",
    ".mp4",
    ".pdf",
    ".png",
    ".pyc",
    ".so",
    ".webp",
    ".zip",
}

GitRunner = Callable[[list[str]], subprocess.CompletedProcess[str]]


@dataclass(frozen=True)
class Repository:
    name: str
    path: Path
    branch: str
    dirty: bool
    status: str


@dataclass(frozen=True)
class CodeMatch:
    repo: Repository
    file_path: Path
    line_number: int
    line: str


@dataclass(frozen=True)
class CommitMatch:
    repo: Repository
    sha: str
    summary: str


@dataclass(frozen=True)
class CodeSearchResult:
    query: str
    repositories: list[Repository]
    matches: list[CodeMatch]
    commits: list[CommitMatch]
    gaps: list[str]
    truncated: bool = False


def discover_repositories(repo_roots: list[Path], *, runner: GitRunner | None = None) -> list[Repository]:
    repos: dict[Path, Repository] = {}
    for root in repo_roots:
        selected_root = root.expanduser()
        if not selected_root.exists():
            continue
        if _is_git_repo(selected_root):
            repo = repository_metadata(selected_root, runner=runner)
            repos[repo.path] = repo
            continue
        for git_dir in selected_root.rglob(".git"):
            repo_path = git_dir.parent
            if any(part in SKIP_DIRS - {".git"} for part in repo_path.relative_to(selected_root).parts):
                continue
            repo = repository_metadata(repo_path, runner=runner)
            repos[repo.path] = repo
    return sorted(repos.values(), key=lambda repo: str(repo.path).lower())


def select_repositories(repositories: list[Repository], selectors: list[str]) -> tuple[list[Repository], list[str]]:
    if not selectors:
        return repositories, []
    selected: list[Repository] = []
    gaps: list[str] = []
    by_name = {repo.name: repo for repo in repositories}
    by_path = {str(repo.path): repo for repo in repositories}
    for selector in selectors:
        repo = by_name.get(selector) or by_path.get(selector) or _match_path_suffix(repositories, selector)
        if repo:
            if repo not in selected:
                selected.append(repo)
        else:
            gaps.append(f"Selected repository `{selector}` was not found locally.")
    return selected, gaps


def search_repositories(
    query: str,
    repositories: list[Repository],
    *,
    limit: int,
    max_file_bytes: int = 20_000,
) -> CodeSearchResult:
    matches: list[CodeMatch] = []
    commits: list[CommitMatch] = []
    gaps: list[str] = []
    lowered_query = query.lower()
    truncated = False
    if not repositories:
        gaps.append("No local repositories were selected.")
    for repo in repositories:
        if repo.dirty:
            gaps.append(f"Repository `{repo.name}` has local uncommitted changes.")
        commits.extend(search_commits(query, repo, limit=5))
        for file_path in _iter_candidate_files(repo.path):
            if len(matches) >= limit:
                truncated = True
                break
            try:
                if file_path.stat().st_size > max_file_bytes:
                    continue
                lines = file_path.read_text(encoding="utf-8").splitlines()
            except (OSError, UnicodeDecodeError):
                continue
            for idx, line in enumerate(lines, 1):
                if lowered_query in line.lower():
                    matches.append(CodeMatch(repo=repo, file_path=file_path.relative_to(repo.path), line_number=idx, line=redact_text(line.strip())))
                    if len(matches) >= limit:
                        truncated = True
                        break
            if len(matches) >= limit:
                break
    if not matches and repositories:
        gaps.append("Local code search returned no matches for the topic.")
    return CodeSearchResult(query=query, repositories=repositories, matches=matches, commits=commits, gaps=gaps, truncated=truncated)


def search_commits(query: str, repo: Repository, *, limit: int, runner: GitRunner | None = None) -> list[CommitMatch]:
    runner = runner or _run_git
    result = runner(
        [
            "git",
            "-C",
            str(repo.path),
            "log",
            "--oneline",
            "--decorate",
            "--max-count",
            str(limit),
            "--grep",
            query,
        ]
    )
    if result.returncode != 0 or not result.stdout:
        return []
    commits = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        sha, _, summary = line.partition(" ")
        commits.append(CommitMatch(repo=repo, sha=sha, summary=redact_text(summary.strip())))
    return commits


def repository_metadata(repo_path: Path, *, runner: GitRunner | None = None) -> Repository:
    runner = runner or _run_git
    path = repo_path.resolve()
    branch_result = runner(["git", "-C", str(path), "branch", "--show-current"])
    branch = (branch_result.stdout or "").strip() or "unknown"
    status_result = runner(["git", "-C", str(path), "status", "--short"])
    status = (status_result.stdout or "").strip()
    return Repository(name=path.name, path=path, branch=branch, dirty=bool(status), status=status)


def repo_selectors_from_file(path: Path | None) -> list[str]:
    if not path:
        return []
    return [
        line.strip()
        for line in path.expanduser().read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]


def _is_git_repo(path: Path) -> bool:
    return (path / ".git").exists()


def _match_path_suffix(repositories: list[Repository], selector: str) -> Repository | None:
    normalized = selector.rstrip("/")
    matches = [repo for repo in repositories if str(repo.path).endswith(normalized)]
    return matches[0] if len(matches) == 1 else None


def _iter_candidate_files(repo_path: Path):
    for path in repo_path.rglob("*"):
        if not path.is_file():
            continue
        relative_parts = path.relative_to(repo_path).parts
        if any(part in SKIP_DIRS for part in relative_parts):
            continue
        if path.suffix.lower() in SKIP_SUFFIXES:
            continue
        yield path


def _run_git(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, capture_output=True, text=True, check=False)
