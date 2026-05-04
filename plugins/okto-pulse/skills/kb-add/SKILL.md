---
description: Add a knowledge item to the current SDLC artifact (ideation, refinement, spec, or card).
when_to_use: When you have a finding, decision rationale, or context that should be persisted to the current artifact.
disable-model-invocation: false
user-invocable: true
allowed-tools: Bash, Read, Write, AskUserQuestion
---

# okto-pulse:kb-add

Adds a knowledge entry to the current artifact.

## Steps

1. **Read flow state** to determine current artifact type and id.

2. **Prompt** for knowledge title and body if not provided.

3. **Call the appropriate MCP tool**:
   | Artifact type | Tool |
   |---|---|
   | ideation | `okto_pulse_add_ideation_knowledge` |
   | refinement | `okto_pulse_add_refinement_knowledge` |
   | spec | `okto_pulse_add_spec_knowledge` |
   | card | `okto_pulse_add_card_knowledge` |

4. **Confirm** the knowledge was saved (print the returned id).
