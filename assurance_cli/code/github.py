from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from typing import Callable

from assurance_cli.util.redaction import redact_text


GhRunner = Callable[[list[str]], subprocess.CompletedProcess[str]]
GITHUB_PR_RE = re.compile(r"https://github\.com/([^/\s]+)/([^/\s]+)/pull/(\d+)")


@dataclass(frozen=True)
class PullRequestEvidence:
    url: str
    title: str = ""
    state: str = ""
    author: str = ""
    head_ref: str = ""
    base_ref: str = ""
    merge_state: str = ""
    changed_files: int | None = None
    diff: str = ""
    diff_truncated: bool = False
    error: str = ""


def extract_github_pr_urls(texts: list[str]) -> list[str]:
    urls: list[str] = []
    for text in texts:
        for match in GITHUB_PR_RE.finditer(text or ""):
            url = match.group(0)
            if url not in urls:
                urls.append(url)
    return urls


def get_pull_request_evidence(
    url: str,
    *,
    include_diff: bool = False,
    max_diff_lines: int = 500,
    runner: GhRunner | None = None,
) -> PullRequestEvidence:
    runner = runner or _run_gh
    view_command = [
        "gh",
        "pr",
        "view",
        url,
        "--json",
        "number,title,state,author,headRefName,baseRefName,mergeStateStatus,url,changedFiles",
    ]
    view = runner(view_command)
    if view.returncode != 0:
        return PullRequestEvidence(url=url, error=(view.stderr or view.stdout or "gh pr view failed").strip())
    try:
        payload = json.loads(view.stdout or "{}")
    except json.JSONDecodeError:
        return PullRequestEvidence(url=url, error="gh pr view returned invalid JSON.")
    diff = ""
    diff_truncated = False
    if include_diff:
        diff_result = runner(["gh", "pr", "diff", url])
        if diff_result.returncode != 0:
            return _pull_request_from_payload(url, payload, error=(diff_result.stderr or diff_result.stdout or "gh pr diff failed").strip())
        lines = (diff_result.stdout or "").splitlines()
        if len(lines) > max_diff_lines:
            lines = lines[:max_diff_lines]
            diff_truncated = True
        diff = redact_text("\n".join(lines))
    return _pull_request_from_payload(url, payload, diff=diff, diff_truncated=diff_truncated)


def _pull_request_from_payload(
    url: str,
    payload: dict,
    *,
    diff: str = "",
    diff_truncated: bool = False,
    error: str = "",
) -> PullRequestEvidence:
    author = payload.get("author") or {}
    if isinstance(author, dict):
        author_name = author.get("login") or author.get("name") or ""
    else:
        author_name = str(author)
    return PullRequestEvidence(
        url=str(payload.get("url") or url),
        title=redact_text(str(payload.get("title") or "")),
        state=str(payload.get("state") or ""),
        author=author_name,
        head_ref=str(payload.get("headRefName") or ""),
        base_ref=str(payload.get("baseRefName") or ""),
        merge_state=str(payload.get("mergeStateStatus") or ""),
        changed_files=payload.get("changedFiles") if isinstance(payload.get("changedFiles"), int) else None,
        diff=diff,
        diff_truncated=diff_truncated,
        error=error,
    )


def _run_gh(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, capture_output=True, text=True, check=False)
