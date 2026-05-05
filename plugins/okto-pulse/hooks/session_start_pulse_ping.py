#!/usr/bin/env python3
"""SessionStart hook — Pulse auth + active-board ping.

Fires once per Claude Code session. Surfaces Pulse health proactively
before the user invokes /okto-pulse:flow, eliminating Family 2 errors
("auth-health invisible until call time") at the source.

Hard constraints (per v0.2.4 plan, "DO NOT touch the working MCP wiring"):

* Token rides as ``?api_key=...`` in the URL, NOT a ``Bearer`` header.
  This mirrors the ``mcpServers.okto-pulse.url`` pattern in plugin.json
  and the load-bearing fix from v0.1.16-v0.1.19.
* Reads ``PULSE_MCP_URL`` from env (default
  ``http://127.0.0.1:8101/mcp``) and ``PULSE_API_TOKEN`` from env.
* If ``PULSE_API_TOKEN`` is empty, exits silently — the user hasn't
  run /okto-pulse:setup yet.

Output protocol (mirrors ``ensure-pulse-up.sh``):

* Emits a single ``<system-reminder>...</system-reminder>`` line on
  stdout. Claude Code surfaces this as additional context to the model.
* On any error, prints a remediation hint and exits 0.
* Always exits 0. NEVER blocks session start.

Behaviour:

1. Read PULSE_MCP_URL + PULSE_API_TOKEN from env. Empty token = silent exit.
2. Resolve per-project state via ``resolve_project_state.py``; read
   ``$STATE_DIR/active-board.json`` for board name.
3. Compose URL ``${PULSE_MCP_URL}?api_key=${PULSE_API_TOKEN}``.
4. Hit ``<base>/readyz?api_key=...`` with 1.5s timeout. On failure,
   emit "Pulse MCP unreachable" hint and exit.
5. POST JSON-RPC ``tools/call`` for ``okto_pulse_get_my_profile`` to
   the MCP URL. On auth failure, emit doctor remediation hint.
6. On success, emit "Pulse: connected as <agent.name>; active board
   <board_name>." so the model has auth+scope context from message #1.

Hard timeout: 2 seconds (declared in hooks.json). Internal probes cap
at 1.5s each so the script self-bounds well under that.
"""
from __future__ import annotations

import json
import os
import pathlib
import re
import subprocess
import sys
import urllib.error
import urllib.request

_DEFAULT_MCP_URL = "http://127.0.0.1:8101/mcp"
_PROBE_TIMEOUT_S = 1.5


def _emit(line: str) -> None:
    """Print a single system-reminder line to stdout."""
    sys.stdout.write(f"<system-reminder>{line}</system-reminder>\n")


def _resolve_state_dir() -> pathlib.Path | None:
    """Run resolve_project_state.py against PWD."""
    script = pathlib.Path(__file__).parent.parent / "scripts" / "resolve_project_state.py"
    if not script.exists():
        return None
    try:
        out = subprocess.run(
            ["python3", str(script), "--cwd", os.getcwd()],
            capture_output=True,
            text=True,
            timeout=1.5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    path = out.stdout.strip()
    if not path:
        return None
    return pathlib.Path(path)


def _read_board_name(state_dir: pathlib.Path | None) -> str | None:
    if state_dir is None:
        return None
    board_file = state_dir / "active-board.json"
    if not board_file.exists():
        return None
    try:
        data = json.loads(board_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    name = data.get("board_name")
    if isinstance(name, str) and name:
        return name
    return None


def _detect_deploy_mode() -> str:
    """Read ${CLAUDE_PLUGIN_DATA}/deploy-mode.json. Default ``local-pip``.

    deploy-mode is plugin-global (one Pulse server per machine), not
    per-project, so it lives in DATA_DIR — not the per-project state dir.
    """
    raw = os.environ.get("CLAUDE_PLUGIN_DATA", "")
    if raw and "okto-pulse" in raw:
        data_dir = pathlib.Path(raw)
    else:
        data_dir = pathlib.Path.home() / ".claude" / "plugins" / "data" / "okto-pulse-oktolabs-plugins"
    f = data_dir / "deploy-mode.json"
    if not f.exists():
        return "local-pip"
    try:
        payload = json.loads(f.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "local-pip"
    # Accept both legacy ``mode`` (matches doctor.sh) and the actual
    # ``deploy_mode`` key written by setup. doctor.sh's mode-detector
    # never matches the latter so it always defaults to local-pip; we
    # mirror that behaviour for parity but prefer the real key when
    # present so we converge on the right port without guesswork.
    mode = payload.get("deploy_mode") or payload.get("mode")
    if isinstance(mode, str) and mode:
        return mode
    return "local-pip"


def _readyz_candidates(mcp_url: str, deploy_mode: str) -> list[str]:
    """Derive readyz URL candidates from MCP URL.

    Local-pip splits API (8100) and MCP (8101) onto separate ports;
    docker/remote serve both on the same port. The ``deploy-mode.json``
    file in the wild has been observed to disagree with the actual
    setup (e.g., ``deploy_mode=docker`` recorded but the machine is
    really running local-pip). Probe both candidates so a misrecorded
    mode doesn't false-flag the server as unreachable.
    """
    base = re.sub(r"\?.*$", "", mcp_url)
    base = re.sub(r"/mcp(/.*)?$", "", base)
    base = base.rstrip("/")
    candidates: list[str] = []
    primary = base
    if deploy_mode == "local-pip":
        primary = re.sub(r":8101\b", ":8100", primary)
    candidates.append(primary + "/readyz")
    # Always also probe the alternate-port variant on localhost to
    # tolerate misrecorded deploy_mode.
    alt = re.sub(r":8101\b", ":8100", base) + "/readyz"
    if alt not in candidates:
        candidates.append(alt)
    alt2 = re.sub(r":8100\b", ":8101", base) + "/readyz"
    if alt2 not in candidates:
        candidates.append(alt2)
    return candidates


def _http_get(url: str, timeout: float) -> tuple[int, bytes]:
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, b""
    except (urllib.error.URLError, TimeoutError, OSError):
        return 0, b""


def _http_post_json(url: str, body: dict, timeout: float) -> dict | None:
    payload = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, TimeoutError, OSError):
        return None
    # MCP HTTP transport returns either a JSON envelope or an SSE
    # stream. Accept either by stripping the SSE "data: " prefix.
    if raw.startswith("data:"):
        raw = "\n".join(line[5:].lstrip() for line in raw.splitlines() if line.startswith("data:"))
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def _extract_agent_name(profile: dict) -> str:
    """Best-effort dig into the get_my_profile result envelope."""
    try:
        result = profile.get("result", {})
        # Tool-call result shape: result.content[0].text contains JSON.
        content = result.get("content")
        if isinstance(content, list) and content:
            text = content[0].get("text", "")
            try:
                payload = json.loads(text)
            except json.JSONDecodeError:
                return ""
            agent = payload.get("agent") or payload.get("profile") or {}
            return str(agent.get("name") or payload.get("name") or "")
    except (AttributeError, TypeError, IndexError):
        pass
    return ""


def _is_auth_error(profile: dict | None) -> bool:
    """True only when the response body explicitly says auth failed.

    The MCP HTTP transport returns ``Bad Request: Missing session ID``
    for plain JSON-RPC posts, which is reachability noise — not an
    auth failure. We look for the literal ``"Authentication failed"``
    or ``"Invalid api key"`` strings the Pulse MCP emits when it
    actively rejects a token.
    """
    if not profile:
        return False
    raw = json.dumps(profile).lower()
    if "missing session id" in raw:
        return False
    return "authentication failed" in raw or "invalid api key" in raw or "unauthorized" in raw


def main() -> int:
    # Discard stdin (event payload) — not needed for this hook.
    if not sys.stdin.isatty():
        try:
            sys.stdin.read()
        except OSError:
            pass

    token = os.environ.get("PULSE_API_TOKEN", "").strip()
    if not token:
        # User hasn't run /okto-pulse:setup yet; stay silent.
        return 0

    mcp_url_base = os.environ.get("PULSE_MCP_URL", _DEFAULT_MCP_URL).strip() or _DEFAULT_MCP_URL
    # AUTH NOTE: MCP HTTP transport requires ``?api_key=...`` query param (Bearer
    # was rejected by the server in v0.1.16-v0.1.19). Sibling ensure-pulse-up.sh
    # still sends Bearer for backward compatibility — this script is the canonical
    # auth path for new code.
    sep = "&" if "?" in mcp_url_base else "?"
    mcp_url_authed = f"{mcp_url_base}{sep}api_key={token}"

    state_dir = _resolve_state_dir()
    board_name = _read_board_name(state_dir) or "(no active board)"

    deploy_mode = _detect_deploy_mode()

    # Reachability probe — try every candidate, accept any 200.
    reachable = False
    for url in _readyz_candidates(mcp_url_base, deploy_mode):
        status, _ = _http_get(f"{url}?api_key={token}", _PROBE_TIMEOUT_S)
        if status == 200:
            reachable = True
            break
    if not reachable:
        _emit(f"Pulse MCP unreachable at {mcp_url_base}. Run /okto-pulse:doctor to diagnose.")
        return 0

    # Auth probe via tools/call get_my_profile. The MCP HTTP transport
    # requires a session handshake that simple curl/urllib can't replay,
    # so most calls come back as ``Bad Request: Missing session ID``.
    # That string still proves reachability — we treat it as "MCP up,
    # auth indeterminate". Only an explicit ``Authentication failed``
    # in the body is treated as an auth red flag (matches the message
    # the MCP server emits on token rejection in remote/docker mode).
    profile = _http_post_json(
        mcp_url_authed,
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": "okto_pulse_get_my_profile", "arguments": {}},
        },
        _PROBE_TIMEOUT_S,
    )
    if _is_auth_error(profile):
        _emit("Pulse auth token rejected. Run /okto-pulse:doctor and choose pulse_api_token_set.")
        return 0

    agent_name = _extract_agent_name(profile) if profile else ""
    if agent_name:
        _emit(f"Pulse: connected as {agent_name}; active board {board_name}.")
    else:
        # MCP session handshake couldn't be replayed via plain HTTP, so
        # we only know the server is up, not who we are. The first MCP
        # call from a real skill (P1 auth preflight) will surface true
        # auth state.
        _emit(f"Pulse: reachable (auth verifies on first MCP call); active board {board_name}.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001
        # Hard guarantee: never crash session start.
        sys.exit(0)
