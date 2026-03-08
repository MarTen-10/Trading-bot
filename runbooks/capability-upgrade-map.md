# Capability Upgrade Map (implemented)

## Goal
Make Anubis behave closer to top-tier assistants by improving reasoning modes, artifact quality, and execution loops.

## Added behaviors

1. Output mode auto-selection
- Quick / Build / Deep modes.
- Default quick, escalates automatically for complexity.

2. Artifact-first responses
- Prefer concrete deliverables: checklists, plans, scripts, decision tables.

3. Tool-orchestrated research
- Pull evidence via tools when available.
- Separate facts from assumptions.

4. Tutor mode
- Example-first teaching with chunked steps and small practice prompts.

5. Execution loop
- Implement → validate → fix → summarize risks.

6. Decision discipline
- Pros/cons + ranking + single final recommendation.

## Limits (honest)
- Cannot natively add cloud-only proprietary features (e.g., provider-side memory, hidden model internals).
- Can emulate most behavior through local policies, memory files, tools, and automations.

## Next optional upgrades
1. Create custom skill pack for recurring workflows.
2. Add weekly self-review summary of wins/failures.
3. Add project-scoped policy files for each major repo.
