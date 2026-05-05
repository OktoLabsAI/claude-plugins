---
name: sprint
description: Use this skill when okto-pulse:flow routes to current_stage=sprint, or when the okto-pulse:sprint-planner agent loads it. Dual-mode planner — on first entry generates sprint suggestions, creates sprints and cards, surfaces choices to the user, and evaluates each; on re-entry after a sprint closes, detects the next draft sprint and activates it. Always advances to card stage with cards in_progress.
disable-model-invocation: false
user-invocable: true
allowed-tools: Bash, Read, Write, AskUserQuestion, mcp__plugin_okto-pulse_okto-pulse__okto_pulse_suggest_sprints, mcp__plugin_okto-pulse_okto-pulse__okto_pulse_list_sprints, mcp__plugin_okto-pulse_okto-pulse__okto_pulse_get_sprint, mcp__plugin_okto-pulse_okto-pulse__okto_pulse_create_sprint, mcp__plugin_okto-pulse_okto-pulse__okto_pulse_create_card, mcp__plugin_okto-pulse_okto-pulse__okto_pulse_assign_tasks_to_sprint, mcp__plugin_okto-pulse_okto-pulse__okto_pulse_link_card_to_spec, mcp__plugin_okto-pulse_okto-pulse__okto_pulse_add_card_dependency, mcp__plugin_okto-pulse_okto-pulse__okto_pulse_submit_sprint_evaluation, mcp__plugin_okto-pulse_okto-pulse__okto_pulse_move_sprint, mcp__plugin_okto-pulse_okto-pulse__okto_pulse_move_card, mcp__plugin_okto-pulse_okto-pulse__okto_pulse_get_sprint_context, mcp__plugin_okto-pulse_okto-pulse__okto_pulse_get_spec_context, mcp__plugin_okto-pulse_okto-pulse__okto_pulse_list_test_scenarios, mcp__plugin_okto-pulse_okto-pulse__okto_pulse_list_business_rules, mcp__plugin_okto-pulse_okto-pulse__okto_pulse_list_cards_by_status
---

# okto-pulse:sprint

Procedural skill for the Pulse sprint stage. Dual-mode:

- **Initial mode** — spec just validated; no sprints exist (or none have cards assigned). Suggest, create, populate cards, evaluate, activate the first sprint.
- **Continuation mode** — a previous sprint just closed; one or more draft sprints remain. Activate the next draft sprint without re-running suggestion.

Either mode advances the flow to `card` stage with the chosen sprint's cards moved to `in_progress` so the task skill has real work to fan out.

Loaded by the `okto-pulse:sprint-planner` agent during flow routing or invoked directly.

## Inputs

- `$STATE_DIR/flow-state.json` → current artifact (spec or closed sprint)
- Active board id from `$STATE_DIR/active-board.json`

`$STATE_DIR` is the per-project state directory (`${CLAUDE_PLUGIN_DATA}/projects/<key>/`)
returned by `resolve_project_state.py`.

## Workflow

### 0. Resolve per-project state

```bash
STATE_DIR=$(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/resolve_project_state.py" --cwd "$PWD")
```

### 1. Resolve spec id

- Read `$STATE_DIR/flow-state.json`. If `current_artifact.type=spec` → `SPEC_ID = current_artifact.id`.
- If `current_artifact.type=sprint` → call `okto_pulse_get_sprint` to read its `spec_id`.

### 2. Mode detection + drift check

- Call `okto_pulse_list_sprints` for `SPEC_ID`. Inspect the result:
  - If ≥1 sprint exists AND ≥1 of those sprints is in `draft` status → **continuation mode**. Skip to Step 5.
  - If sprints exist but all are `closed` AND all spec cards are `done` → terminal: advance flow directly to `validation` (Step 8) without picking a new sprint.
  - Otherwise (no sprints OR all sprints exist but none are draft / no card assignment) → **initial mode**. Continue to Step 3.

#### 2a. Spec-version drift detection (continuation mode only)

Before activating a draft sprint that was created against an earlier spec revision:

1. Load the candidate draft sprint via `okto_pulse_get_sprint` and capture `sprint.spec_version`.
2. Load the current spec via `okto_pulse_get_spec_context` (use `include_qa="false"` to keep the payload slim — see the `spec` skill's Step 2 note).
3. Compare `sprint.spec_version` with `spec.version`.
4. If they differ, surface via `AskUserQuestion`:
   - "Sprint was created against spec v{X}; current spec is v{Y}. Activate as-is" — proceed with the existing card list.
   - "Regenerate cards" — abort activation; go back to **Step 4** (initial-mode card authoring) so cards reflect current spec.
   - "Abort" — stop without activating any sprint.

Do not auto-activate a stale sprint silently.

### 3. Initial mode — suggest

- Call `okto_pulse_suggest_sprints` with `SPEC_ID`. Capture the suggestion list. Each entry has:
  - `title`, `description`, `card_ids`, `card_titles`, `test_scenario_ids`, `business_rule_ids`.
- **Important:** `card_ids` are EXISTING cards on the spec. `suggest_sprints` does NOT create cards — it groups what already exists. If the spec has no cards yet, the suggestion list will be empty.

### 4. Initial mode — author cards if missing

If `okto_pulse_suggest_sprints` returns zero suggestions OR returns suggestions with empty `card_ids`:

1. Load full spec via `okto_pulse_get_spec_context` (include FRs, TRs, ACs, scenarios, BRs, decisions).
2. For each FR/TR that is an implementation deliverable (not pure documentation): create one **implementation** card via `okto_pulse_create_card` with `spec_id=SPEC_ID`, `card_type="implementation"`, title summarizing the deliverable, description tying it to the FR/TR id.
3. For each test scenario: create one **test** card via `okto_pulse_create_card` with `card_type="test"`, linking the scenario id where the API supports it.
4. For each card needing architecture work: create with `card_type="architecture"`.
5. After authoring, call `okto_pulse_link_card_to_spec` for each card.
6. Re-call `okto_pulse_suggest_sprints` to get updated suggestions over the freshly-authored cards.

### 5. Pick the active sprint

> **`AskUserQuestion` 4-option limit.** The tool accepts at most 4 options per call. With
> >4 candidates you MUST batch: present the first 3 plus a 4th option titled
> "Show next batch", and recurse on selection. Without batching, the call returns
> `too_big maximum: 4` (Family 3, 5 historical errors).

#### Continuation mode (sprints exist, ≥1 draft)

- Run the **drift check (Step 2a)** first against the candidate draft.
- List the draft sprints with their titles.
- If there are **≤4 draft sprints**, present them via `AskUserQuestion` (plus a "next in title order" default option if it fits in the 4-option budget).
- If there are **>4 draft sprints**, batch:
  1. First call presents 3 candidates + "Show next batch".
  2. On "Show next batch", recurse with the next 3 + "Show next batch" (or 4 candidates total on the final batch).
- If only one draft remains, activate it without prompting.

#### Initial mode (just authored / suggested)

- Surface the suggestion list to the user via `AskUserQuestion`. Same 4-option limit applies:
  - Suggestions list ≤3 → present per suggestion + "Approve all" (4 options total).
  - Suggestions list >3 → batch as above. Reserve the final option of each batch for "Approve all" if you want to keep that affordance.
- For approved suggestions: call `okto_pulse_create_sprint` per suggestion with title, description, scenario ids, BR ids. Capture each new sprint id.
- For each newly created sprint: `okto_pulse_assign_tasks_to_sprint` with the suggestion's `card_ids`.
- If multiple sprints created, ask the user via `AskUserQuestion` (with batching if >4) which to activate FIRST.

### 6. Evaluate the active sprint

- Call `okto_pulse_submit_sprint_evaluation` for the active sprint. Target score ≥ 80.
- If < 80: surface the breakdown via `AskUserQuestion` (rebalance / accept / abort). Act on response.

### 7. Activate cards

- Call `okto_pulse_get_sprint` for the active sprint to enumerate its cards.
- For each card whose status is not already `in_progress` and not `done`: call `okto_pulse_move_card` to `in_progress`. **This is the critical step the previous skill was missing — without it the task skill's wave loop has no work.**
- Move the active sprint itself: `okto_pulse_move_sprint` to `in_progress`.

### 8. Atomic flow-state write

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/atomic_write.py" \
  "$STATE_DIR/flow-state.json" \
  '{"current_stage":"card","current_artifact":{"type":"sprint","id":"<active_sprint_id>"},"last_handoff":{"from_skill":"sprint","at":"<iso8601>","mode":"<initial|continuation>"}}'
```

If Step 2 detected the terminal "all sprints closed, all cards done" condition, instead write:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/atomic_write.py" \
  "$STATE_DIR/flow-state.json" \
  '{"current_stage":"validation","current_artifact":{"type":"spec","id":"<SPEC_ID>"},"last_handoff":{"from_skill":"sprint","at":"<iso8601>","mode":"terminal"}}'
```

## Invariants

- `suggest_sprints` groups existing cards. It never creates them. If cards are missing, author them in Step 4 before grouping.
- Always move the active sprint's cards to `in_progress` before advancing — the task skill's wave loop is empty otherwise.
- Never advance to validation while draft sprints with unfinished cards exist. Continuation mode handles the multi-sprint cascade.
- Never auto-approve initial-mode suggestions without `AskUserQuestion`.
- Continuation mode skips suggestion to avoid re-prompting on every sprint close.
