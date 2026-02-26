# Cost Control Playbook

## Rules
- Use default model for complex/high-stakes tasks.
- Avoid unnecessary loops/retries.
- Batch related work into single requests.
- Prefer local tools (Ollama embeddings, local SearXNG) where possible.

## Quick checks
- `openclaw status`
- `openclaw memory status --deep`
- `openclaw update status`

## Weekly review
- Run memory healthcheck + security audit and review drift.
