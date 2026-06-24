from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from markdownify import markdownify as html_to_markdown

from assurance_cli.util.redaction import redact_text


def iso_now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def document_header(title: str, sources: str, command: str, scope: str) -> str:
    return (
        f"# {title}\n\n"
        f"Generated: {iso_now()}\n"
        f"Source system(s): {sources}\n"
        f"Command: `{redact_text(command)}`\n"
        f"Scope: {scope}\n\n"
        "---\n\n"
    )


def html_to_md(html: str | None) -> str:
    if not html:
        return ""
    return html_to_markdown(html, heading_style="ATX").strip()


def adf_to_markdown(node: Any) -> str:
    if not node:
        return ""
    if isinstance(node, str):
        return node
    if isinstance(node, list):
        return "".join(adf_to_markdown(item) for item in node)
    if not isinstance(node, dict):
        return str(node)

    node_type = node.get("type")
    content = node.get("content", [])

    if node_type == "doc":
        return adf_to_markdown(content).strip()
    if node_type == "paragraph":
        return adf_to_markdown(content).strip() + "\n\n"
    if node_type == "text":
        text = node.get("text", "")
        for mark in node.get("marks", []) or []:
            mark_type = mark.get("type")
            if mark_type == "strong":
                text = f"**{text}**"
            elif mark_type == "em":
                text = f"*{text}*"
            elif mark_type == "code":
                text = f"`{text}`"
            elif mark_type == "link":
                href = mark.get("attrs", {}).get("href")
                if href:
                    text = f"[{text}]({href})"
        return text
    if node_type == "hardBreak":
        return "\n"
    if node_type == "heading":
        level = min(max(int(node.get("attrs", {}).get("level", 2)), 1), 6)
        return f"{'#' * level} {adf_to_markdown(content).strip()}\n\n"
    if node_type == "bulletList":
        return "".join(_list_item(item, "- ") for item in content) + "\n"
    if node_type == "orderedList":
        return "".join(_list_item(item, f"{idx}. ") for idx, item in enumerate(content, 1)) + "\n"
    if node_type == "listItem":
        return adf_to_markdown(content).strip()
    if node_type == "codeBlock":
        language = node.get("attrs", {}).get("language") or ""
        return f"```{language}\n{adf_to_markdown(content).strip()}\n```\n\n"
    if node_type == "blockquote":
        text = adf_to_markdown(content).strip().replace("\n", "\n> ")
        return f"> {text}\n\n"
    return adf_to_markdown(content)


def _list_item(item: Any, prefix: str) -> str:
    text = adf_to_markdown(item).strip().replace("\n", "\n  ")
    return f"{prefix}{text}\n"


def fenced_json(value: Any) -> str:
    return "```json\n" + json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n```"


def markdown_table(headers: list[str], rows: list[list[Any]], *, max_cell_chars: int = 120) -> str:
    if not rows:
        return ""
    rendered_headers = [_table_cell(header, max_cell_chars=max_cell_chars) for header in headers]
    lines = [
        "| " + " | ".join(rendered_headers) + " |",
        "| " + " | ".join("---" for _ in rendered_headers) + " |",
    ]
    for row in rows:
        cells = [_table_cell(value, max_cell_chars=max_cell_chars) for value in row]
        if len(cells) < len(rendered_headers):
            cells.extend("" for _ in range(len(rendered_headers) - len(cells)))
        lines.append("| " + " | ".join(cells[: len(rendered_headers)]) + " |")
    return "\n".join(lines) + "\n"


def _table_cell(value: Any, *, max_cell_chars: int) -> str:
    if value is None:
        text = ""
    elif isinstance(value, bool):
        text = "yes" if value else "no"
    elif isinstance(value, (dict, list)):
        text = json.dumps(value, sort_keys=True, ensure_ascii=False)
    else:
        text = str(value)
    text = redact_text(text).replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("|", "\\|").replace("\n", "<br>")
    if max_cell_chars and len(text) > max_cell_chars:
        text = text[: max_cell_chars - 1].rstrip() + "…"
    return text


def write_output(markdown: str, out: Path | None, stdout: bool = True) -> None:
    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(markdown, encoding="utf-8")
    if stdout:
        print(markdown, end="" if markdown.endswith("\n") else "\n")
