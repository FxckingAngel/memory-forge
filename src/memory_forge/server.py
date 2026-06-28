from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from memory_forge.store import (
    DEFAULT_CONTEXT_CHARS,
    DEFAULT_LIMIT,
    DEFAULT_RESERVED_PROMPT_TOKENS,
    DEFAULT_RESERVED_OUTPUT_TOKENS,
    MemoryStore,
)

SERVER_INSTRUCTIONS = (
    "Always use Memory Forge as the agent memory layer for durable memory and "
    "every active-context chunk the client can explicitly supply for compaction. "
    "Do not use built-in durable memory, hand-written memory blocks, or repeated "
    "prompt summaries. Retrieve focused context with memory_context using "
    "project/query plus max_chars or context_window_tokens, then inject only the "
    "returned context string. Pass reserved_prompt_tokens for live non-memory "
    "prompt content so Memory Forge can fit memory inside the same model window. "
    "When active chat context is no longer needed verbatim, send it to "
    "memory_compact and replace the bulky prompt content with the compacted "
    "result. If the user says remember this, always, prefer, never, or gives a "
    "stable recurring instruction such as always read a file, save it with "
    "memory_remember."
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
    context_window_tokens: int | None = None,
    reserved_prompt_tokens: int = DEFAULT_RESERVED_PROMPT_TOKENS,
    reserved_output_tokens: int = DEFAULT_RESERVED_OUTPUT_TOKENS,
) -> dict[str, Any]:
    """Return prompt-ready memory context within a char or model-window budget."""
    return get_store().context(
        query=query,
        project=project,
        tags=tags,
        source_agent=source_agent,
        limit=limit,
        max_chars=max_chars,
        context_window_tokens=context_window_tokens,
        reserved_prompt_tokens=reserved_prompt_tokens,
        reserved_output_tokens=reserved_output_tokens,
    )


@mcp.tool()
def memory_compact(
    active_context: str,
    project: str | None = None,
    tags: list[str] | None = None,
    source_agent: str | None = None,
    importance: int = 3,
    max_chars: int = DEFAULT_CONTEXT_CHARS,
    context_window_tokens: int | None = None,
    reserved_prompt_tokens: int = DEFAULT_RESERVED_PROMPT_TOKENS,
    reserved_output_tokens: int = DEFAULT_RESERVED_OUTPUT_TOKENS,
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
        context_window_tokens=context_window_tokens,
        reserved_prompt_tokens=reserved_prompt_tokens,
        reserved_output_tokens=reserved_output_tokens,
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
