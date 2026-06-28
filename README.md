# Memory Forge

Memory Forge is a local-first MCP memory backend for Codex-style AI agents.
It gives compatible clients a small set of tools for saving, searching, and
summarizing durable project memories without sending the database to a cloud
service.

V1 is intentionally boring in the best way: a Python MCP server, SQLite, and
full-text search.

## Features

- Local SQLite database with FTS5 search.
- MCP tools for remember, search, context, update, and forget.
- Soft-delete by default so accidental forgets can be recovered from backups.
- Project, tag, source-agent, and importance metadata.
- Token-budgeted context retrieval to avoid duplicate long-term memory blocks.
- Works with any MCP client that can launch a stdio server.

## Single-Memory Mode

Memory Forge should be the agent's source of truth for durable memory. Do not
also paste a long memory summary into the agent's system prompt or project
instructions, because that makes the model pay for the same memory twice.

Recommended agent instruction:

```text
Use Memory Forge as the only durable memory source. Do not maintain or repeat a
separate long-term memory block in the prompt. When prior context is needed,
call memory_context with a focused query, project, and max_chars budget. Save
new durable facts with memory_remember only when they will help future sessions.
```

Use small `memory_context` budgets by default, then request more only when the
task genuinely needs it. A good starting point is `max_chars: 2000` for normal
coding tasks and `max_chars: 6000` for broad project orientation.

## Install

```powershell
uv sync
```

Run the MCP server:

```powershell
uv run memory-forge
```

By default the database is stored at:

```text
%USERPROFILE%\.memory-forge\memory.db
```

Set a custom path with:

```powershell
$env:MEMORY_FORGE_DB="C:\path\to\memory.db"
uv run memory-forge
```

## MCP Tools

### `memory_remember`

Save a durable memory.

```json
{
  "content": "The API service uses SQLite for local development.",
  "tags": ["api", "local-dev"],
  "project": "example-project",
  "source_agent": "codex",
  "importance": 3
}
```

### `memory_search`

Search memories with optional filters.

```json
{
  "query": "SQLite local development",
  "project": "example-project",
  "tags": ["api"],
  "limit": 10
}
```

### `memory_context`

Return compact prompt-ready context for an agent.

```json
{
  "query": "database setup",
  "project": "example-project",
  "limit": 8,
  "max_chars": 2000
}
```

The response includes `context`, `count`, `max_chars`, `truncated`, and the raw
matching `memories`. Clients should inject only the `context` string into the
working prompt.

### `memory_update`

Update content, tags, project, source agent, or importance.

```json
{
  "memory_id": "memory-id",
  "importance": 5,
  "tags": ["api", "database"]
}
```

### `memory_forget`

Archive by default, or hard-delete only when explicitly requested.

```json
{
  "memory_id": "memory-id",
  "hard_delete": false
}
```

## Codex MCP Example

Add a stdio MCP server entry that launches Memory Forge from this checkout:

```json
{
  "mcpServers": {
    "memory-forge": {
      "command": "uv",
      "args": ["--directory", "C:\\Users\\notal\\Downloads\\Better Memory", "run", "memory-forge"],
      "env": {
        "MEMORY_FORGE_DB": "C:\\Users\\notal\\.memory-forge\\memory.db"
      }
    }
  }
}
```

To make Memory Forge the single durable memory source for Codex, also disable
Codex's built-in memory generation and injection:

```toml
[features]
memories = false

[memories]
use_memories = false
generate_memories = false
disable_on_external_context = true
```

Full local `~/.codex/config.toml` example:

```toml
[features]
memories = false

[memories]
use_memories = false
generate_memories = false
disable_on_external_context = true

[mcp_servers.memory_forge]
command = "uv"
args = ["--directory", "C:\\Users\\notal\\Downloads\\Better Memory", "run", "memory-forge"]
startup_timeout_sec = 20
tool_timeout_sec = 60
enabled = true

[mcp_servers.memory_forge.env]
MEMORY_FORGE_DB = "C:\\Users\\notal\\.memory-forge\\memory.db"
```

Restart Codex after editing config. In the Codex TUI, run `/mcp` to confirm
that `memory_forge` is active.

## Claude Code MCP Example

From this checkout:

```powershell
claude mcp add memory-forge uv -- --directory "C:\Users\notal\Downloads\Better Memory" run memory-forge
```

## Development

```powershell
uv run pytest
```

## Roadmap

- Export and import memories as JSONL.
- Optional semantic search using local embeddings.
- Memory compaction and conflict detection.
- Client-specific install helpers.
