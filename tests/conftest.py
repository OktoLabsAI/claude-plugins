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


# ----- R2.x bootstrap surface (paths the R2.2 impl card set will create) -----

@pytest.fixture(scope="session")
def plugin_root() -> Path:
    """The plugin source root (corresponds to ${CLAUDE_PLUGIN_ROOT} after install)."""
    return REPO_ROOT / "plugins" / "okto-pulse"


@pytest.fixture(scope="session")
def bootstrap_local_pip_script(plugin_root: Path) -> Path:
    return plugin_root / "bin" / "bootstrap-local-pip.sh"


@pytest.fixture(scope="session")
def bootstrap_docker_script(plugin_root: Path) -> Path:
    return plugin_root / "bin" / "bootstrap-docker.sh"


@pytest.fixture(scope="session")
def bootstrap_remote_script(plugin_root: Path) -> Path:
    return plugin_root / "bin" / "bootstrap-remote.sh"


@pytest.fixture(scope="session")
def doctor_script(plugin_root: Path) -> Path:
    return plugin_root / "bin" / "doctor.sh"


@pytest.fixture(scope="session")
def setup_skill_path(plugin_root: Path) -> Path:
    return plugin_root / "skills" / "setup" / "SKILL.md"


@pytest.fixture(scope="session")
def doctor_skill_path(plugin_root: Path) -> Path:
    return plugin_root / "skills" / "doctor" / "SKILL.md"


@pytest.fixture(scope="session")
def hooks_json_path(plugin_root: Path) -> Path:
    return plugin_root / "hooks" / "hooks.json"


@pytest.fixture(scope="session")
def ensure_pulse_up_script(plugin_root: Path) -> Path:
    return plugin_root / "scripts" / "ensure-pulse-up.sh"


@pytest.fixture(scope="session")
def consolidate_on_compact_script(plugin_root: Path) -> Path:
    return plugin_root / "scripts" / "consolidate-on-compact.sh"


@pytest.fixture(scope="session")
def stop_validation_gate_script(plugin_root: Path) -> Path:
    return plugin_root / "scripts" / "stop-validation-gate.sh"


@pytest.fixture(scope="session")
def task_completed_card_sync_script(plugin_root: Path) -> Path:
    return plugin_root / "scripts" / "task-completed-card-sync.sh"


@pytest.fixture(scope="session")
def docker_compose_path(plugin_root: Path) -> Path:
    return plugin_root / "deploy" / "docker-compose.yml"


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
