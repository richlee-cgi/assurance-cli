from assurance_cli.markdown import adf_to_markdown, html_to_md, markdown_table


def test_html_to_md() -> None:
    assert "Hello" in html_to_md("<p><strong>Hello</strong></p>")


def test_html_to_md_ordered_list_start() -> None:
    markdown = html_to_md('<ol start="3"><li>Third</li><li>Fourth</li></ol>')

    assert markdown == "3. Third\n4. Fourth"


def test_html_to_md_separates_adjacent_table_links() -> None:
    markdown = html_to_md(
        '<table><tr><th>Story Link</th></tr>'
        '<tr><td><a href="https://example.atlassian.net/browse/DSP-1">DSP-1</a>'
        '<a href="https://example.atlassian.net/browse/DSP-2">DSP-2</a></td></tr></table>'
    )

    assert "| [DSP-1](https://example.atlassian.net/browse/DSP-1)<br>[DSP-2](https://example.atlassian.net/browse/DSP-2) |" in markdown


def test_adf_to_markdown_basic_marks() -> None:
    doc = {
        "type": "doc",
        "content": [
            {
                "type": "paragraph",
                "content": [
                    {"type": "text", "text": "Hello", "marks": [{"type": "strong"}]},
                    {"type": "text", "text": " world"},
                ],
            }
        ],
    }
    assert adf_to_markdown(doc) == "**Hello** world"


def test_adf_to_markdown_ordered_list_start() -> None:
    doc = {
        "type": "doc",
        "content": [
            {
                "type": "orderedList",
                "attrs": {"order": 3},
                "content": [
                    _adf_list_item("Third"),
                    _adf_list_item("Fourth"),
                ],
            }
        ],
    }

    assert adf_to_markdown(doc) == "3. Third\n4. Fourth"


def test_adf_to_markdown_adjacent_ordered_lists_keep_source_order() -> None:
    doc = {
        "type": "doc",
        "content": [
            {
                "type": "orderedList",
                "attrs": {"order": 1},
                "content": [_adf_list_item("First")],
            },
            {
                "type": "orderedList",
                "attrs": {"order": 2},
                "content": [_adf_list_item("Second")],
            },
        ],
    }

    assert adf_to_markdown(doc) == "1. First\n\n2. Second"


def test_markdown_table_escapes_and_truncates_cells() -> None:
    table = markdown_table(["Name", "Value"], [["A|B", "one\ntwo"], ["Long", "x" * 20]], max_cell_chars=8)

    assert "A\\|B" in table
    assert "one<br>…" in table
    assert "xxxxxxx…" in table


def _adf_list_item(text: str) -> dict:
    return {
        "type": "listItem",
        "content": [
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": text}],
            }
        ],
    }
