# Incident Response (Fast)

1. Confirm impact/scope in 1 sentence.
2. Capture current status:
   - `openclaw status --deep`
   - `openclaw security audit --deep`
   - `openclaw health --json`
3. Stabilize first (stop regressions, preserve access).
4. Apply minimal fix.
5. Re-run validation commands.
6. Log outcome in `memory/daily/YYYY-MM-DD.md`.
