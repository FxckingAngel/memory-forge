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

Memory Forge owns durable memory, retrieved memory, usage reporting, and every
active-context chunk the client can explicitly supply for compaction. It cannot
read a client's hidden chat buffer by itself; the client must send active
context to `memory_compact` when it wants Memory Forge to take over that state.
After compaction, the client must replace the bulky active context with the
compacted result or a saved memory reference; keeping both still fills the model
window.

## Why Active Chat Context Still Exists

The active chat context is the agent's working area. It contains things like:

- The user's newest request.
- Recent corrections and decisions.
- Command outputs from the current task.
- Code snippets or diffs currently being discussed.

This should stay short-lived. Do not save the whole active chat as durable
memory. For usage reduction, compact bulky active context as soon as it is no
longer needed verbatim, then keep only the compacted result in the prompt. Save
only stable facts that future sessions should know.

Good durable memories:

- "This project uses Memory Forge as its single durable memory source."
- "Use SQLite FTS for v1 search."
- "The local client disables built-in memories to avoid duplicate context."

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

If the client knows the model context window, use model-window budgeting instead
of guessing only with `max_chars`:

```json
{
  "context_window_tokens": 128000,
  "reserved_prompt_tokens": 24000,
  "reserved_output_tokens": 4000,
  "max_chars": 6000
}
```

Memory Forge then computes the memory budget from:

```text
available_memory_tokens = context_window_tokens
  - reserved_prompt_tokens
  - reserved_output_tokens
```

`reserved_prompt_tokens` is for live non-memory content the client still plans
to send, such as the current user request, system instructions, selected tool
output, and code snippets. `reserved_output_tokens` is for the model response.
The returned `usage.fits_context_window` tells whether Memory Forge's returned
text fits that declared memory slice.

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
  "max_chars": 1200,
  "context_window_tokens": 128000,
  "reserved_prompt_tokens": 12000,
  "reserved_output_tokens": 4000
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
- Save user-declared durable instructions immediately when the user says
  "remember this", "always", "prefer", "never", or gives a stable recurring
  rule such as always reading a project file.
- Prefer one concise memory over many tiny notes.
- Do not save facts already checked into `README.md`, `AGENTS.md`, or other
  docs unless they are useful as quick recall.

## Avoiding Double Memory

When using Memory Forge, turn off other durable memory systems if the client
supports it. Built-in memory can duplicate retrieved Memory Forge context and
increase token usage.

For clients that support Codex-style memory settings:

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

For Codex, the release setup command applies those settings and registers the
Memory Forge MCP server:

```powershell
memory-forge-setup codex
```

When developing from a checkout:

```powershell
uv run memory-forge-setup codex --from-checkout .
```

For other clients:

- Disable built-in long-term memory if possible.
- Remove hand-written "memory" sections from system prompts.
- Keep project rules in checked-in docs, not generated memory summaries.
- Add an instruction that Memory Forge is the memory layer for durable memory
  and every active-context chunk the client can explicitly supply for
  compaction.

## Compaction

Memory Forge should handle compaction whenever the client can supply active
context to `memory_compact`. This moves long working context out of the prompt
and into a budgeted compact form.

If a model still reaches its context limit while using Memory Forge, the likely
cause is not durable memory retrieval. It means the client is carrying too much
non-memory prompt content, such as long transcripts, large tool outputs, or file
excerpts. The fix is to send that bulky active context to `memory_compact`, then
replace it in the prompt with the compacted result.

## Beyond MCP

The MCP server cannot see hidden client chat buffers or arbitrary local files on
its own. Memory Forge can still support those sources through an explicit client
integration or release installer that runs with user permission.

Possible integration jobs:

- Configure Codex-style clients to disable built-in memory and register Memory
  Forge as the MCP memory backend.
- Import accessible Codex chat history into compacted memories when the user
  opts in.
- Index selected repositories or local folders into compact summaries.
- Watch specific project instruction files, such as `AGENTS.md`, and refresh
  durable recall memories when those rules change.

Codex setup ships first. Claude Code should use the same integration shape next:
configure the client, avoid duplicate memory, and make history imports or file
indexing explicit opt-in actions.

These jobs should be opt-in, local-first, and scoped to selected files or
client data. They should skip secrets and avoid storing whole transcripts or
entire source files as durable memories.

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
Use Memory Forge as the memory layer for durable memory and every active-context
chunk the client can explicitly supply for compaction. Do not maintain or repeat
a separate long-term memory block in the prompt. Retrieve focused context with
memory_context using project/query/max_chars, then inject only the returned
context string. Use memory_compact for bulky active context the client can send
as soon as it is no longer needed verbatim. Save new durable facts with
memory_remember only when they will help future sessions.
```

5. Start each task with a small `memory_context` call.
6. Call `memory_compact` before active context becomes too large.
7. Save durable facts at the end of the task.
8. Keep required rules in repo docs so humans and agents can audit them.
