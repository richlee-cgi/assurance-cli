import json
import subprocess

from assurance_cli.code.github import extract_github_pr_urls, get_pull_request_evidence
from assurance_cli.code.local import CodeSearchResult
from assurance_cli.code.markdown import code_search_markdown


def test_extract_github_pr_urls_deduplicates() -> None:
    urls = extract_github_pr_urls(
        [
            "See https://github.com/org/repo/pull/123",
            "Again https://github.com/org/repo/pull/123 and https://github.com/org/repo/pull/124",
        ]
    )

    assert urls == ["https://github.com/org/repo/pull/123", "https://github.com/org/repo/pull/124"]


def test_get_pull_request_evidence_with_bounded_diff() -> None:
    calls = []

    def fake_runner(command):
        calls.append(command)
        if command[:3] == ["gh", "pr", "view"]:
            return subprocess.CompletedProcess(
                command,
                0,
                stdout=json.dumps(
                    {
                        "url": "https://github.com/org/repo/pull/123",
                        "title": "Booking change",
                        "state": "MERGED",
                        "author": {"login": "alice"},
                        "headRefName": "feature",
                        "baseRefName": "main",
                        "mergeStateStatus": "CLEAN",
                        "changedFiles": 2,
                    }
                ),
                stderr="",
            )
        return subprocess.CompletedProcess(command, 0, stdout="line1\nline2\nline3\n", stderr="")

    pr = get_pull_request_evidence("https://github.com/org/repo/pull/123", include_diff=True, max_diff_lines=2, runner=fake_runner)

    assert pr.title == "Booking change"
    assert pr.author == "alice"
    assert pr.diff == "line1\nline2"
    assert pr.diff_truncated is True
    assert calls[1] == ["gh", "pr", "diff", "https://github.com/org/repo/pull/123"]


def test_get_pull_request_evidence_reports_failure() -> None:
    def fake_runner(command):
        return subprocess.CompletedProcess(command, 1, stdout="", stderr="not authenticated")

    pr = get_pull_request_evidence("https://github.com/org/repo/pull/123", runner=fake_runner)

    assert pr.error == "not authenticated"


def test_code_search_markdown_uses_longer_outer_fences_for_nested_diff_fences() -> None:
    class FakePr:
        url = "https://github.com/org/repo/pull/123"
        title = "Docs change"
        state = "OPEN"
        author = "alice"
        head_ref = "feature"
        base_ref = "main"
        merge_state = "CLEAN"
        changed_files = 1
        diff = "+```bash\n+curl example\n+```"
        diff_truncated = False
        error = ""

    markdown = code_search_markdown(
        CodeSearchResult(
            query="https://github.com/org/repo/pull/123",
            repositories=[],
            matches=[],
            commits=[],
            gaps=[],
        ),
        pull_requests=[FakePr()],
    )

    assert "````diff" in markdown
    assert "+```bash" in markdown
    assert "+```" in markdown
    assert "\u200b" not in markdown


def test_code_search_markdown_handles_longer_nested_fences() -> None:
    class FakePr:
        url = "https://github.com/org/repo/pull/123"
        title = "Docs change"
        state = "OPEN"
        author = "alice"
        head_ref = "feature"
        base_ref = "main"
        merge_state = "CLEAN"
        changed_files = 1
        diff = "+````markdown\n+content\n+````"
        diff_truncated = False
        error = ""

    markdown = code_search_markdown(
        CodeSearchResult(
            query="https://github.com/org/repo/pull/123",
            repositories=[],
            matches=[],
            commits=[],
            gaps=[],
        ),
        pull_requests=[FakePr()],
    )

    assert "`````diff" in markdown
    assert "+````markdown" in markdown
    assert "\u200b" not in markdown
