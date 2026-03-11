# Hermes Windows Security + Training Plan (v1)

## Objective
Deploy Hermes on a personal Windows laptop with top-security defaults, strict non-destructive behavior, and practical file/OneDrive organization support.

## Non-negotiable policy
1. No delete operations (files/folders/cloud items).
2. No overwrite without explicit preview + approval.
3. Prefer copy/move-to-review-folder over destructive edits.
4. Every action logged with before/after summary.

## Phase 0 — Access + control plane
- Pair/connect `Marten Laptop` node.
- Verify remote command capability and health signals.
- Confirm account context (local admin vs standard user).

## Phase 1 — Security baseline (read-only first)
- Windows version/patch level.
- Defender + Firewall + BitLocker status.
- Remote access posture (RDP/SMB exposure).
- Startup apps + scheduled tasks quick scan.
- OneDrive sync status and known folder backup state.

## Phase 2 — Hardening (approval-gated)
- Enforce firewall on all profiles.
- Enable/verify Defender tamper protection + cloud protection.
- Verify BitLocker enabled for OS drive.
- Restrict remote management surfaces unless required.
- Configure least-privilege daily-use account pattern.

## Phase 3 — Hermes behavior training
- Task Class A (safe autopilot):
  - categorize files
  - create folders
  - tag/rename with preview
  - generate organization reports
- Task Class B (approval required):
  - bulk renames
  - moves across major directories
  - archive operations
- Task Class C (blocked):
  - deletes, permanent cleanup, recycle bin empty

## Phase 4 — OneDrive organization workflow
- Build canonical folder map (School / Projects / Admin / Archive).
- Dry-run classification (no writes) with report.
- Apply approved move/rename plan in batches.
- Post-run reconciliation report + rollback map.

## Phase 5 — Continuous safety
- Weekly integrity check (duplicate hotspots, unsorted inbox folders).
- Monthly security check (patch/firewall/defender/bitlocker status).
- Alert on risky drift (disabled firewall, failed AV, sync errors).

## First execution checkpoint
Prereq to start execution now: laptop node must be connected.
Current observed state: paired but disconnected.
