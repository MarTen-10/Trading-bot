# Organs Check (Anubis)

## Purpose
Fast internal diagnostic for assistant readiness, safety, and execution quality.

## Check Blocks

1. Runtime Vital Signs
- `session_status`
- `openclaw status --deep`

Pass criteria:
- Gateway reachable
- Model active
- Session healthy (no blocked queue)

2. Security Surface
- `openclaw security audit --deep`

Pass criteria:
- 0 critical findings
- Any warning has explicit fix path

3. Update Hygiene
- `openclaw update status`

Pass criteria:
- Update state known and actionable command available

4. Memory Integrity
- `memory_search` sanity query
- Verify MEMORY.md exists and is readable

Pass criteria:
- search returns snippets
- no memory read errors

5. Execution Integrity
- `git status --short` in workspace
- verify recent commits recorded

Pass criteria:
- uncommitted state is intentional
- no unknown destructive changes

## Output Format
- Status: GREEN / YELLOW / RED
- Findings: max 5 bullets
- Action: exact next command(s)
- Risk note: one line
