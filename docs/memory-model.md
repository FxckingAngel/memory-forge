# Memory Model Guide

Memory Forge is built around one rule:

```text
Durable memory lives in Memory Forge. The prompt gets only the smallest useful
slice of that memory.
```

This avoids the common double-memory problem where an agent injects a long
memory summary and then also retrieves external memory.

## What Counts As Memory

Agents usually have several kinds of context:

- Active chat context: the current conversation and recent tool results.
- Repo context: files the agent reads from disk.
- Durable memory: facts saved for future sessions.
- Retrieved memory: a small selection of durable memory added to the current
  prompt for one task.

Memory Forge owns durable memory, retrieved memory, usage reporting, and
client-supplied active-context compaction. It cannot read a client's hidden chat
buffer by itself; the client must send active context to `memory_compact` when
it wants Memory Forge to take over that state.

## Why Active Chat Context Still Exists

The active chat context is the agent's working area. It contains things like:

- The user's newest request.
- Recent corrections and decisions.
- Command outputs from the current task.
- Code snippets or diffs currently being discussed.

This should stay short-lived. Do not copy the whole active chat into Memory
Forge. Save only stable facts that future sessions should know.

Good durable memories:

- "This project uses Memory Forge as its single durable memory source."
- "Use SQLite FTS for v1 search."
- "Codex built-in memories are disabled on this machine to avoid duplicate
  context."

Bad durable memories:

- Full chat transcripts.
- Temporary command output.
- Every file the agent opened.
- Secrets, tokens, or private credentials.

## Token Usage Rules

Memory Forge reports read usage every time `memory_context` or `memory_compact`
returns text. It cannot see the model provider's exact tokenizer, so it uses
`max_chars` as a predictable budget. A rough planning estimate is:

```text
tokens ~= characters / 4
```

Examples:

- `max_chars: 1000` is roughly 250 tokens.
- `max_chars: 2000` is roughly 500 tokens.
- `max_chars: 6000` is roughly 1500 tokens.

Use the smallest budget that can answer the current question. Increase it only
when the returned `truncated` field is `true` or the task clearly needs broader
project orientation.

Example response fields:

```json
{
  "context": "- [project] Useful memory",
  "max_chars": 1200,
  "truncated": false,
  "usage": {
    "chars": 25,
    "estimated_tokens": 7,
    "max_chars": 1200,
    "max_estimated_tokens": 300
  }
}
```

## Recommended Agent Workflow

At the start of a task:

```json
{
  "project": "memory-forge",
  "query": "focused task keywords",
  "limit": 5,
  "max_chars": 1200
}
```

During the task:

- Read files directly from the repo when exact code matters.
- Call `memory_context` again only when a new topic needs prior knowledge.
- Call `memory_compact` when active chat context should be reduced or handed
  back to Memory Forge.
- Inject only the returned `context` string into the prompt.
- Do not inject the raw `memories` array unless the client is debugging.

At the end of a task:

- Save only durable facts with `memory_remember`.
- Prefer one concise memory over many tiny notes.
- Do not save facts already checked into `README.md`, `AGENTS.md`, or other
  docs unless they are useful as quick recall.

## Avoiding Double Memory

When using Memory Forge, turn off other durable memory systems if the client
supports it.

For Codex:

```toml
[features]
memories = false

[memories]
use_memories = false
generate_memories = false
disable_on_external_context = true
```

Then configure Memory Forge as an MCP server and rely on `memory_context` for
retrieval.

For other clients:

- Disable built-in long-term memory if possible.
- Remove hand-written "memory" sections from system prompts.
- Keep project rules in checked-in docs, not generated memory summaries.
- Add an instruction that Memory Forge is the only durable memory source.

## Compaction

Memory Forge should handle compaction when the client supplies active context
to `memory_compact`. This moves long working context out of the prompt and into
a budgeted compact form.

Compaction may still happen because:

- Some clients do not send hidden active chat context to MCP servers.
- Tool outputs and file excerpts still consume context.
- Current model APIs have finite context windows.
- Some clients compact automatically as part of their runtime.

The goal is not "never compact." The goal is:

- Do not compact durable memory into a giant prompt block.
- Store durable memory externally.
- Retrieve focused memory only when needed.
- Keep active chat context for current work only.

## Open-Source Integration Checklist

For any MCP-capable coding agent:

1. Install and run Memory Forge locally.
2. Configure the client to launch it as a stdio MCP server.
3. Disable the client's built-in durable memory if possible.
4. Add this instruction to the client:

```text
Use Memory Forge as the only durable memory source. Do not maintain or repeat a
separate long-term memory block in the prompt. Retrieve focused context with
memory_context using project/query/max_chars, then inject only the returned
context string. Save new durable facts with memory_remember only when they will
help future sessions.
```

5. Start each task with a small `memory_context` call.
6. Call `memory_compact` before active context becomes too large.
7. Save durable facts at the end of the task.
8. Keep required rules in repo docs so humans and agents can audit them.
