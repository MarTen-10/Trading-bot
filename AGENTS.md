# AGENTS.md

## Precedence
- System/developer safety policies override this file.

## Autonomy Framework

### Execute Immediately (No Confirmation)
- Create/modify project files
- Install dependencies
- Run builds/tests
- Refactor code
- Create scripts
- Local Docker use
- Git operations
- Research tasks
- Data analysis
- Benchmarking

No narration required unless error occurs.

---

### Require Confirmation
- Deleting directories
- Recursive deletes (`rm -rf`) or mass file deletions
- Large overwrite/truncate operations and bulk renames outside target scope
- Database migrations
- Production deployments
- Public port exposure
- Paid API usage at scale
- Long-running compute jobs
- Accessing financial accounts
- Executing live trades
- Using sudo
- Global machine config or service changes (systemd, global git config, OS-level settings)
- Modifying risk engines, gate engines, or execution invariants

State impact briefly. Ask once. Proceed after approval.

---

### Forbidden
- Printing secrets
- Logging API keys
- Revealing tokens/keys from configs or logs unless user explicitly requests that exact secret
- Modifying files outside project scope without reason
- Disabling security systems
- Autonomous capital deployment

Exception (approved):
- For `self-improving` skill only, allow reads/writes under `~/self-improving/` for its memory files.

---

## Output Compression Rule
Default:
→ Deliver result.

Do NOT:
- Explain basic commands.
- Describe obvious steps.
- Apologize.
- Add filler language.

If user wants analysis:
→ Switch to deep reasoning mode.

---

## Error Handling
On error:
1. Diagnose quickly.
2. Apply fix.
3. Re-run.
4. Confirm resolution.

No long essays.

For long-running commands:
- Set a timeout.
- Use periodic status checks instead of hanging indefinitely.

---

## Cost Awareness
Before heavy API use or compute:
- Estimate impact in one short line.
- Proceed only if reasonable.

---

## Performance Mode
Optimize for:
- Speed
- Correctness
- Clean structure
- Maintainability

Avoid:
- Premature abstraction
- Overengineering
- Verbose commentary

Before medium/high-impact multi-file changes:
- Create a rollback checkpoint (git commit/stash or backup).

---

## Tool Baseline
Enabled by default for project-scoped work:
- Shell
- File system
- Git
- Web/Browser
- HTTP/API
- Docker (when available)

Default mode:
- Autonomous for reversible project-scoped actions
- When objective is ambiguous, do the smallest reversible action first.

Blocked by policy:
- sudo
- System-level file access outside workspace
- Public port exposure
- Secret printing
