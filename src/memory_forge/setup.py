from __future__ import annotations

import argparse
import difflib
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_CODEX_CONFIG = Path.home() / ".codex" / "config.toml"
DEFAULT_MEMORY_DB = Path.home() / ".memory-forge" / "memory.db"


@dataclass(frozen=True)
class SetupResult:
    config_path: Path
    before: str
    after: str

    @property
    def changed(self) -> bool:
        return self.before != self.after

    def diff(self) -> str:
        return "".join(
            difflib.unified_diff(
                self.before.splitlines(keepends=True),
                self.after.splitlines(keepends=True),
                fromfile=f"{self.config_path} (before)",
                tofile=f"{self.config_path} (after)",
            )
        )


def plan_codex_setup(
    config_path: str | Path = DEFAULT_CODEX_CONFIG,
    db_path: str | Path = DEFAULT_MEMORY_DB,
    server_command: str = "memory-forge",
    server_args: list[str] | None = None,
) -> SetupResult:
    """Return the Codex config update needed to use Memory Forge as memory."""
    clean_config_path = Path(config_path).expanduser()
    before = clean_config_path.read_text(encoding="utf-8") if clean_config_path.exists() else ""
    after = configure_codex_text(
        before,
        db_path=str(Path(db_path).expanduser()),
        server_command=server_command,
        server_args=server_args or [],
    )
    return SetupResult(config_path=clean_config_path, before=before, after=after)


def apply_codex_setup(
    config_path: str | Path = DEFAULT_CODEX_CONFIG,
    db_path: str | Path = DEFAULT_MEMORY_DB,
    server_command: str = "memory-forge",
    server_args: list[str] | None = None,
    dry_run: bool = False,
) -> SetupResult:
    result = plan_codex_setup(
        config_path=config_path,
        db_path=db_path,
        server_command=server_command,
        server_args=server_args,
    )
    if result.changed and not dry_run:
        result.config_path.parent.mkdir(parents=True, exist_ok=True)
        result.config_path.write_text(result.after, encoding="utf-8")
    return result


def configure_codex_text(
    config_text: str,
    db_path: str,
    server_command: str,
    server_args: list[str],
) -> str:
    text = config_text.replace("\r\n", "\n")
    text = _upsert_table(text, "features", {"memories": False})
    text = _upsert_table(
        text,
        "memories",
        {
            "use_memories": False,
            "generate_memories": False,
            "disable_on_external_context": True,
        },
    )
    text = _upsert_table(
        text,
        "mcp_servers.memory_forge",
        {
            "command": server_command,
            "args": server_args,
            "startup_timeout_sec": 20,
            "tool_timeout_sec": 60,
            "enabled": True,
        },
    )
    text = _upsert_table(
        text,
        "mcp_servers.memory_forge.env",
        {"MEMORY_FORGE_DB": db_path},
    )
    return text if text.endswith("\n") else f"{text}\n"


def _upsert_table(config_text: str, section: str, values: dict[str, Any]) -> str:
    lines = config_text.splitlines()
    header = f"[{section}]"
    start = next((index for index, line in enumerate(lines) if line.strip() == header), None)

    if start is None:
        if lines and lines[-1].strip():
            lines.append("")
        lines.append(header)
        lines.extend(f"{key} = {_format_value(value)}" for key, value in values.items())
        return "\n".join(lines) + "\n"

    end = start + 1
    while end < len(lines) and not _is_table_header(lines[end]):
        end += 1

    block = lines[start + 1 : end]
    seen = set()
    next_block = []
    for line in block:
        key = _line_key(line)
        if key in values:
            next_block.append(f"{key} = {_format_value(values[key])}")
            seen.add(key)
        else:
            next_block.append(line)

    for key, value in values.items():
        if key not in seen:
            next_block.append(f"{key} = {_format_value(value)}")

    return "\n".join([*lines[: start + 1], *next_block, *lines[end:]]) + "\n"


def _is_table_header(line: str) -> bool:
    stripped = line.strip()
    return stripped.startswith("[") and stripped.endswith("]")


def _line_key(line: str) -> str | None:
    stripped = line.strip()
    if not stripped or stripped.startswith("#") or "=" not in stripped:
        return None
    return stripped.split("=", 1)[0].strip()


def _format_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, list):
        return "[" + ", ".join(_format_value(item) for item in value) + "]"
    return '"' + str(value).replace("\\", "\\\\").replace('"', '\\"') + '"'


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="memory-forge-setup",
        description="Configure local AI clients to use Memory Forge.",
    )
    subparsers = parser.add_subparsers(dest="client", required=True)

    codex = subparsers.add_parser(
        "codex",
        help="Disable Codex built-in memory and register Memory Forge MCP.",
    )
    codex.add_argument("--config", type=Path, default=DEFAULT_CODEX_CONFIG)
    codex.add_argument("--db", type=Path, default=DEFAULT_MEMORY_DB)
    codex.add_argument("--server-command", default="memory-forge")
    codex.add_argument("--server-arg", action="append", default=[])
    codex.add_argument(
        "--from-checkout",
        type=Path,
        help="Use `uv --directory CHECKOUT run memory-forge` as the MCP command.",
    )
    codex.add_argument("--dry-run", action="store_true", help="Print the diff without writing.")
    codex.add_argument(
        "--check",
        action="store_true",
        help="Exit 1 if the Codex config is not already configured.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.client == "codex":
        server_command = args.server_command
        server_args = list(args.server_arg)
        if args.from_checkout:
            server_command = "uv"
            checkout = args.from_checkout.expanduser().resolve()
            server_args = ["--directory", str(checkout), "run", "memory-forge"]

        result = apply_codex_setup(
            config_path=args.config,
            db_path=args.db,
            server_command=server_command,
            server_args=server_args,
            dry_run=args.dry_run or args.check,
        )

        if result.changed:
            print(result.diff() or "Codex config would change.")
            return 1 if args.check else 0

        print(f"Codex config already uses Memory Forge: {result.config_path}")
        return 0

    raise AssertionError(f"Unhandled client: {args.client}")


if __name__ == "__main__":
    raise SystemExit(main())
