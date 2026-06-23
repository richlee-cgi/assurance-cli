from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

from assurance_cli.exceptions import ConfigError


@dataclass(frozen=True)
class AtlassianConfig:
    base_url: str
    email: str
    api_token: str
    default_confluence_space: str | None
    default_jira_project: str | None
    page_size: int
    max_results: int


@dataclass(frozen=True)
class AppConfig:
    atlassian: AtlassianConfig


def load_config() -> AppConfig:
    load_dotenv()
    base_url = _env_required("ATLASSIAN_BASE_URL").rstrip("/")
    return AppConfig(
        atlassian=AtlassianConfig(
            base_url=base_url,
            email=_env_required("ATLASSIAN_EMAIL"),
            api_token=_env_required("ATLASSIAN_API_TOKEN"),
            default_confluence_space=_env_optional("ATLASSIAN_DEFAULT_CONFLUENCE_SPACE"),
            default_jira_project=_env_optional("ATLASSIAN_DEFAULT_JIRA_PROJECT"),
            page_size=_env_int("ATLASSIAN_PAGE_SIZE", 25),
            max_results=_env_int("ATLASSIAN_MAX_RESULTS", 100),
        )
    )


def _env_required(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ConfigError(f"Configuration error: {name} is not set.")
    return value


def _env_optional(name: str) -> str | None:
    value = os.getenv(name)
    return value or None


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if not value:
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise ConfigError(f"Configuration error: {name} must be an integer.") from exc

