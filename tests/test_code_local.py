import subprocess
from pathlib import Path

from assurance_cli.code.local import discover_repositories, search_repositories, select_repositories
from assurance_cli.code.markdown import code_search_markdown


def test_discover_repositories_and_search(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path / "booking-service")
    (repo / "README.md").write_text("Booking allocation rules live here.\n", encoding="utf-8")
    (repo / "ignored.lock").write_text("Booking should not be searched.\n", encoding="utf-8")

    repositories = discover_repositories([tmp_path])
    selected, gaps = select_repositories(repositories, ["booking-service"])
    result = search_repositories("Booking", selected, limit=10)

    assert gaps == []
    assert len(repositories) == 1
    assert repositories[0].name == "booking-service"
    assert repositories[0].dirty is True
    assert len(result.matches) == 1
    assert result.matches[0].file_path == Path("README.md")
    assert "uncommitted changes" in result.gaps[0]


def test_code_search_markdown_reports_matches(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path / "booking-service")
    (repo / "app.py").write_text("def booking_allocation():\n    return True\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "app.py"], capture_output=True, text=True, check=True)
    subprocess.run(["git", "-C", str(repo), "-c", "user.email=test@example.com", "-c", "user.name=Test", "commit", "-m", "Add booking allocation"], capture_output=True, text=True, check=True)
    repositories = discover_repositories([tmp_path])
    result = search_repositories("booking", repositories, limit=10)

    markdown = code_search_markdown(result)

    assert "# Code Evidence" in markdown
    assert "booking-service" in markdown
    assert "app.py" in markdown
    assert "booking_allocation" in markdown
    assert "Add booking allocation" in markdown


def _init_repo(path: Path) -> Path:
    path.mkdir()
    subprocess.run(["git", "init", str(path)], capture_output=True, text=True, check=True)
    return path
