from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from assurance_cli.exceptions import AssuranceError, UnsafeCommandError
from assurance_cli.util.redaction import redact_text

ALLOWED_PREFIXES: tuple[tuple[str, ...], ...] = (
    ("pac", "auth", "list"),
    ("pac", "org", "list"),
    ("pac", "env", "list"),
    ("pac", "solution", "list"),
    ("pac", "connector", "list"),
    ("pac", "connection", "list"),
    ("pac", "help"),
)

BLOCKED_TOKENS = {
    "activate",
    "add",
    "apply",
    "assign",
    "clone",
    "create",
    "delete",
    "deploy",
    "disable",
    "enable",
    "export",
    "import",
    "install",
    "publish",
    "push",
    "remove",
    "reset",
    "set",
    "sync",
    "update",
    "upgrade",
}


@dataclass(frozen=True)
class PacCommandResult:
    command: list[str]
    data: Any
    stdout: str
    stderr: str
    parsed_json: bool


def pac_path() -> str | None:
    found = shutil.which("pac")
    if found:
        return found
    dotnet_tool = Path.home() / ".dotnet" / "tools" / "pac"
    if dotnet_tool.exists():
        return str(dotnet_tool)
    return None


def validate_pac_command(command: list[str]) -> None:
    if not command or command[0] != "pac":
        raise UnsafeCommandError("Blocked unsafe command: Dataverse wrapper only runs pac commands.")
    tokens = {part.lower() for part in command[1:] if not part.startswith("-")}
    blocked = sorted(tokens & BLOCKED_TOKENS)
    if blocked:
        raise UnsafeCommandError(
            f"Blocked unsafe command: {' '.join(command)}\n"
            f"Blocked token(s): {', '.join(blocked)}. Only read-only pac commands are allowed."
        )
    if not any(_starts_with(command, prefix) for prefix in ALLOWED_PREFIXES):
        raise UnsafeCommandError(
            f"Blocked unsafe command: {' '.join(command)}\n"
            "Only explicitly allowlisted pac commands are allowed in v1."
        )


def run_pac(command: list[str], *, try_json: bool = True, dry_run: bool = False) -> PacCommandResult:
    validate_pac_command(command)
    executable = pac_path()
    if dry_run:
        return PacCommandResult(command=command, data={"dry_run": True, "command": command}, stdout="", stderr="", parsed_json=True)
    if not executable:
        raise AssuranceError("Power Platform CLI not found on PATH or ~/.dotnet/tools/pac.")
    actual = [executable, *command[1:]]
    if try_json and "-o" not in actual and "--output" not in actual:
        actual.extend(["--output", "json"])
    env = {**os.environ, "PATH": f"{os.environ.get('PATH', '')}:{Path.home() / '.dotnet' / 'tools'}"}
    completed = subprocess.run(actual, capture_output=True, text=True, check=False, env=env)
    stdout = redact_text(completed.stdout.strip())
    stderr = redact_text(completed.stderr.strip())
    if completed.returncode != 0 and try_json:
        # Some pac commands/versions do not support --output json. Retry once as text.
        return run_pac(command, try_json=False, dry_run=False)
    if completed.returncode != 0:
        message = stderr or stdout or f"pac exited with {completed.returncode}"
        raise AssuranceError(f"Power Platform CLI command failed: {message}")
    if try_json and stdout:
        try:
            return PacCommandResult(command=command, data=json.loads(stdout), stdout=stdout, stderr=stderr, parsed_json=True)
        except json.JSONDecodeError:
            pass
    return PacCommandResult(command=command, data=stdout, stdout=stdout, stderr=stderr, parsed_json=False)


def _starts_with(command: list[str], prefix: tuple[str, ...]) -> bool:
    return tuple(command[: len(prefix)]) == prefix

