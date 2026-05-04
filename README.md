# OktoLabs Claude Code plugin marketplace

This repository is the **`oktolabs-plugins`** marketplace — a Claude Code plugin
marketplace owned by [OktoLabs](https://oktolabs.ai). Today it ships a single
flagship plugin, **okto-pulse**, which connects Claude Code to the
[okto-pulse](https://github.com/OktoLabsAI/okto-pulse) SDLC orchestrator over
MCP.

> 🚧 **Status:** scaffold (sprint R1.1). The plugin tree, manifests, and
> CI gates land in sprint R1.2. The four pytest files in `tests/` are RED
> scaffolds (`xfail(strict=True)`) that pin the leaf test scenarios for
> the foundation work.

## Install (once R1.2 lands)

```text
/plugin marketplace add oktolabsai/claude-plugins
/plugin install okto-pulse@oktolabs-plugins
```

## Layout

```
claude-plugins/
├── .claude-plugin/             # marketplace.json (R1.2)
├── plugins/
│   └── okto-pulse/             # plugin.json + components (R1.2)
├── tools/
│   └── ci/                     # 7-check CI suite (R1.2)
└── tests/                      # leaf test scaffolds (this sprint, R1.1)
```

## SDLC lineage

All requirements, decisions, and acceptance criteria are tracked in the
**OktoPulse-ClaudeCode-Skill** Pulse board.

| Artifact | Pulse id |
|---|---|
| Board | `39eecda7-ced0-4450-8b7c-9267b60826cb` |
| Ideation | `2ae263b6-c813-4da9-9447-701a9a87d0e4` |
| R1 spec (Foundation) | `75fe081f-2e7f-4d38-ba73-57d47815c369` |
| R1.1 sprint (this) | `97de0400-5ba6-4c16-8945-9e1f78d5bd40` |

Each test in `tests/` carries `@pytest.mark.scenario("ts_xxxxxxxx")` plus
`@pytest.mark.card("<uuid>")`, `sprint(...)`, and `spec(...)` marks so the
mapping back to Pulse stays mechanical.

## Running the test scaffolds

```bash
pip install -e ".[test]"
pytest
```

Expected current state: **5 xfailed, 0 passed, 0 failed** (Card 4 is parametrized over `local-pip` and `docker` deploy modes, so it contributes 2 xfail rows).

## License

MIT — see [LICENSE](LICENSE).
