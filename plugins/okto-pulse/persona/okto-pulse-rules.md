# okto-pulse-rules

System-level rules for Pulse SDLC orchestration. Import via `@okto-pulse-rules`.

## Core Rules

1. **Always check flow state first** — read `${CLAUDE_PLUGIN_DATA}/flow-state.json` before any action. Never assume stage from conversation context.

2. **Never skip KG consolidation** — at every stage transition, consolidate the artifact into the KG before advancing.

3. **Planning agents work MCP-only** — agents with `disallowedTools: [Write, Edit]` must never attempt filesystem writes. Route all state through Pulse MCP tools.

4. **Validate with evidence** — task validations must include runtime evidence (logs, test output, screenshots). Assertions alone are insufficient.

5. **Atomic state writes only** — always use `scripts/atomic_write.py` for flow-state.json. Never write state files directly with bash redirection.

6. **Archive, never delete** — use `okto_pulse_archive_tree` for cleanup operations. Deletion is irreversible.

7. **Tiebreaker rule** — when stage is ambiguous, count open Q&A. If open_count > 0, stay at current stage.
