---
name: Self-Improving Agent
slug: self-improving
version: 1.1.0
homepage: https://clawic.com/skills/self-improving
description: Corrections become improvements. Memory that self-improves.
changelog: Added detection triggers, quick queries, memory stats, and example templates for easier setup.
metadata: {"clawdbot":{"emoji":"🧠","requires":{"bins":[]},"os":["linux","darwin","win32"]}}
---

## When to Use

User corrects you or points out mistakes. You need to remember preferences, patterns, and lessons across sessions. Knowledge should compound over time without manual maintenance.

## Architecture

Memory lives in `~/self-improving/` with tiered structure. See `memory-template.md` for setup.

```
~/self-improving/
├── memory.md          # HOT: ≤100 lines, always loaded
├── index.md           # Topic index with line counts
├── projects/          # Per-project learnings
├── domains/           # Domain-specific (code, writing, comms)
├── archive/           # COLD: decayed patterns
└── corrections.md     # Last 50 corrections log
```

## Quick Reference

| Topic | File |
|-------|------|
| Learning mechanics | `learning.md` |
| Security boundaries | `boundaries.md` |
| Scaling rules | `scaling.md` |
| Memory operations | `operations.md` |

## Data Storage

All data stored in `~/self-improving/`. Create on first use:
```bash
mkdir -p ~/self-improving/{projects,domains,archive}
```

## Detection Triggers

Log automatically when you notice these patterns:

**Corrections** → add to `corrections.md`, evaluate for `memory.md`:
- "No, that's not right..."
- "Actually, it should be..."
- "You're wrong about..."
- "I prefer X, not Y"
- "Remember that I always..."
- "I told you before..."
- "Stop doing X"
- "Why do you keep..."

**Preference signals** → add to `memory.md` if explicit:
- "I like when you..."
- "Always do X for me"
- "Never do Y"
- "My style is..."
- "For [project], use..."

**Pattern candidates** → track, promote after 3x:
- Same instruction repeated 3+ times
- Workflow that works well repeatedly
- User praises specific approach

**Ignore** (don't log):
- One-time instructions ("do X now")
- Context-specific ("in this file...")
- Hypotheticals ("what if...")

## Quick Queries

| User says | Action |
|-----------|--------|
| "What do you know about X?" | Search all tiers for X |
| "What have you learned?" | Show last 10 from `corrections.md` |
| "Show my patterns" | List `memory.md` (HOT) |
| "Show [project] patterns" | Load `projects/{name}.md` |
| "What's in warm storage?" | List files in `projects/` + `domains/` |
| "Memory stats" | Show counts per tier |
| "Forget X" | Remove from all tiers (confirm first) |
| "Export memory" | ZIP all files |

## Memory Stats

On "memory stats" request, report:

```
📊 Self-Improving Memory

HOT (always loaded):
  memory.md: X entries

WARM (load on demand):
  projects/: X files
  domains/: X files

COLD (archived):
  archive/: X files

Recent activity (7 days):
  Corrections logged: X
  Promotions to HOT: X
  Demotions to WARM: X
```

## Core Rules

### 1. Learn from Corrections Only
- Log when user explicitly corrects you
- Never infer from silence or observation
- After 3 identical corrections → ask to confirm as rule

### 2. Tiered Storage
| Tier | Location | Size Limit | Behavior |
|------|----------|------------|----------|
| HOT | memory.md | ≤100 lines | Always loaded |
| WARM | projects/, domains/ | ≤200 lines each | Load on context match |
| COLD | archive/ | Unlimited | Load on explicit query |

### 3. Automatic Promotion/Demotion
- Pattern used 3x in 7 days → promote to HOT
- Pattern unused 30 days → demote to WARM
- Pattern unused 90 days → archive to COLD
- Never delete without asking

### 4. Namespace Isolation
- Project patterns stay in `projects/{name}.md`
- Global preferences in HOT tier (memory.md)
- Domain patterns (code, writing) in `domains/`
- Cross-namespace inheritance: global → domain → project

### 5. Conflict Resolution
When patterns contradict:
1. Most specific wins (project > domain > global)
2. Most recent wins (same level)
3. If ambiguous → ask user

### 6. Compaction
When file exceeds limit:
1. Merge similar corrections into single rule
2. Archive unused patterns
3. Summarize verbose entries
4. Never lose confirmed preferences

### 7. Transparency
- Every action from memory → cite source: "Using X (from projects/foo.md:12)"
- Weekly digest available: patterns learned, demoted, archived
- Full export on demand: all files as ZIP

### 8. Security Boundaries
See `boundaries.md` — never store credentials, health data, third-party info.

### 9. Graceful Degradation
If context limit hit:
1. Load only memory.md (HOT)
2. Load relevant namespace on demand
3. Never fail silently — tell user what's not loaded

## Scope

This skill ONLY:
- Learns from explicit user corrections
- Stores preferences in local files (`~/self-improving/`)
- Reads its own memory files on activation

This skill NEVER:
- Accesses calendar, email, or contacts
- Makes network requests
- Reads files outside `~/self-improving/`
- Infers preferences from silence or observation
- Modifies its own SKILL.md

## Related Skills
Install with `clawhub install <slug>` if user confirms:

- `memory` — Long-term memory patterns for agents
- `learning` — Adaptive teaching and explanation
- `decide` — Auto-learn decision patterns
- `escalate` — Know when to ask vs act autonomously

## Feedback

- If useful: `clawhub star self-improving`
- Stay updated: `clawhub sync`
