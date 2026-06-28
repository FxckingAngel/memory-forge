# Memory Forge

Memory Forge is a local-first MCP memory backend for MCP-capable AI clients.
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
- Usage estimates on retrieved context so clients can see read cost.
- Active-context compaction through `memory_compact` when clients send the
  working context they want Memory Forge to own.
- Model-window budgeting with `context_window_tokens`,
  `reserved_prompt_tokens`, and `reserved_output_tokens`.
- Fallback retrieval for focused queries that miss but project memory exists.
- Works with any MCP client that can launch a stdio server.

## Memory Budgeting

Memory Forge returns only the focused memory a client asks for. Use small
`memory_context` budgets by default, then request more only when the task needs
broader project orientation. A good starting point is `max_chars: 2000` for
normal coding tasks and `max_chars: 6000` for broad project orientation.

If the client knows the model window, pass `context_window_tokens`,
`reserved_prompt_tokens`, and `reserved_output_tokens` so Memory Forge budgets
retrieved memory against the same window as the model call.

See [Memory Model Guide](docs/memory-model.md) for token-budget guidance and
active-context compaction behavior.

## Install

```powershell
uv sync
```

Run the MCP server:

```powershell
uv run memory-forge
```

Configure Codex to use Memory Forge and disable duplicate built-in memory:

```powershell
uv run memory-forge-setup codex --from-checkout .
```

For an installed release, run:

```powershell
memory-forge-setup codex
```

Preview the config change without writing:

```powershell
memory-forge-setup codex --dry-run
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
  "max_chars": 2000,
  "context_window_tokens": 128000,
  "reserved_prompt_tokens": 24000,
  "reserved_output_tokens": 4000
}
```

The response includes `context`, `count`, `max_chars`, `truncated`, and the raw
matching `memories`. It also includes `usage` with character count and rough
token estimates, including whether the returned memory fits the declared model
window budget. If a focused query misses but project or tag filters can still
return relevant memories, `fallback_used` is `true`. Clients should inject only
the `context` string into the working prompt.

### `memory_compact`

Compact active context supplied by a client and optionally store the compacted
result in Memory Forge.

```json
{
  "active_context": "Current chat notes or working context supplied by the client.",
  "project": "example-project",
  "tags": ["handoff"],
  "source_agent": "codex",
  "max_chars": 2000,
  "context_window_tokens": 128000,
  "reserved_prompt_tokens": 24000,
  "reserved_output_tokens": 4000,
  "save": true
}
```

MCP servers cannot read a client's hidden prompt or chat buffer by themselves.
Clients that want Memory Forge to handle active context should call
`memory_compact` before the working context grows too large, then replace the
bulky active context with only the returned `compacted_context` or saved memory
reference. Appending compacted context while keeping the original transcript
still spends the model window twice.

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

## Development

```powershell
uv run pytest
```

## Client Integrations

Memory Forge's MCP server can only receive context a client explicitly sends.
A richer client integration can handle more memory sources, such as:

- configuring the client to disable duplicate built-in memory;
- installing Memory Forge as the MCP memory backend;
- importing accessible chat history when the user explicitly opts in;
- indexing selected local files or repositories into compact memories.

These integrations should be explicit, local-first, and reversible. Memory Forge
should not silently ingest private chats, secrets, or entire filesystems.

### Codex

`memory-forge-setup codex` updates the local Codex config to:

- disable built-in Codex memory;
- register Memory Forge as the `memory_forge` MCP server;
- point `MEMORY_FORGE_DB` at the local Memory Forge database.

Use `--from-checkout PATH` while developing from a local checkout. Use
`--dry-run` to inspect the diff and `--check` in automation.

### Next Clients

Claude Code is the next planned setup target. Its installer should follow the
same pattern: configure Memory Forge as the memory backend, avoid duplicate
built-in memory where possible, and keep imports or local indexing opt-in.

## Roadmap

- Export and import memories as JSONL.
- Optional semantic search using local embeddings.
- Memory compaction and conflict detection.
- Claude Code setup helper.
- Opt-in Codex history import and selected local-file indexing.
