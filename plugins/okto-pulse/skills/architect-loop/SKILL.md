---
name: architect-loop
description: Per-card or per-spec architecture authoring - composes Excalidraw diagrams, validates payload, imports via Pulse MCP. Loaded by the okto-pulse:architect agent.
when_to_use: Loaded only by the okto-pulse:architect agent. Not user-invocable.
disable-model-invocation: true
user-invocable: false
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, mcp__plugin_okto-pulse_okto-pulse__okto_pulse_get_architecture_design_schema, mcp__plugin_okto-pulse_okto-pulse__okto_pulse_validate_architecture_design_payload, mcp__plugin_okto-pulse_okto-pulse__okto_pulse_import_excalidraw_architecture_diagram, mcp__plugin_okto-pulse_okto-pulse__okto_pulse_copy_architecture_to_card, mcp__plugin_okto-pulse_okto-pulse__okto_pulse_list_architecture_designs, mcp__plugin_okto-pulse_okto-pulse__okto_pulse_get_spec_context, mcp__plugin_okto-pulse_okto-pulse__okto_pulse_get_task_context, mcp__plugin_okto-pulse_okto-pulse__okto_pulse_get_card, mcp__plugin_okto-pulse_okto-pulse__okto_pulse_move_card
---

# okto-pulse:architect-loop

Architecture authoring procedure for either ONE architecture-type card OR ONE spec missing its diagram. Loaded by the `okto-pulse:architect` agent.

## Inputs

Provided by the parent agent prompt — exactly ONE of `CARD_ID` or `SPEC_ID` must be set:

- `BOARD_ID`
- `SPEC_ID` *(spec-stage use, when arch is missing)* OR
- `CARD_ID` *(card-stage use)*
- `PLUGIN_ROOT`

## Hard constraints

- NEVER call `AskUserQuestion`. Zero-confirmation.
- NEVER spawn further subagents.
- Validate every payload before importing. Never import an unvalidated diagram.

## Workflow

### 1. Resolve target

- If `CARD_ID` is set: `okto_pulse_get_task_context` and `okto_pulse_get_card`. Read linked spec id.
- If `SPEC_ID` is set: `okto_pulse_get_spec_context`.

### 2. Inspect the design schema

- Call `okto_pulse_get_architecture_design_schema` to fetch the canonical Excalidraw schema this Pulse instance expects.

### 3. Compose the diagram

- Build an Excalidraw-compatible JSON payload reflecting the components, flows, and boundaries described in the spec / card.
- Layer suggestions: client → API gateway → services → data stores. Group by deployment unit. Label arrows with the protocol or invocation type.

### 4. Validate the payload

- Call `okto_pulse_validate_architecture_design_payload` with the JSON.
- If validation fails: revise and re-validate. Do not proceed past this gate without a green validation.

### 5. Import

- Call `okto_pulse_import_excalidraw_architecture_diagram` with the validated payload to create the design record. Capture the `design_id`.

### 6. Attach to target

- If `CARD_ID` was provided: call `okto_pulse_copy_architecture_to_card` with the new `design_id`. Then call `okto_pulse_move_card` to `done`.
- If `SPEC_ID` only: leave attached to the spec; verify via `okto_pulse_list_architecture_designs`.

### 7. Return summary

```
{
  "status": "PASS" | "FAIL",
  "design_id": "<id>",
  "attached_to": {"type": "spec" | "card", "id": "<id>"},
  "moved_to": "done" | null,
  "summary": "<one paragraph>",
  "blockers": ["<one-line>", ...]
}
```

## Invariants

- Schema → compose → validate → import → attach. Never skip validate.
- The skill never derives spec content; it only diagrams what the spec already states.
