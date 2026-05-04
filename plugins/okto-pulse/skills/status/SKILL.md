---
description: Print a summary of the current flow state - stage, artifact, and last handoff.
when_to_use: Quick orientation check to see where you are in the SDLC flow.
disable-model-invocation: false
user-invocable: true
allowed-tools: Read
---

# okto-pulse:status

Prints the current flow state in a human-readable summary.

## Steps

1. **Read flow state**:
   ```
   Read "${CLAUDE_PLUGIN_DATA}/flow-state.json"
   ```
   If file does not exist: print "No flow state found. Run /okto-pulse:flow to start."

2. **Print summary**:
   ```
   Current stage:    <current_stage>
   Artifact type:    <current_artifact.type>
   Artifact ID:      <current_artifact.id>
   Last handoff:     <last_handoff.from_skill> → <last_handoff.to_subagent> at <last_handoff.at>
   ```
