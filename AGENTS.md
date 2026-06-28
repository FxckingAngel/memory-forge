# Memory Forge Agent Guidance

- Treat Memory Forge as the memory layer for durable memory and every active
  context chunk the client can explicitly send to `memory_compact`.
- Keep Codex built-in memory disabled; do not enable `features.memories`,
  `memories.use_memories`, or `memories.generate_memories`.
- Do not paste or maintain a separate long-term memory block in prompts.
- When prior context is needed, call `memory_context` with a focused query,
  project name, and small `max_chars` budget. When the model window is known,
  pass `context_window_tokens`, `reserved_prompt_tokens`, and
  `reserved_output_tokens`.
- Inject only the returned `context` string into working context.
- When active chat context is no longer needed verbatim, call `memory_compact`
  and replace the bulky live context with the compacted result instead of
  carrying both.
- If the user says "remember this", "always", "prefer", "never", or gives a
  stable recurring instruction such as always reading a file, save it with
  `memory_remember`.
- Save new memories with `memory_remember` only for stable facts, recurring
  preferences, project conventions, or pitfalls that will help future sessions.
- Keep required project rules in this file or checked-in docs, not only in
  generated memory state.
