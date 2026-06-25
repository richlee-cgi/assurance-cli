import json
import subprocess

from assurance_cli.code.github import extract_github_pr_urls, get_pull_request_evidence


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
