from pathlib import Path

from typer.testing import CliRunner

from assurance_cli.cache import Cache
from assurance_cli.main import app


def _seed_cache(cache_dir: Path) -> str:
    cache = Cache(cache_dir)
    cache_key = cache.key("atlassian/jira/search", {"jql": "project = ABC"})
    cache.set(
        cache_key,
        {"issues": [{"key": "ABC-123", "fields": {"summary": "Example"}}]},
        {"source": "Jira", "endpoint": "/rest/api/3/search"},
    )
    return cache_key


def test_cache_list_verbose(tmp_path: Path) -> None:
    cache_key = _seed_cache(tmp_path)

    result = CliRunner().invoke(app, ["cache", "list", "--cache-dir", str(tmp_path), "--verbose"])

    assert result.exit_code == 0
    assert cache_key in result.output
    assert "Jira" in result.output
    assert "/rest/api/3/search" in result.output


def test_cache_list_raw(tmp_path: Path) -> None:
    cache_key = _seed_cache(tmp_path)

    result = CliRunner().invoke(app, ["cache", "list", "--cache-dir", str(tmp_path), "--raw"])

    assert result.exit_code == 0
    assert cache_key in result.output
    assert '"source": "Jira"' in result.output


def test_cache_show_metadata_only(tmp_path: Path) -> None:
    cache_key = _seed_cache(tmp_path)

    result = CliRunner().invoke(app, ["cache", "show", cache_key, "--cache-dir", str(tmp_path), "--metadata-only"])

    assert result.exit_code == 0
    assert '"cache_key"' in result.output
    assert '"data"' not in result.output


def test_cache_clear_entry(tmp_path: Path) -> None:
    cache_key = _seed_cache(tmp_path)

    result = CliRunner().invoke(app, ["cache", "clear", cache_key, "--cache-dir", str(tmp_path)])

    assert result.exit_code == 0
    assert "Cleared cache entry" in result.output
    assert Cache(tmp_path).list_entries() == []


def test_cache_clear_requires_key_or_all(tmp_path: Path) -> None:
    result = CliRunner().invoke(app, ["cache", "clear", "--cache-dir", str(tmp_path)])

    assert result.exit_code != 0
    assert result.exception is not None
    assert "Provide either a cache key or --all" in str(result.exception)


def test_cache_clear_all(tmp_path: Path) -> None:
    _seed_cache(tmp_path)

    result = CliRunner().invoke(app, ["cache", "clear", "--cache-dir", str(tmp_path), "--all"])

    assert result.exit_code == 0
    assert "Cleared 1 cache entry" in result.output
    assert Cache(tmp_path).list_entries() == []
