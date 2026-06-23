from assurance_cli.util.redaction import REDACTION_MARKER, redact, redact_text


def test_redacts_sensitive_keys() -> None:
    value = redact({"api_token": "abc", "nested": {"password": "secret"}, "safe": "visible"})
    assert value["api_token"] == REDACTION_MARKER
    assert value["nested"]["password"] == REDACTION_MARKER
    assert value["safe"] == "visible"


def test_redacts_bearer_text() -> None:
    assert redact_text("Authorization: Bearer abc.def") == f"Authorization: Bearer {REDACTION_MARKER}"

