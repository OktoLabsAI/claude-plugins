"""Verbatim Given/When/Then for every Pulse-tracked test scenario.

Source: Pulse specs 75fe081f (R1 Foundation) and 46dbff78 (R2 Bootstrap),
        sprints 97de0400/e18856b2/6eaa093b (R1.x) and 2c353ca4/3b4bbb87/f337e95f (R2.x).
"""
from typing import TypedDict


class Scenario(TypedDict):
    title: str
    type: str
    given: str
    when: str
    then: str
    card_id: str


SCENARIOS: dict[str, Scenario] = {
    "ts_d3c447de": {
        "title": "Fresh install via marketplace shows plugin",
        "type": "e2e",
        "given": (
            "A clean Claude Code installation with no oktolabs-plugins "
            "marketplace registered and no okto-pulse plugin installed"
        ),
        "when": (
            "User runs /plugin marketplace add oktolabsai/claude-plugins "
            "followed by /plugin install okto-pulse@oktolabs-plugins"
        ),
        "then": (
            "The /plugin list output includes an entry for okto-pulse with "
            "the version from plugin.json and source pointing to the marketplace"
        ),
        "card_id": "ae5f23bb-a3a5-4967-987a-cc3e392e7189",
    },
    "ts_e53d04fb": {
        "title": "Kebab-case violation fails CI",
        "type": "integration",
        "given": (
            "A PR adds a skill directory named skills/StressTest/SKILL.md "
            "(PascalCase) violating kebab-case"
        ),
        "when": (
            "CI runs the kebab-case enforcer as part of the 7-check suite"
        ),
        "then": (
            "The kebab-case check fails with the offending path; PR cannot "
            "be merged; the other 6 checks may still run but the overall "
            "gate is failed"
        ),
        "card_id": "3a62aad0-45b3-4faa-8c99-9250d863e80a",
    },
    "ts_d6d14d62": {
        "title": "compatible-pulse-range excludes next major",
        "type": "unit",
        "given": (
            "plugin.json#version is 0.1.14 and compatible-pulse-range is "
            "\">=0.1.14, <0.2\"; CI is testing against okto-pulse pip 0.2.0"
        ),
        "when": (
            "CI version-consistency check parses the range and compares "
            "against the installed pip version"
        ),
        "then": (
            "Check fails with a message that 0.2.0 is outside the "
            "compatible range; PR is blocked from merging"
        ),
        "card_id": "98365a30-fb54-4a58-b3c8-95364759565f",
    },
    "ts_659675c6": {
        "title": "No-token install works in local-pip and docker modes",
        "type": "e2e",
        "given": (
            "A user installs the plugin and selects local-pip (or docker) "
            "deploy mode in /okto-pulse:setup; pulse_api_token is left empty"
        ),
        "when": (
            "Plugin is enabled and the MCP server is contacted at "
            "http://127.0.0.1:8101/mcp without an Authorization header"
        ),
        "then": (
            "MCP handshake succeeds; tool calls work; setup proceeds to the "
            "board picker; no error about missing token"
        ),
        "card_id": "c052f2c8-29e0-44f9-8b9b-62be12f210f2",
    },
    # ----- R2.1 Bootstrap test scaffolds (spec 46dbff78, sprint 2c353ca4) -----
    "ts_5ced4e76": {
        "title": "Setup completes with one prompt and ends green",
        "type": "e2e",
        "given": (
            "A clean Claude Code environment with okto-pulse plugin enabled, "
            "no userConfig set, no Pulse running"
        ),
        "when": (
            "User invokes /okto-pulse:setup and answers the deploy-mode "
            "question once (any of local-pip, docker, remote with valid inputs)"
        ),
        "then": (
            "No further prompts beyond mode question and userConfig values; "
            "helper script runs to completion; common tail persists userConfig "
            "and runs /okto-pulse:doctor; doctor reports 100% green; active "
            "board picker completes"
        ),
        "card_id": "b53480c6-826f-4e8d-ba52-a0d7d8d79961",
    },
    "ts_8c3aa4ed": {
        "title": "Remote path validates URL/token without local install",
        "type": "e2e",
        "given": (
            "A reachable remote Pulse instance at "
            "http://192.168.31.154:9100/mcp with a valid Bearer token; user "
            "has selected 'remote' deploy mode and entered URL+token"
        ),
        "when": (
            "/okto-pulse:setup runs bootstrap-remote.sh to completion"
        ),
        "then": (
            "No pip install, no docker container; URL validated; /readyz "
            "returns 200 with the Bearer header; okto_pulse_kg_health returns "
            "ok; userConfig is populated with the URL and token (token "
            "sensitive=true → keychain); MCP handshake succeeds"
        ),
        "card_id": "7b3a8b71-ed98-487d-b393-d37ccafb51ad",
    },
    "ts_6592e960": {
        "title": "PreCompact hook persists un-consolidated KG edges",
        "type": "integration",
        "given": (
            "An active Claude session has created at least one un-consolidated "
            "KG edge (e.g. via okto_pulse_kg_add_edge_candidate during the "
            "session)"
        ),
        "when": (
            "Claude Code triggers context compaction (PreCompact event)"
        ),
        "then": (
            "consolidate-on-compact.sh fires; kg_begin_consolidation + "
            "kg_commit_consolidation succeed; the previously-uncommitted edge "
            "is queryable via okto_pulse_kg_query_natural after the hook "
            "completes; on commit failure, kg_abort_consolidation is called "
            "and the edge remains in the candidate state"
        ),
        "card_id": "9447d51a-185e-40b1-a583-b6f897d66156",
    },
    "ts_d8e85551": {
        "title": "Helper scripts return documented exit codes per failure",
        "type": "integration",
        "given": (
            "Four failure injections against the helper scripts: "
            "(a) bootstrap-docker.sh with docker daemon stopped; "
            "(b) bootstrap-local-pip.sh with pip server unreachable; "
            "(c) bootstrap-local-pip.sh with /readyz never returning 200 "
            "within 15s; "
            "(d) any helper with user typing Ctrl+C at the mode prompt"
        ),
        "when": (
            "Each helper runs under the failure injection"
        ),
        "then": (
            "(a) exits 10 (precondition fail); (b) exits 20 (runtime fail); "
            "(c) exits 30 (timeout); (d) exits 2 (user cancellation); each "
            "emits a final NDJSON envelope with ok=false and an error.message"
        ),
        "card_id": "b3e132a6-96eb-4ada-9c30-21ba8695aca9",
    },
}
