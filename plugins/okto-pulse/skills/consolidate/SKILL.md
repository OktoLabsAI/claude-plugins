---
description: Manual KG consolidation trigger - consolidates the current artifact into the knowledge graph.
when_to_use: Run after completing a stage or when KG may be out of date with recent artifact changes.
disable-model-invocation: false
user-invocable: true
allowed-tools: Bash, Read, Write
---

# okto-pulse:consolidate

Manually triggers KG consolidation for the current artifact.

## Steps

1. **Read flow state** to get current artifact id and type.

2. **Begin consolidation**: call `okto_pulse_kg_begin_consolidation`.

3. **Commit**: call `okto_pulse_kg_commit_consolidation`.

4. **Verify**: call `okto_pulse_kg_health` — all checks must be green.

5. **Print** the node count delta (before vs after).
