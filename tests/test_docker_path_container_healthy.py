"""Card 3800675a / scenario ts_8e4df22a / AC[3] — Docker path leaves container healthy.

E2E smoke for the docker deploy mode of ``/okto-pulse:setup``:

    Running /okto-pulse:setup with docker leaves the okto-pulse container
    running with image=ghcr.io/oktolabsai/okto-pulse:<plugin-version>, the
    container healthcheck passing, and the MCP handshake successful.

This test runs against a real Docker daemon and a real (published)
image. It self-skips if any prerequisite is missing so the suite stays
green on developer machines where:

    - Docker isn't installed
    - The Docker daemon isn't running
    - The pinned image hasn't been published yet (the okto-pulse repo
      release pipeline owns ghcr.io/oktolabsai/okto-pulse tags)
"""
from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest


PINNED_VERSION = "0.1.14"
PINNED_IMAGE = f"ghcr.io/oktolabsai/okto-pulse:{PINNED_VERSION}"
READYZ_URL = "http://127.0.0.1:8101/readyz"


def _docker_available() -> bool:
    if shutil.which("docker") is None:
        return False
    try:
        rc = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            timeout=10,
            check=False,
        ).returncode
    except (subprocess.TimeoutExpired, OSError):
        return False
    return rc == 0


def _host_docker_arch() -> str:
    """Map uname machine to the docker manifest architecture spelling."""
    m = platform.machine().lower()
    if m in {"x86_64", "amd64"}:
        return "amd64"
    if m in {"aarch64", "arm64"}:
        return "arm64"
    return m


def _image_published_for_host(image: str) -> bool:
    """Return True iff a manifest exists AND covers the current host arch.

    Without this dual gate the test on Apple Silicon will fail at
    ``docker pull`` with "no matching manifest for linux/arm64/v8" even
    though ``docker manifest inspect`` returns success (the manifest list
    is amd64-only).
    """
    try:
        proc = subprocess.run(
            ["docker", "manifest", "inspect", image],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
    except (subprocess.TimeoutExpired, OSError):
        return False
    if proc.returncode != 0 or not proc.stdout.strip():
        return False
    try:
        manifest = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return False
    host_arch = _host_docker_arch()
    entries = manifest.get("manifests") or []
    if not entries:
        # Single-arch v2 schema; look at config -> architecture.
        return manifest.get("architecture", host_arch) == host_arch
    for entry in entries:
        plat = entry.get("platform") or {}
        if plat.get("architecture") == host_arch and plat.get("os") in (None, "linux"):
            return True
    return False


@pytest.mark.scenario("ts_8e4df22a")
@pytest.mark.card("3800675a-50fb-4eb6-9720-40b1ded9f2a8")
@pytest.mark.sprint("f337e95f-0d5b-4615-a353-725167306330")
@pytest.mark.spec("46dbff78-5997-442e-a6c3-c6fb6cb735e3")
def test_docker_path_leaves_container_healthy(
    bootstrap_docker_script: Path,
    docker_compose_path: Path,
) -> None:
    """End-to-end: bootstrap-docker leaves a healthy container + reachable /readyz."""
    assert bootstrap_docker_script.exists(), "bootstrap-docker.sh must exist"
    assert docker_compose_path.exists(), "docker-compose.yml must exist"

    if not _docker_available():
        pytest.skip("docker CLI/daemon unavailable on this host")
    if not _image_published_for_host(PINNED_IMAGE):
        pytest.skip(
            f"image {PINNED_IMAGE} not published for {_host_docker_arch()}; "
            "covered when okto-pulse repo publishes the release tag"
        )

    env = {
        **os.environ,
        "OKTO_PULSE_PIN_VERSION": PINNED_VERSION,
        "OKTO_PULSE_IMAGE": PINNED_IMAGE,
        "OKTO_PULSE_READYZ_TIMEOUT_SECONDS": "90",
    }

    try:
        result = subprocess.run(
            [str(bootstrap_docker_script)],
            env=env,
            capture_output=True,
            text=True,
            check=False,
            timeout=240,
        )
        assert result.returncode == 0, (
            f"bootstrap-docker.sh exit {result.returncode}\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )

        # Final NDJSON envelope is the last non-blank stdout line.
        lines = [ln for ln in result.stdout.strip().splitlines() if ln.strip()]
        assert lines, f"bootstrap emitted no stdout; stderr:\n{result.stderr}"
        envelope = json.loads(lines[-1])
        assert envelope.get("ok") is True, f"final envelope not ok: {envelope}"
        assert envelope.get("mode") == "docker", f"mode mismatch: {envelope}"
        assert envelope.get("container") == "okto-pulse", (
            f"container mismatch: {envelope}"
        )
        assert envelope.get("image") == PINNED_IMAGE, (
            f"image mismatch: {envelope}"
        )

        # Poll docker healthcheck (up to 30s).
        deadline = time.time() + 30
        last_status = ""
        while time.time() < deadline:
            inspect = subprocess.run(
                [
                    "docker",
                    "inspect",
                    "--format",
                    "{{.State.Health.Status}}",
                    "okto-pulse",
                ],
                capture_output=True,
                text=True,
                check=False,
                timeout=10,
            )
            last_status = (inspect.stdout or "").strip()
            if last_status == "healthy":
                break
            time.sleep(1)
        assert last_status == "healthy", (
            f"container never became healthy; last status={last_status!r}"
        )

        # MCP handshake proxy: probe /readyz.
        try:
            with urllib.request.urlopen(READYZ_URL, timeout=5) as resp:
                assert resp.status == 200, f"/readyz returned {resp.status}"
        except urllib.error.URLError as exc:
            pytest.fail(f"/readyz unreachable: {exc}")

    finally:
        # Best-effort teardown; compose needs OKTO_PULSE_IMAGE to expand the
        # image: directive even on `down`.
        teardown_env = {
            **os.environ,
            "OKTO_PULSE_IMAGE": PINNED_IMAGE,
        }
        subprocess.run(
            [
                "docker",
                "compose",
                "-f",
                str(docker_compose_path),
                "down",
            ],
            env=teardown_env,
            capture_output=True,
            check=False,
            timeout=60,
        )
        # Belt-and-suspenders: force-remove the container if compose missed it.
        subprocess.run(
            ["docker", "rm", "-f", "okto-pulse"],
            capture_output=True,
            check=False,
            timeout=30,
        )
