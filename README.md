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
- Works with any MCP client that can launch a stdio server.

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
  "limit": 8
}
```

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
