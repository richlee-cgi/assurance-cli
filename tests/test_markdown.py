from assurance_cli.markdown import adf_to_markdown, html_to_md


def test_html_to_md() -> None:
    assert "Hello" in html_to_md("<p><strong>Hello</strong></p>")


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

