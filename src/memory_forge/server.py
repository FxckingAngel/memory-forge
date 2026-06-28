from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from memory_forge.store import DEFAULT_CONTEXT_CHARS, DEFAULT_LIMIT, MemoryStore

SERVER_INSTRUCTIONS = (
    "Use Memory Forge as the only durable memory source. Do not maintain or "
    "repeat a separate long-term memory block in the prompt. Retrieve focused "
    "context with memory_context using project/query/max_chars, then inject "
    "only the returned context string. When active chat context grows large, "
    "send it to memory_compact instead of carrying it forever. Save new durable "
    "facts with memory_remember only when they will help future sessions."
)

mcp = FastMCP("Memory Forge", instructions=SERVER_INSTRUCTIONS)


def default_db_path() -> Path:
    configured = os.getenv("MEMORY_FORGE_DB")
    if configured:
        return Path(configured).expanduser()
    return Path.home() / ".memory-forge" / "memory.db"


def get_store() -> MemoryStore:
    return MemoryStore(default_db_path())


@mcp.tool()
def memory_remember(
    content: str,
    tags: list[str] | None = None,
    project: str | None = None,
    source_agent: str | None = None,
    importance: int = 3,
) -> dict[str, Any]:
    """Save a durable local memory."""
    return get_store().remember(
        content=content,
        tags=tags,
        project=project,
        source_agent=source_agent,
        importance=importance,
    ).to_dict()


@mcp.tool()
def memory_search(
    query: str | None = None,
    project: str | None = None,
    tags: list[str] | None = None,
    source_agent: str | None = None,
    include_archived: bool = False,
    limit: int = DEFAULT_LIMIT,
) -> list[dict[str, Any]]:
    """Search local memories with optional filters."""
    return [
        memory.to_dict()
        for memory in get_store().search(
            query=query,
            project=project,
            tags=tags,
            source_agent=source_agent,
            include_archived=include_archived,
            limit=limit,
        )
    ]


@mcp.tool()
def memory_context(
    query: str | None = None,
    project: str | None = None,
    tags: list[str] | None = None,
    source_agent: str | None = None,
    limit: int = 8,
    max_chars: int = DEFAULT_CONTEXT_CHARS,
) -> dict[str, Any]:
    """Return compact prompt-ready memory context within a character budget."""
    return get_store().context(
        query=query,
        project=project,
        tags=tags,
        source_agent=source_agent,
        limit=limit,
        max_chars=max_chars,
    )


@mcp.tool()
def memory_compact(
    active_context: str,
    project: str | None = None,
    tags: list[str] | None = None,
    source_agent: str | None = None,
    importance: int = 3,
    max_chars: int = DEFAULT_CONTEXT_CHARS,
    save: bool = False,
) -> dict[str, Any]:
    """Compact active context supplied by a client and optionally store it."""
    return get_store().compact(
        active_context=active_context,
        project=project,
        tags=tags,
        source_agent=source_agent,
        importance=importance,
        max_chars=max_chars,
        save=save,
    )


@mcp.tool()
def memory_update(
    memory_id: str,
    content: str | None = None,
    tags: list[str] | None = None,
    project: str | None = None,
    source_agent: str | None = None,
    importance: int | None = None,
) -> dict[str, Any]:
    """Update an existing local memory."""
    return get_store().update(
        memory_id=memory_id,
        content=content,
        tags=tags,
        project=project,
        source_agent=source_agent,
        importance=importance,
    ).to_dict()


@mcp.tool()
def memory_forget(memory_id: str, hard_delete: bool = False) -> dict[str, Any]:
    """Archive a memory by default, or hard-delete when requested."""
    return get_store().forget(memory_id=memory_id, hard_delete=hard_delete)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
