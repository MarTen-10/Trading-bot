# MEMORY.md

## Active retained items
- Pending follow-up: set up Hermes as distributed local operator after soak: Hermes-Laptop + Hermes-Desktop (same role, two device instances) with Anubis orchestrating.
- Communication preference: always explain actions taken, especially config/system changes.
- Communication preference: after any restart/redeploy that impacts availability, send explicit "back online and ready" confirmation.
- Approval UX preference: for node/script deployments, avoid long heredoc approvals; use short (<2KB) chunked/base64 commands with separate write/chmod phases.
- Communication preference: include a direct opinion/recommendation at the end when giving guidance.
