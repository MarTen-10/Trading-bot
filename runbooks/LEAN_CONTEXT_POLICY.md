# Lean Context Policy

## Default load (always)
- SOUL.md
- USER.md
- IDENTITY.md
- latest `memory/daily/YYYY-MM-DD.md` if present

## Do not preload
- Full MEMORY.md
- Full session history
- Large tool outputs

## On-demand recall
1. Use `memory_search` for prior context.
2. Use `memory_get` for only the relevant lines.
3. Only open full files if required to complete the task.

## End-of-task writeback
- Append concise outcome + decisions to `memory/daily/YYYY-MM-DD.md`.
