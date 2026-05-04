"""Verbatim Given/When/Then for the four R1.1 leaf test scenarios.

Source: Pulse spec 75fe081f-2e7f-4d38-ba73-57d47815c369
        sprint 97de0400-5ba6-4c16-8945-9e1f78d5bd40
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
}
