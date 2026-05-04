"""Shared fixtures for the R1.1 leaf test scaffolds.

These fixtures intentionally point at paths and scripts that R1.2 will
create. The scaffolds remain in xfail(strict=True) until those land.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

# Default Pulse MCP endpoint (matches plugin.json#mcpServers.okto-pulse default)
PULSE_MCP_URL_DEFAULT = "http://127.0.0.1:8101/mcp"


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return REPO_ROOT


@pytest.fixture(scope="session")
def marketplace_json_path() -> Path:
    """Path the marketplace manifest WILL live at after R1.2."""
    return REPO_ROOT / ".claude-plugin" / "marketplace.json"


@pytest.fixture(scope="session")
def plugin_json_path() -> Path:
    """Path the okto-pulse plugin manifest WILL live at after R1.2."""
    return REPO_ROOT / "plugins" / "okto-pulse" / ".claude-plugin" / "plugin.json"


@pytest.fixture(scope="session")
def kebab_case_check_script() -> Path:
    return REPO_ROOT / "tools" / "ci" / "kebab_case_check.py"


@pytest.fixture(scope="session")
def version_consistency_check_script() -> Path:
    return REPO_ROOT / "tools" / "ci" / "version_consistency_check.py"


@pytest.fixture(scope="session")
def smoke_install_script() -> Path:
    return REPO_ROOT / "tools" / "ci" / "smoke_install.sh"


@pytest.fixture
def clean_claude_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Spawn an isolated CLAUDE_HOME for a single test.

    R1.2 will fill this in with the actual env wiring required by the
    smoke-install script. Today it just returns an empty tmp dir and
    redirects HOME so we cannot accidentally write to the real home.
    """
    home = tmp_path / "claude-home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("CLAUDE_HOME", str(home))
    return home


@pytest.fixture
def mcp_url() -> str:
    return os.environ.get("OKTO_PULSE_MCP_URL", PULSE_MCP_URL_DEFAULT)


@pytest.fixture(params=["local-pip", "docker"])
def deploy_mode(request: pytest.FixtureRequest) -> str:
    """Parametrize over the two deploy modes that must work without a token."""
    return request.param
