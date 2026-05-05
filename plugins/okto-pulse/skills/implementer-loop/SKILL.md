---
name: implementer-loop
description: Per-card implementation procedure - TDD code writing for one okto-pulse implementation card. Loaded by the okto-pulse:implementer agent during card-stage fan-out.
when_to_use: Loaded only by the okto-pulse:implementer agent. Not user-invocable.
disable-model-invocation: true
user-invocable: false
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, mcp__plugin_okto-pulse_okto-pulse__okto_pulse_get_task_context, mcp__plugin_okto-pulse_okto-pulse__okto_pulse_get_card, mcp__plugin_okto-pulse_okto-pulse__okto_pulse_link_task_to_scenario, mcp__plugin_okto-pulse_okto-pulse__okto_pulse_link_task_to_rule, mcp__plugin_okto-pulse_okto-pulse__okto_pulse_link_task_to_decision, mcp__plugin_okto-pulse_okto-pulse__okto_pulse_link_task_to_contract, mcp__plugin_okto-pulse_okto-pulse__okto_pulse_add_card_knowledge, mcp__plugin_okto-pulse_okto-pulse__okto_pulse_move_card
---

# okto-pulse:implementer-loop

Per-card TDD implementation procedure. This skill is loaded by the `okto-pulse:implementer` agent during card-stage parallel fan-out. It owns the code-writing loop for ONE implementation card and returns a structured JSON report.

## Inputs

The agent provides these via the parent prompt (already parsed by the agent):

- `BOARD_ID` — Pulse board id
- `SPRINT_ID` — current sprint id
- `CARD_ID` — implementation card to work
- `PLUGIN_ROOT` — resolved `${CLAUDE_PLUGIN_ROOT}`

## Hard constraints

- NEVER call `AskUserQuestion`. This is zero-confirmation.
- NEVER spawn further subagents.
- The agent prints `===REPORT===` and the JSON; do not duplicate that — return your summary so the agent can format.

## Workflow

### 1. Load card context

- Call `okto_pulse_get_task_context` with `card_id=CARD_ID` to load the card payload, linked artifacts (specs, scenarios, rules, contracts, decisions), and acceptance criteria.
- Call `okto_pulse_get_card` for the canonical card record.

If the card is not in `in_progress` status, return immediately with `status=FAIL`, `blockers=["card not in_progress"]`.

### 2. Write failing tests first (TDD)

- Identify the test framework from the repo (pytest/unittest/jest/etc.) by reading test files in the project tree.
- Write one or more failing tests that encode the acceptance criteria from the card and any linked test scenarios.
- Run the test suite to confirm the new tests FAIL for the expected reason (not import errors).

Capture the failing test names and one-line failure reasons.

### 3. Implement minimal code to pass

- Implement the smallest change that makes the failing tests pass.
- Re-run tests; iterate until tests pass.
- Refactor if the implementation is awkward, then re-run tests.
- Stop when all new tests pass and no previously-passing tests regressed.

### 4. Link traceability

For every artifact the work touches:

- Linked scenarios → `okto_pulse_link_task_to_scenario`
- Linked business rules → `okto_pulse_link_task_to_rule`
- Linked decisions → `okto_pulse_link_task_to_decision`
- Linked API contracts → `okto_pulse_link_task_to_contract`

If a card-level finding belongs in the KG, record it via `okto_pulse_add_card_knowledge`.

### 5. Move the card

- All tests pass + traceability links recorded → `okto_pulse_move_card` to status `done`.
- Blocked (test infra missing, missing dependency, ambiguous requirement) → `okto_pulse_move_card` to `blocked` with a one-line reason.

### 6. Return summary

Return to the agent a JSON-shaped object containing:

```
{
  "status": "PASS" | "FAIL",
  "card_id": "<CARD_ID>",
  "moved_to": "done" | "blocked",
  "summary": "<one-paragraph what changed>",
  "files_changed": ["<repo-relative path>", ...],
  "scenarios_passed": ["<scenario id>", ...],
  "blockers": ["<one-line>", ...]
}
```

The agent will wrap this with the `===REPORT===` delimiter.

## Invariants

- Tests must be written before implementation (TDD). No "implement, then write tests".
- Never call `okto_pulse_submit_task_validation` — that is the qa-engineer's job at validation stage, not card-stage implementation.
- Never call `AskUserQuestion`.
