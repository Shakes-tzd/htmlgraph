from __future__ import annotations

import json
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime
from typing import TYPE_CHECKING, Any, Protocol

from rich.console import Console

if TYPE_CHECKING:
    from htmlgraph.sdk import SDK

_console = Console()


class CommandError(Exception):
    """User-facing CLI error with an exit code."""

    def __init__(self, message: str, exit_code: int = 1) -> None:
        super().__init__(message)
        self.exit_code = exit_code


@dataclass
class CommandResult:
    data: Any = None
    text: str | Iterable[str] | None = None
    json_data: Any | None = None


class Formatter(Protocol):
    def output(self, result: CommandResult) -> None: ...


def _serialize_json(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if hasattr(value, "model_dump") and callable(getattr(value, "model_dump")):
        return _serialize_json(value.model_dump())
    if hasattr(value, "to_dict") and callable(getattr(value, "to_dict")):
        return _serialize_json(value.to_dict())
    if isinstance(value, dict):
        return {key: _serialize_json(val) for key, val in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_serialize_json(item) for item in value]
    return value


class JsonFormatter:
    def output(self, result: CommandResult) -> None:
        payload = result.json_data if result.json_data is not None else result.data
        _console.print(json.dumps(_serialize_json(payload), indent=2))


class TextFormatter:
    def output(self, result: CommandResult) -> None:
        if result.text is None:
            if result.data is not None:
                _console.print(result.data)
            return
        if isinstance(result.text, str):
            _console.print(result.text)
            return
        _console.print("\n".join(str(line) for line in result.text))


def get_formatter(format_name: str) -> Formatter:
    if format_name == "json":
        return JsonFormatter()
    if format_name in ("text", "plain", ""):
        return TextFormatter()
    raise CommandError(f"Unknown output format '{format_name}'")


class BaseCommand:
    def __init__(self) -> None:
        self.graph_dir: str | None = None
        self.agent: str | None = None
        self._sdk: SDK | None = None

    def validate(self) -> None:
        return None

    def execute(self) -> CommandResult:
        raise NotImplementedError

    def get_sdk(self) -> Any:
        if self.graph_dir is None:
            raise CommandError("Missing graph directory for command execution.")
        if self._sdk is None:
            from htmlgraph.sdk import SDK

            self._sdk = SDK(directory=self.graph_dir, agent=self.agent)
        return self._sdk

    def run(self, *, graph_dir: str, agent: str | None, output_format: str) -> None:
        self.graph_dir = graph_dir
        self.agent = agent
        try:
            self.validate()
            result = self.execute()
            formatter = get_formatter(output_format)
            formatter.output(result)
        except CommandError as exc:
            error_console = Console(file=sys.stderr)
            error_console.print(f"[red]Error: {exc}[/red]")
            sys.exit(exc.exit_code)
        except ValueError as exc:
            error_console = Console(file=sys.stderr)
            error_console.print(f"[red]Error: {exc}[/red]")
            sys.exit(1)
