import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from agente_ventas import tools


def test_get_cdp_candidates_prefers_env(monkeypatch):
    monkeypatch.setenv("LIGHTPANDA_CDP_URL", "ws://example:9222")

    candidates = tools._get_cdp_candidates()

    assert candidates[0] == "ws://example:9222"


def test_get_cdp_candidates_includes_docker_fallbacks(monkeypatch):
    monkeypatch.delenv("LIGHTPANDA_CDP_URL", raising=False)
    monkeypatch.setenv("IN_DOCKER", "1")

    candidates = tools._get_cdp_candidates()

    assert "ws://host.docker.internal:9222" in candidates
    assert "ws://127.0.0.1:9222" in candidates
