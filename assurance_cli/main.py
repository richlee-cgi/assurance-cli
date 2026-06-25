from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from assurance_cli.atlassian.client import AtlassianClient
from assurance_cli.atlassian.confluence import build_cql, get_page, page_id_from_url, search_confluence
from assurance_cli.atlassian.jira import DEFAULT_FIELDS, build_jql, get_issue, search_jira
from assurance_cli.atlassian.markdown import (
    confluence_page_markdown,
    confluence_search_markdown,
    jira_issue_markdown,
    jira_search_markdown,
)
from assurance_cli.azure.cli import az_available, build_resource_graph_query, run_az_json
from assurance_cli.azure.markdown import (
    azure_check_markdown,
    azure_resources_markdown,
    azure_snapshot_markdown,
    function_apps_markdown,
)
from assurance_cli.cache import Cache
from assurance_cli.code.github import extract_github_pr_urls, get_pull_request_evidence
from assurance_cli.code.local import discover_repositories, repo_selectors_from_file, search_repositories, select_repositories
from assurance_cli.code.markdown import code_search_markdown, repositories_markdown
from assurance_cli.config import load_config
from assurance_cli.dataverse.markdown import (
    dataverse_check_markdown,
    dataverse_list_markdown,
    dataverse_snapshot_markdown,
)
from assurance_cli.dataverse.pac import pac_path, run_pac
from assurance_cli.exceptions import AssuranceError, ConfigError
from assurance_cli.markdown import document_header, write_output
from assurance_cli.presets import get_preset, list_presets
from assurance_cli.reports.evidence_pack import (
    combined_evidence_pack_markdown,
    confluence_evidence_pack_markdown,
    jira_evidence_pack_markdown,
)
from assurance_cli.util.redaction import redact

app = typer.Typer(help="Read-only assurance evidence gathering CLI.")
confluence_app = typer.Typer(help="Read-only Confluence retrieval.")
jira_app = typer.Typer(help="Read-only Jira retrieval.")
azure_app = typer.Typer(help="Read-only Azure CLI wrappers.")
dataverse_app = typer.Typer(help="Read-only Dataverse / Power Platform CLI wrappers.")
code_app = typer.Typer(help="Read-only local repository evidence.")
cache_app = typer.Typer(help="Inspect local assurance cache.")
report_app = typer.Typer(help="Compose multi-system evidence reports.")
presets_app = typer.Typer(help="List built-in evidence query presets.")

app.add_typer(confluence_app, name="confluence")
app.add_typer(jira_app, name="jira")
app.add_typer(azure_app, name="azure")
app.add_typer(dataverse_app, name="dataverse")
app.add_typer(code_app, name="code")
app.add_typer(cache_app, name="cache")
app.add_typer(report_app, name="report")
app.add_typer(presets_app, name="presets")

stderr = Console(stderr=True)


def _cache(cache_dir: Path, no_cache: bool) -> Cache:
    return Cache(cache_dir, enabled=not no_cache)


def _client() -> AtlassianClient:
    return AtlassianClient(load_config().atlassian)


def _emit(payload: str | dict, *, raw: bool, out: Optional[Path]) -> None:
    text = json.dumps(redact(payload), indent=2, sort_keys=True, ensure_ascii=False) + "\n" if raw else str(payload)
    write_output(text, out)


def _fetch_confluence_search(
    *,
    config,
    cache: Cache,
    cql: str,
    limit: int,
    expand: str,
    refresh: bool,
) -> dict:
    cache_key = cache.key("atlassian/confluence/search", {"cql": cql, "limit": limit, "expand": expand})
    data = None if refresh else cache.get(cache_key)
    if data is not None:
        return data
    client = AtlassianClient(config)
    try:
        data = search_confluence(client, cql=cql, limit=limit, expand=expand, page_size=config.page_size)
    finally:
        client.close()
    cache.set(cache_key, data, {"source": "Confluence", "endpoint": "/wiki/rest/api/content/search"})
    return data


def _fetch_confluence_page(
    *,
    config,
    cache: Cache,
    page_id: str,
    body_format: str,
    include_comments: bool,
    include_children: bool,
    include_attachments: bool,
    refresh: bool,
) -> dict:
    cache_key = cache.key(
        f"atlassian/confluence/content/{page_id}",
        {
            "body_format": body_format,
            "include_comments": include_comments,
            "include_children": include_children,
            "include_attachments": include_attachments,
        },
    )
    data = None if refresh else cache.get(cache_key)
    if data is not None:
        return data
    client = AtlassianClient(config)
    try:
        data = get_page(
            client,
            page_id=page_id,
            body_format=body_format,
            include_comments=include_comments,
            include_children=include_children,
            include_attachments=include_attachments,
        )
    finally:
        client.close()
    cache.set(cache_key, data, {"source": "Confluence", "endpoint": f"/wiki/rest/api/content/{page_id}"})
    return data


def _fetch_jira_search(
    *,
    config,
    cache: Cache,
    jql: str,
    fields: str,
    limit: int,
    refresh: bool,
) -> dict:
    cache_key = cache.key("atlassian/jira/search", {"jql": jql, "fields": fields, "limit": limit})
    data = None if refresh else cache.get(cache_key)
    if data is not None:
        return data
    client = AtlassianClient(config)
    try:
        data = search_jira(client, jql=jql, fields=fields, limit=limit, page_size=config.page_size)
    finally:
        client.close()
    cache.set(cache_key, data, {"source": "Jira", "endpoint": "/rest/api/3/search"})
    return data


def _fetch_jira_issue(
    *,
    config,
    cache: Cache,
    issue_key: str,
    fields: str,
    include_comments: bool,
    include_changelog: bool,
    refresh: bool,
) -> dict:
    cache_key = cache.key(
        f"atlassian/jira/issue/{issue_key}",
        {"fields": fields, "include_comments": include_comments, "include_changelog": include_changelog},
    )
    issue = None if refresh else cache.get(cache_key)
    if issue is not None:
        return issue
    client = AtlassianClient(config)
    try:
        issue = get_issue(
            client,
            issue_key=issue_key,
            fields=fields,
            include_comments=include_comments,
            include_changelog=include_changelog,
        )
    finally:
        client.close()
    cache.set(cache_key, issue, {"source": "Jira", "endpoint": f"/rest/api/3/issue/{issue_key}"})
    return issue


def _run_dataverse_list_command(
    *,
    command: list[str],
    title: str,
    scope: str,
    out: Optional[Path],
    raw: bool,
    dry_run: bool,
) -> None:
    try:
        result = run_pac(command, dry_run=dry_run)
    except AssuranceError as exc:
        if raw:
            _emit({"error": str(exc), "command": command}, raw=True, out=out)
            return
        body = dataverse_list_markdown(
            title=title,
            payload=f"Warning: {exc}",
            command=" ".join(command),
            scope=scope,
        )
        _emit(body, raw=False, out=out)
        return
    if raw:
        _emit(result.data, raw=True, out=out)
        return
    body = dataverse_list_markdown(title=title, payload=result.data, command=" ".join(result.command), scope=scope)
    _emit(body, raw=False, out=out)


def _azure_topic_evidence_markdown(*, topic: str, limit: int, resource_group: str | None = None) -> tuple[str | None, str | None]:
    try:
        kql = build_resource_graph_query(
            query=topic,
            resource_type=None,
            resource_group=resource_group,
            tags=(),
            limit=limit,
        )
        command = ["az", "graph", "query", "-q", kql, "--first", str(limit)]
        result = run_az_json(command)
        markdown = azure_resources_markdown(
            title="Azure Evidence",
            data=result.data,
            command=" ".join(result.command),
            scope=kql,
        )
        return markdown, None
    except AssuranceError as exc:
        return None, f"Azure evidence retrieval failed: {exc}"


def _dataverse_topic_evidence_markdown() -> tuple[str | None, str | None]:
    warnings: list[str] = []

    def attempt(command: list[str]):
        try:
            return run_pac(command).data
        except AssuranceError as exc:
            warnings.append(f"`{' '.join(command)}` failed: {exc}")
            return None

    auth_profiles = attempt(["pac", "auth", "list"])
    environments = attempt(["pac", "env", "list"])
    solutions = attempt(["pac", "solution", "list"])
    connectors = attempt(["pac", "connector", "list"])
    connections = attempt(["pac", "connection", "list"])
    markdown = dataverse_snapshot_markdown(
        auth_profiles=auth_profiles,
        environments=environments,
        solutions=solutions,
        connectors=connectors,
        connection_refs=connections,
        warnings=warnings,
        command="assurance dataverse snapshot",
    )
    return markdown, None if not warnings else "Dataverse evidence retrieval completed with warnings."


def _code_topic_evidence_markdown(
    *,
    topic: str,
    repo_roots: list[Path],
    repos: list[str],
    repo_file: Path | None,
    limit: int,
    max_file_bytes: int,
    include_prs: bool = False,
    include_diffs: bool = False,
    github_fallback: bool = False,
    max_diff_lines: int = 500,
    linked_texts: list[str] | None = None,
) -> tuple[str | None, list[str]]:
    gaps: list[str] = []
    if not repo_roots:
        return None, ["Code evidence was requested but no --repo-root was supplied."]
    discovered = discover_repositories(repo_roots)
    selectors = [*repos, *repo_selectors_from_file(repo_file)]
    selected, selection_gaps = select_repositories(discovered, selectors)
    gaps.extend(selection_gaps)
    result = search_repositories(topic, selected, limit=limit, max_file_bytes=max_file_bytes)
    gaps.extend(result.gaps)
    pull_requests = []
    if include_prs:
        urls = extract_github_pr_urls(linked_texts or [])
        if not urls:
            gaps.append("PR metadata was requested but no GitHub pull request links were found in gathered evidence.")
        for url in urls:
            pull_request = get_pull_request_evidence(url, include_diff=include_diffs, max_diff_lines=max_diff_lines)
            if pull_request.error:
                gaps.append(f"GitHub PR `{url}` could not be resolved: {pull_request.error}")
            if pull_request.diff_truncated:
                gaps.append(f"Diff evidence for `{url}` was truncated.")
            pull_requests.append(pull_request)
    elif github_fallback:
        gaps.append("GitHub fallback was requested but PR metadata was not enabled.")
    return code_search_markdown(result, pull_requests=pull_requests), gaps


@confluence_app.command("search")
def confluence_search_cmd(
    query: Optional[str] = typer.Argument(None),
    cql: Optional[str] = typer.Option(None, "--cql"),
    space: Optional[str] = typer.Option(None, "--space"),
    content_type: str = typer.Option("page", "--type"),
    updated_after: Optional[str] = typer.Option(None, "--updated-after"),
    updated_before: Optional[str] = typer.Option(None, "--updated-before"),
    limit: int = typer.Option(25, "--limit", min=1),
    expand: str = typer.Option("space,history,version,ancestors", "--expand"),
    out: Optional[Path] = typer.Option(None, "--out"),
    cache_dir: Path = typer.Option(Path(".assurance-cache"), "--cache-dir"),
    no_cache: bool = typer.Option(False, "--no-cache"),
    refresh: bool = typer.Option(False, "--refresh"),
    raw: bool = typer.Option(False, "--raw"),
) -> None:
    config = load_config().atlassian
    selected_space = space or config.default_confluence_space
    final_cql = build_cql(
        query,
        cql=cql,
        space=selected_space,
        content_type=content_type,
        updated_after=updated_after,
        updated_before=updated_before,
    )
    cache = _cache(cache_dir, no_cache)
    data = _fetch_confluence_search(
        config=config,
        cache=cache,
        cql=final_cql,
        limit=limit,
        expand=expand,
        refresh=refresh,
    )
    if raw:
        _emit(data, raw=True, out=out)
        return
    body = document_header("Confluence Search", "Confluence", "assurance confluence search", final_cql)
    body += confluence_search_markdown(data, config.base_url)
    _emit(body, raw=False, out=out)


@confluence_app.command("get")
def confluence_get_cmd(
    page_id: Optional[str] = typer.Option(None, "--id"),
    url: Optional[str] = typer.Option(None, "--url"),
    include_comments: bool = typer.Option(False, "--include-comments"),
    include_children: bool = typer.Option(False, "--include-children"),
    include_attachments: bool = typer.Option(False, "--include-attachments"),
    body_format: str = typer.Option("storage", "--body-format"),
    max_body_chars: int = typer.Option(20000, "--max-body-chars"),
    out: Optional[Path] = typer.Option(None, "--out"),
    cache_dir: Path = typer.Option(Path(".assurance-cache"), "--cache-dir"),
    no_cache: bool = typer.Option(False, "--no-cache"),
    refresh: bool = typer.Option(False, "--refresh"),
    raw: bool = typer.Option(False, "--raw"),
) -> None:
    resolved_id = page_id or (page_id_from_url(url) if url else None)
    if not resolved_id:
        raise ConfigError("Provide --id or a Confluence --url containing a page ID.")
    config = load_config().atlassian
    cache = _cache(cache_dir, no_cache)
    data = _fetch_confluence_page(
        config=config,
        cache=cache,
        page_id=resolved_id,
        body_format=body_format,
        include_comments=include_comments,
        include_children=include_children,
        include_attachments=include_attachments,
        refresh=refresh,
    )
    if raw:
        _emit(data, raw=True, out=out)
        return
    title = data.get("page", {}).get("title", resolved_id)
    body = document_header(f"Confluence Page: {title}", "Confluence", "assurance confluence get", f"Page ID {resolved_id}")
    body += confluence_page_markdown(data, config.base_url, max_body_chars)
    _emit(body, raw=False, out=out)


@confluence_app.command("evidence-pack")
def confluence_evidence_pack_cmd(
    topic: str = typer.Argument(...),
    cql: Optional[str] = typer.Option(None, "--cql"),
    space: Optional[str] = typer.Option(None, "--space"),
    limit: int = typer.Option(10, "--limit", min=1),
    max_page_chars: int = typer.Option(8000, "--max-page-chars"),
    include_comments: bool = typer.Option(False, "--include-comments"),
    include_children: bool = typer.Option(False, "--include-children"),
    include_attachments: bool = typer.Option(False, "--include-attachments"),
    body_format: str = typer.Option("storage", "--body-format"),
    out: Optional[Path] = typer.Option(None, "--out"),
    cache_dir: Path = typer.Option(Path(".assurance-cache"), "--cache-dir"),
    no_cache: bool = typer.Option(False, "--no-cache"),
    refresh: bool = typer.Option(False, "--refresh"),
    raw: bool = typer.Option(False, "--raw"),
) -> None:
    config = load_config().atlassian
    selected_space = space or config.default_confluence_space
    final_cql = build_cql(topic, cql=cql, space=selected_space, content_type="page")
    cache = _cache(cache_dir, no_cache)
    search_data = _fetch_confluence_search(
        config=config,
        cache=cache,
        cql=final_cql,
        limit=limit,
        expand="space,history,version,ancestors",
        refresh=refresh,
    )
    pages = [
        _fetch_confluence_page(
            config=config,
            cache=cache,
            page_id=str(item["id"]),
            body_format=body_format,
            include_comments=include_comments,
            include_children=include_children,
            include_attachments=include_attachments,
            refresh=refresh,
        )
        for item in search_data.get("results", [])
        if item.get("id")
    ]
    if raw:
        _emit({"search": search_data, "pages": pages}, raw=True, out=out)
        return
    body = confluence_evidence_pack_markdown(
        topic=topic,
        cql=final_cql,
        search_results=search_data,
        pages=pages,
        base_url=config.base_url,
        max_page_chars=max_page_chars,
    )
    _emit(body, raw=False, out=out)


@jira_app.command("search")
def jira_search_cmd(
    query: Optional[str] = typer.Argument(None),
    jql: Optional[str] = typer.Option(None, "--jql"),
    project: Optional[str] = typer.Option(None, "--project"),
    status: Optional[str] = typer.Option(None, "--status"),
    issue_type: Optional[str] = typer.Option(None, "--issue-type"),
    label: list[str] = typer.Option([], "--label"),
    component: list[str] = typer.Option([], "--component"),
    updated_after: Optional[str] = typer.Option(None, "--updated-after"),
    updated_before: Optional[str] = typer.Option(None, "--updated-before"),
    order_by: str = typer.Option("updated DESC", "--order-by"),
    fields: str = typer.Option(DEFAULT_FIELDS, "--fields"),
    limit: int = typer.Option(25, "--limit", min=1),
    out: Optional[Path] = typer.Option(None, "--out"),
    cache_dir: Path = typer.Option(Path(".assurance-cache"), "--cache-dir"),
    no_cache: bool = typer.Option(False, "--no-cache"),
    refresh: bool = typer.Option(False, "--refresh"),
    raw: bool = typer.Option(False, "--raw"),
) -> None:
    config = load_config().atlassian
    selected_project = project or config.default_jira_project
    final_jql = build_jql(
        query,
        jql=jql,
        project=selected_project,
        status=status,
        issue_type=issue_type,
        labels=tuple(label),
        components=tuple(component),
        updated_after=updated_after,
        updated_before=updated_before,
        order_by=order_by,
    )
    cache = _cache(cache_dir, no_cache)
    data = _fetch_jira_search(
        config=config,
        cache=cache,
        jql=final_jql,
        fields=fields,
        limit=limit,
        refresh=refresh,
    )
    if raw:
        _emit(data, raw=True, out=out)
        return
    body = document_header("Jira Search", "Jira", "assurance jira search", final_jql)
    body += jira_search_markdown(data, config.base_url)
    _emit(body, raw=False, out=out)


@jira_app.command("get")
def jira_get_cmd(
    issue_keys: list[str] = typer.Argument(...),
    include_comments: bool = typer.Option(False, "--include-comments"),
    comment_limit: int = typer.Option(10, "--comment-limit", min=1),
    include_links: bool = typer.Option(False, "--include-links"),
    include_changelog: bool = typer.Option(False, "--include-changelog"),
    fields: str = typer.Option(DEFAULT_FIELDS, "--fields"),
    out: Optional[Path] = typer.Option(None, "--out"),
    cache_dir: Path = typer.Option(Path(".assurance-cache"), "--cache-dir"),
    no_cache: bool = typer.Option(False, "--no-cache"),
    refresh: bool = typer.Option(False, "--refresh"),
    raw: bool = typer.Option(False, "--raw"),
) -> None:
    config = load_config().atlassian
    cache = _cache(cache_dir, no_cache)
    issues = []
    for issue_key in issue_keys:
        issue = _fetch_jira_issue(
            config=config,
            cache=cache,
            issue_key=issue_key,
            fields=fields,
            include_comments=include_comments,
            include_changelog=include_changelog,
            refresh=refresh,
        )
        issues.append(issue)
    if raw:
        _emit({"issues": issues}, raw=True, out=out)
        return
    body = document_header("Jira Issue Detail", "Jira", "assurance jira get", ", ".join(issue_keys))
    rendered = []
    for issue in issues:
        if not include_links:
            issue = {**issue, "fields": {**issue.get("fields", {}), "issuelinks": []}}
        rendered.append(jira_issue_markdown(issue, config.base_url, comment_limit))
    body += "\n".join(rendered)
    _emit(body, raw=False, out=out)


@jira_app.command("evidence-pack")
def jira_evidence_pack_cmd(
    topic: str = typer.Argument(...),
    jql: Optional[str] = typer.Option(None, "--jql"),
    project: Optional[str] = typer.Option(None, "--project"),
    limit: int = typer.Option(15, "--limit", min=1),
    include_comments: bool = typer.Option(False, "--include-comments"),
    comment_limit: int = typer.Option(10, "--comment-limit", min=1),
    include_changelog: bool = typer.Option(False, "--include-changelog"),
    fields: str = typer.Option(DEFAULT_FIELDS, "--fields"),
    out: Optional[Path] = typer.Option(None, "--out"),
    cache_dir: Path = typer.Option(Path(".assurance-cache"), "--cache-dir"),
    no_cache: bool = typer.Option(False, "--no-cache"),
    refresh: bool = typer.Option(False, "--refresh"),
    raw: bool = typer.Option(False, "--raw"),
) -> None:
    config = load_config().atlassian
    selected_project = project or config.default_jira_project
    final_jql = build_jql(
        topic,
        jql=jql,
        project=selected_project,
        status=None,
        issue_type=None,
        labels=(),
        components=(),
        updated_after=None,
        updated_before=None,
        order_by="updated DESC",
    )
    cache = _cache(cache_dir, no_cache)
    search_data = _fetch_jira_search(
        config=config,
        cache=cache,
        jql=final_jql,
        fields=fields,
        limit=limit,
        refresh=refresh,
    )
    issues = [
        _fetch_jira_issue(
            config=config,
            cache=cache,
            issue_key=str(item["key"]),
            fields=fields,
            include_comments=include_comments,
            include_changelog=include_changelog,
            refresh=refresh,
        )
        for item in search_data.get("issues", [])
        if item.get("key")
    ]
    if raw:
        _emit({"search": search_data, "issues": issues}, raw=True, out=out)
        return
    body = jira_evidence_pack_markdown(
        topic=topic,
        jql=final_jql,
        search_results=search_data,
        issues=issues,
        base_url=config.base_url,
        comment_limit=comment_limit,
    )
    _emit(body, raw=False, out=out)


@azure_app.command("check")
def azure_check_cmd(
    out: Optional[Path] = typer.Option(None, "--out"),
    raw: bool = typer.Option(False, "--raw"),
    dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
    result = run_az_json(["az", "account", "show"], dry_run=dry_run)
    if raw:
        _emit(result.data, raw=True, out=out)
        return
    body = azure_check_markdown(account=result.data if isinstance(result.data, dict) else None, az_path=az_available(), command=" ".join(result.command))
    _emit(body, raw=False, out=out)


@azure_app.command("resource-search")
def azure_resource_search_cmd(
    query: Optional[str] = typer.Argument(None),
    subscription: Optional[str] = typer.Option(None, "--subscription"),
    resource_type: Optional[str] = typer.Option(None, "--type"),
    resource_group: Optional[str] = typer.Option(None, "--resource-group"),
    tag: list[str] = typer.Option([], "--tag"),
    query_file: Optional[Path] = typer.Option(None, "--query-file"),
    limit: int = typer.Option(25, "--limit", min=1),
    out: Optional[Path] = typer.Option(None, "--out"),
    raw: bool = typer.Option(False, "--raw"),
    dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
    if query_file:
        kql = query_file.read_text(encoding="utf-8")
    else:
        kql = build_resource_graph_query(
            query=query,
            resource_type=resource_type,
            resource_group=resource_group,
            tags=tuple(tag),
            limit=limit,
        )
    command = ["az", "graph", "query", "-q", kql, "--first", str(limit)]
    if subscription:
        command.extend(["--subscriptions", subscription])
    result = run_az_json(command, dry_run=dry_run)
    if raw:
        _emit(result.data, raw=True, out=out)
        return
    body = azure_resources_markdown(
        title="Azure Resource Search",
        data=result.data,
        command=" ".join(result.command),
        scope=kql,
    )
    _emit(body, raw=False, out=out)


@azure_app.command("resource-get")
def azure_resource_get_cmd(
    resource_id: str = typer.Option(..., "--id"),
    out: Optional[Path] = typer.Option(None, "--out"),
    raw: bool = typer.Option(False, "--raw"),
    dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
    result = run_az_json(["az", "resource", "show", "--ids", resource_id], dry_run=dry_run)
    if raw:
        _emit(result.data, raw=True, out=out)
        return
    body = azure_resources_markdown(
        title="Azure Resource Detail",
        data=result.data,
        command=" ".join(result.command),
        scope=resource_id,
    )
    _emit(body, raw=False, out=out)


@azure_app.command("functions")
def azure_functions_cmd(
    name: Optional[str] = typer.Option(None, "--name"),
    resource_group: Optional[str] = typer.Option(None, "--resource-group"),
    include_settings: bool = typer.Option(False, "--include-settings"),
    show_setting_values: bool = typer.Option(False, "--show-setting-values"),
    out: Optional[Path] = typer.Option(None, "--out"),
    raw: bool = typer.Option(False, "--raw"),
    dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
    if name:
        if not resource_group:
            raise ConfigError("--resource-group is required when --name is provided.")
        result = run_az_json(["az", "functionapp", "show", "--name", name, "--resource-group", resource_group], dry_run=dry_run)
        apps = [] if result.data is None else [result.data]
    else:
        command = ["az", "functionapp", "list"]
        if resource_group:
            command.extend(["--resource-group", resource_group])
        result = run_az_json(command, dry_run=dry_run)
        apps = result.data if isinstance(result.data, list) else []
    settings_by_app: dict[str, list[dict]] = {}
    setting_errors: dict[str, str] = {}
    if include_settings and not dry_run:
        for app_data in apps:
            app_name = app_data.get("name")
            rg = app_data.get("resourceGroup")
            if app_name and rg:
                try:
                    settings_result = run_az_json(
                        ["az", "functionapp", "config", "appsettings", "list", "--name", app_name, "--resource-group", rg]
                    )
                    settings_by_app[app_name] = settings_result.data if isinstance(settings_result.data, list) else []
                except AssuranceError as exc:
                    setting_errors[app_name] = str(exc)
    payload = {"apps": apps, "settings": settings_by_app}
    if raw:
        _emit(payload, raw=True, out=out)
        return
    body = function_apps_markdown(
        apps=apps,
        settings_by_app=settings_by_app,
        setting_errors=setting_errors,
        show_values=show_setting_values,
        command=" ".join(result.command),
        scope=resource_group or name or "all visible function apps",
    )
    _emit(body, raw=False, out=out)


@azure_app.command("apim")
def azure_apim_cmd(
    name: Optional[str] = typer.Option(None, "--name"),
    resource_group: Optional[str] = typer.Option(None, "--resource-group"),
    include_apis: bool = typer.Option(False, "--include-apis"),
    out: Optional[Path] = typer.Option(None, "--out"),
    raw: bool = typer.Option(False, "--raw"),
    dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
    if name:
        if not resource_group:
            raise ConfigError("--resource-group is required when --name is provided.")
        result = run_az_json(["az", "apim", "show", "--name", name, "--resource-group", resource_group], dry_run=dry_run)
        apims = [] if result.data is None else [result.data]
    else:
        command = ["az", "apim", "list"]
        if resource_group:
            command.extend(["--resource-group", resource_group])
        result = run_az_json(command, dry_run=dry_run)
        apims = result.data if isinstance(result.data, list) else []
    apis_by_apim: dict[str, list[dict]] = {}
    if include_apis and not dry_run:
        for apim in apims:
            apim_name = apim.get("name")
            rg = apim.get("resourceGroup")
            if apim_name and rg:
                api_result = run_az_json(["az", "apim", "api", "list", "--service-name", apim_name, "--resource-group", rg])
                apis_by_apim[apim_name] = api_result.data if isinstance(api_result.data, list) else []
    payload = {"apim": apims, "apis": apis_by_apim}
    if raw:
        _emit(payload, raw=True, out=out)
        return
    body = azure_resources_markdown(
        title="Azure API Management",
        data=apims,
        command=" ".join(result.command),
        scope=resource_group or name or "all visible APIM instances",
    )
    for apim_name, apis in apis_by_apim.items():
        body += f"### APIs: `{apim_name}`\n\n"
        body += "_No APIs returned._\n" if not apis else "\n".join(f"- `{api.get('name')}`: `{api.get('path', '')}`" for api in apis) + "\n"
    _emit(body, raw=False, out=out)


@azure_app.command("role-assignments")
def azure_role_assignments_cmd(
    scope: str = typer.Option(..., "--scope"),
    out: Optional[Path] = typer.Option(None, "--out"),
    raw: bool = typer.Option(False, "--raw"),
    dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
    result = run_az_json(["az", "role", "assignment", "list", "--scope", scope], dry_run=dry_run)
    if raw:
        _emit(result.data, raw=True, out=out)
        return
    body = azure_resources_markdown(
        title="Azure Role Assignments",
        data=result.data,
        command=" ".join(result.command),
        scope=scope,
    )
    _emit(body, raw=False, out=out)


@azure_app.command("snapshot")
def azure_snapshot_cmd(
    resource_group: str = typer.Option(..., "--resource-group"),
    out: Optional[Path] = typer.Option(None, "--out"),
    raw: bool = typer.Option(False, "--raw"),
    dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
    result = run_az_json(["az", "resource", "list", "--resource-group", resource_group], dry_run=dry_run)
    resources = result.data if isinstance(result.data, list) else []
    if raw:
        _emit({"resources": resources}, raw=True, out=out)
        return
    body = azure_snapshot_markdown(resource_group=resource_group, resources=resources, command=" ".join(result.command))
    _emit(body, raw=False, out=out)


@dataverse_app.command("check")
def dataverse_check_cmd(
    out: Optional[Path] = typer.Option(None, "--out"),
    raw: bool = typer.Option(False, "--raw"),
    dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
    result = run_pac(["pac", "auth", "list"], dry_run=dry_run)
    if raw:
        _emit({"pac_path": pac_path(), "auth": result.data}, raw=True, out=out)
        return
    body = dataverse_check_markdown(pac_path=pac_path(), auth_result=result.data, command=" ".join(result.command))
    _emit(body, raw=False, out=out)


@dataverse_app.command("environments")
def dataverse_environments_cmd(
    out: Optional[Path] = typer.Option(None, "--out"),
    raw: bool = typer.Option(False, "--raw"),
    dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
    _run_dataverse_list_command(
        command=["pac", "env", "list"],
        title="Dataverse Environments",
        scope="Visible environments",
        out=out,
        raw=raw,
        dry_run=dry_run,
    )


@dataverse_app.command("solutions")
def dataverse_solutions_cmd(
    environment: Optional[str] = typer.Option(None, "--environment"),
    out: Optional[Path] = typer.Option(None, "--out"),
    raw: bool = typer.Option(False, "--raw"),
    dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
    command = ["pac", "solution", "list"]
    if environment:
        command.extend(["--environment", environment])
    _run_dataverse_list_command(
        command=command,
        title="Dataverse Solutions",
        scope=environment or "Current environment",
        out=out,
        raw=raw,
        dry_run=dry_run,
    )


@dataverse_app.command("connectors")
def dataverse_connectors_cmd(
    out: Optional[Path] = typer.Option(None, "--out"),
    raw: bool = typer.Option(False, "--raw"),
    dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
    _run_dataverse_list_command(
        command=["pac", "connector", "list"],
        title="Power Platform Connectors",
        scope="Current profile",
        out=out,
        raw=raw,
        dry_run=dry_run,
    )


@dataverse_app.command("connections")
def dataverse_connections_cmd(
    out: Optional[Path] = typer.Option(None, "--out"),
    raw: bool = typer.Option(False, "--raw"),
    dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
    _run_dataverse_list_command(
        command=["pac", "connection", "list"],
        title="Power Platform Connections",
        scope="Current profile",
        out=out,
        raw=raw,
        dry_run=dry_run,
    )


@dataverse_app.command("snapshot")
def dataverse_snapshot_cmd(
    out: Optional[Path] = typer.Option(None, "--out"),
    raw: bool = typer.Option(False, "--raw"),
    dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
    warnings: list[str] = []

    def attempt(command: list[str]):
        try:
            return run_pac(command, dry_run=dry_run).data
        except AssuranceError as exc:
            warnings.append(f"`{' '.join(command)}` failed: {exc}")
            return None

    auth_profiles = attempt(["pac", "auth", "list"])
    environments = attempt(["pac", "env", "list"])
    solutions = attempt(["pac", "solution", "list"])
    connectors = attempt(["pac", "connector", "list"])
    connections = attempt(["pac", "connection", "list"])
    payload = {
        "auth_profiles": auth_profiles,
        "environments": environments,
        "solutions": solutions,
        "connectors": connectors,
        "connections": connections,
        "warnings": warnings,
    }
    if raw:
        _emit(payload, raw=True, out=out)
        return
    body = dataverse_snapshot_markdown(
        auth_profiles=auth_profiles,
        environments=environments,
        solutions=solutions,
        connectors=connectors,
        connection_refs=connections,
        warnings=warnings,
        command="assurance dataverse snapshot",
    )
    _emit(body, raw=False, out=out)


@code_app.command("repos")
def code_repos_cmd(
    repo_root: list[Path] = typer.Option([], "--repo-root", help="Directory containing local Git repositories."),
    out: Optional[Path] = typer.Option(None, "--out"),
    raw: bool = typer.Option(False, "--raw"),
) -> None:
    repositories = discover_repositories(repo_root)
    if raw:
        _emit(
            {
                "repositories": [
                    {
                        "name": repo.name,
                        "path": str(repo.path),
                        "branch": repo.branch,
                        "dirty": repo.dirty,
                        "status": repo.status,
                    }
                    for repo in repositories
                ]
            },
            raw=True,
            out=out,
        )
        return
    body = repositories_markdown(repositories, roots=[str(root) for root in repo_root])
    _emit(body, raw=False, out=out)


@code_app.command("search")
def code_search_cmd(
    query: str = typer.Argument(...),
    repo_root: list[Path] = typer.Option([], "--repo-root", help="Directory containing local Git repositories."),
    repo: list[str] = typer.Option([], "--repo", help="Repository name or path to include."),
    repo_file: Optional[Path] = typer.Option(None, "--repo-file", help="Newline-delimited repository selectors."),
    limit: int = typer.Option(30, "--limit", min=1),
    max_file_bytes: int = typer.Option(20_000, "--max-file-bytes", min=1),
    out: Optional[Path] = typer.Option(None, "--out"),
    raw: bool = typer.Option(False, "--raw"),
) -> None:
    repositories = discover_repositories(repo_root)
    selectors = [*repo, *repo_selectors_from_file(repo_file)]
    selected, gaps = select_repositories(repositories, selectors)
    result = search_repositories(query, selected, limit=limit, max_file_bytes=max_file_bytes)
    all_gaps = [*gaps, *result.gaps]
    result = type(result)(
        query=result.query,
        repositories=result.repositories,
        matches=result.matches,
        commits=result.commits,
        gaps=all_gaps,
        truncated=result.truncated,
    )
    if raw:
        _emit(
            {
                "query": result.query,
                "repositories": [
                    {
                        "name": item.name,
                        "path": str(item.path),
                        "branch": item.branch,
                        "dirty": item.dirty,
                    }
                    for item in result.repositories
                ],
                "matches": [
                    {
                        "repo": match.repo.name,
                        "file": str(match.file_path),
                        "line_number": match.line_number,
                        "line": match.line,
                    }
                    for match in result.matches
                ],
                "gaps": result.gaps,
                "truncated": result.truncated,
            },
            raw=True,
            out=out,
        )
        return
    _emit(code_search_markdown(result), raw=False, out=out)


@code_app.command("pr")
def code_pr_cmd(
    url: str = typer.Argument(..., help="GitHub pull request URL."),
    include_diff: bool = typer.Option(False, "--include-diff", help="Include bounded PR diff output."),
    max_diff_lines: int = typer.Option(500, "--max-diff-lines", min=1),
    out: Optional[Path] = typer.Option(None, "--out"),
    raw: bool = typer.Option(False, "--raw"),
) -> None:
    pull_request = get_pull_request_evidence(url, include_diff=include_diff, max_diff_lines=max_diff_lines)
    if raw:
        _emit(pull_request.__dict__, raw=True, out=out)
        return
    empty_result = type(search_repositories("", [], limit=1))(
        query=url,
        repositories=[],
        matches=[],
        commits=[],
        gaps=[f"GitHub PR `{url}` could not be resolved: {pull_request.error}"] if pull_request.error else [],
        truncated=False,
    )
    _emit(code_search_markdown(empty_result, pull_requests=[pull_request]), raw=False, out=out)


@report_app.command("evidence-pack")
def report_evidence_pack_cmd(
    topic: Optional[str] = typer.Argument(None),
    preset: Optional[str] = typer.Option(None, "--preset", help="Use a built-in query preset."),
    confluence_space: Optional[str] = typer.Option(None, "--confluence-space"),
    jira_project: Optional[str] = typer.Option(None, "--jira-project"),
    skip_confluence: bool = typer.Option(False, "--skip-confluence"),
    skip_jira: bool = typer.Option(False, "--skip-jira"),
    include_azure: bool = typer.Option(False, "--include-azure"),
    include_dataverse: bool = typer.Option(False, "--include-dataverse"),
    include_code: bool = typer.Option(False, "--include-code"),
    azure_resource_group: Optional[str] = typer.Option(None, "--azure-resource-group"),
    repo_root: list[Path] = typer.Option([], "--repo-root", help="Directory containing local Git repositories."),
    repo: list[str] = typer.Option([], "--repo", help="Repository name or path to include."),
    repo_file: Optional[Path] = typer.Option(None, "--repo-file", help="Newline-delimited repository selectors."),
    max_file_bytes: int = typer.Option(20_000, "--max-file-bytes", min=1),
    include_prs: bool = typer.Option(False, "--include-prs", help="Resolve GitHub PR links found in gathered evidence."),
    include_diffs: bool = typer.Option(False, "--include-diffs", help="Include bounded PR diffs when resolving PRs."),
    github_fallback: bool = typer.Option(False, "--github-fallback", help="Allow GitHub lookup as an explicit fallback."),
    max_diff_lines: int = typer.Option(500, "--max-diff-lines", min=1),
    limit: int = typer.Option(10, "--limit", min=1),
    max_page_chars: int = typer.Option(8000, "--max-page-chars"),
    include_comments: bool = typer.Option(False, "--include-comments"),
    comment_limit: int = typer.Option(10, "--comment-limit", min=1),
    out: Optional[Path] = typer.Option(None, "--out"),
    cache_dir: Path = typer.Option(Path(".assurance-cache"), "--cache-dir"),
    no_cache: bool = typer.Option(False, "--no-cache"),
    refresh: bool = typer.Option(False, "--refresh"),
) -> None:
    if preset:
        try:
            selected_preset = get_preset(preset)
        except ValueError as exc:
            raise AssuranceError(str(exc)) from exc
        topic = topic or selected_preset.topic
        include_azure = include_azure or selected_preset.include_azure
        include_dataverse = include_dataverse or selected_preset.include_dataverse
        include_comments = include_comments or selected_preset.include_comments
        limit = max(limit, selected_preset.limit)
        max_page_chars = max(max_page_chars, selected_preset.max_page_chars)
    if not topic:
        raise AssuranceError("Provide a topic argument or --preset.")

    config = load_config().atlassian
    cache = _cache(cache_dir, no_cache)
    gaps: list[str] = []
    confluence_body = None
    jira_body = None
    azure_body = None
    dataverse_body = None
    code_body = None

    if not skip_confluence:
        selected_space = confluence_space or config.default_confluence_space
        cql = build_cql(topic, cql=None, space=selected_space, content_type="page")
        confluence_search_data = _fetch_confluence_search(
            config=config,
            cache=cache,
            cql=cql,
            limit=limit,
            expand="space,history,version,ancestors",
            refresh=refresh,
        )
        confluence_pages = [
            _fetch_confluence_page(
                config=config,
                cache=cache,
                page_id=str(item["id"]),
                body_format="storage",
                include_comments=False,
                include_children=False,
                include_attachments=False,
                refresh=refresh,
            )
            for item in confluence_search_data.get("results", [])
            if item.get("id")
        ]
        if not confluence_pages:
            gaps.append("Confluence search returned no pages for the topic.")
        confluence_body = confluence_evidence_pack_markdown(
            topic=topic,
            cql=cql,
            search_results=confluence_search_data,
            pages=confluence_pages,
            base_url=config.base_url,
            max_page_chars=max_page_chars,
        )

    if not skip_jira:
        selected_project = jira_project or config.default_jira_project
        jql = build_jql(
            topic,
            jql=None,
            project=selected_project,
            status=None,
            issue_type=None,
            labels=(),
            components=(),
            updated_after=None,
            updated_before=None,
            order_by="updated DESC",
        )
        jira_search_data = _fetch_jira_search(
            config=config,
            cache=cache,
            jql=jql,
            fields=DEFAULT_FIELDS,
            limit=limit,
            refresh=refresh,
        )
        issues = [
            _fetch_jira_issue(
                config=config,
                cache=cache,
                issue_key=str(item["key"]),
                fields=DEFAULT_FIELDS,
                include_comments=include_comments,
                include_changelog=False,
                refresh=refresh,
            )
            for item in jira_search_data.get("issues", [])
            if item.get("key")
        ]
        if not issues:
            gaps.append("Jira search returned no issues for the topic.")
        jira_body = jira_evidence_pack_markdown(
            topic=topic,
            jql=jql,
            search_results=jira_search_data,
            issues=issues,
            base_url=config.base_url,
            comment_limit=comment_limit,
        )

    if include_azure:
        azure_body, azure_gap = _azure_topic_evidence_markdown(
            topic=topic,
            limit=limit,
            resource_group=azure_resource_group,
        )
        if azure_gap:
            gaps.append(azure_gap)
        if azure_body and "_No Azure resources found._" in azure_body:
            gaps.append("Azure resource search returned no resources for the topic.")

    if include_dataverse:
        dataverse_body, dataverse_gap = _dataverse_topic_evidence_markdown()
        if dataverse_gap:
            gaps.append(dataverse_gap)

    if include_code:
        code_body, code_gaps = _code_topic_evidence_markdown(
            topic=topic,
            repo_roots=repo_root,
            repos=repo,
            repo_file=repo_file,
            limit=limit,
            max_file_bytes=max_file_bytes,
            include_prs=include_prs,
            include_diffs=include_diffs,
            github_fallback=github_fallback,
            max_diff_lines=max_diff_lines,
            linked_texts=[text for text in [confluence_body, jira_body] if text],
        )
        gaps.extend(code_gaps)

    body = combined_evidence_pack_markdown(
        topic=topic,
        confluence_markdown=confluence_body,
        jira_markdown=jira_body,
        azure_markdown=azure_body,
        dataverse_markdown=dataverse_body,
        code_markdown=code_body,
        azure_requested=include_azure,
        dataverse_requested=include_dataverse,
        code_requested=include_code,
        gaps=gaps,
    )
    _emit(body, raw=False, out=out)


@cache_app.command("list")
def cache_list(
    cache_dir: Path = typer.Option(Path(".assurance-cache"), "--cache-dir"),
    verbose: bool = typer.Option(False, "--verbose"),
    raw: bool = typer.Option(False, "--raw"),
) -> None:
    cache = Cache(cache_dir)
    entries = cache.list_entries()
    if not entries:
        typer.echo("_No cache entries found._")
        return
    if raw:
        _emit({"entries": [cache.metadata_for_path(path) for path in entries]}, raw=True, out=None)
        return
    for path in entries:
        if not verbose:
            typer.echo(cache.key_for_path(path))
            continue
        metadata = cache.metadata_for_path(path)
        source = metadata.get("source") or "-"
        endpoint = metadata.get("endpoint") or "-"
        timestamp = metadata.get("timestamp") or "-"
        typer.echo(f"{metadata['cache_key']}\t{timestamp}\t{source}\t{endpoint}\t{metadata['size_bytes']} bytes")


@cache_app.command("show")
def cache_show(
    cache_key: str,
    cache_dir: Path = typer.Option(Path(".assurance-cache"), "--cache-dir"),
    metadata_only: bool = typer.Option(False, "--metadata-only"),
) -> None:
    cache = Cache(cache_dir)
    try:
        envelope = cache.read_envelope(cache_key)
    except FileNotFoundError as exc:
        raise AssuranceError(f"Cache entry not found: {cache_key}")
    if metadata_only:
        envelope = {key: value for key, value in envelope.items() if key != "data"}
    typer.echo(json.dumps(redact(envelope), indent=2, sort_keys=True, ensure_ascii=False))


@cache_app.command("clear")
def cache_clear(
    cache_key: Optional[str] = typer.Argument(None),
    all_entries: bool = typer.Option(False, "--all"),
    cache_dir: Path = typer.Option(Path(".assurance-cache"), "--cache-dir"),
) -> None:
    if all_entries == bool(cache_key):
        raise AssuranceError("Provide either a cache key or --all.")
    cache = Cache(cache_dir)
    if all_entries:
        count = cache.clear_all()
        typer.echo(f"Cleared {count} cache entr{'y' if count == 1 else 'ies'}.")
        return
    assert cache_key is not None
    if not cache.clear(cache_key):
        raise AssuranceError(f"Cache entry not found: {cache_key}")
    typer.echo(f"Cleared cache entry: {cache_key}")


@presets_app.command("list")
def presets_list(raw: bool = typer.Option(False, "--raw")) -> None:
    presets = list_presets()
    if raw:
        _emit({"presets": [preset.__dict__ for preset in presets]}, raw=True, out=None)
        return
    lines = ["# Evidence Presets", ""]
    for preset in presets:
        lines.append(f"- `{preset.name}`: {preset.summary}")
        lines.append(f"  - Topic: `{preset.topic}`")
        lines.append(f"  - Azure: `{'yes' if preset.include_azure else 'no'}`")
        lines.append(f"  - Dataverse: `{'yes' if preset.include_dataverse else 'no'}`")
    typer.echo("\n".join(lines))


@presets_app.command("show")
def presets_show(name: str, raw: bool = typer.Option(False, "--raw")) -> None:
    try:
        preset = get_preset(name)
    except ValueError as exc:
        raise AssuranceError(str(exc)) from exc
    if raw:
        _emit(preset.__dict__, raw=True, out=None)
        return
    typer.echo(
        "\n".join(
            [
                f"# Evidence Preset: {preset.name}",
                "",
                preset.summary,
                "",
                f"- Topic: `{preset.topic}`",
                f"- Azure: `{'yes' if preset.include_azure else 'no'}`",
                f"- Dataverse: `{'yes' if preset.include_dataverse else 'no'}`",
                f"- Include comments: `{'yes' if preset.include_comments else 'no'}`",
                f"- Limit: `{preset.limit}`",
            ]
        )
    )


def main() -> int:
    try:
        app()
    except ConfigError as exc:
        stderr.print(str(exc))
        return exc.exit_code
    except AssuranceError as exc:
        stderr.print(str(exc))
        return exc.exit_code
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
