# Memory Forge Agent Guidance

- Treat Memory Forge as the durable memory source for this project.
- Do not paste or maintain a separate long-term memory block in prompts.
- When prior context is needed, call `memory_context` with a focused query,
  project name, and small `max_chars` budget.
- Inject only the returned `context` string into working context.
- Save new memories with `memory_remember` only for stable facts, recurring
  preferences, project conventions, or pitfalls that will help future sessions.
- Keep required project rules in this file or checked-in docs, not only in
  generated memory state.
