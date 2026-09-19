"""Structural checks on infra/ (AC10). The stack itself was run for real
on 2026-09-19: `docker compose -f infra/docker-compose.yml up --build`,
then the full Playwright suite passed against the containers."""
from __future__ import annotations

import pathlib

import yaml

INFRA_DIR = pathlib.Path(__file__).resolve().parents[2] / "infra"


def test_compose_file_parses_and_has_both_services():
    compose = yaml.safe_load((INFRA_DIR / "docker-compose.yml").read_text())
    assert set(compose["services"].keys()) == {"backend", "frontend"}


def test_backend_service_defaults_to_local_mode_no_credentials_required():
    compose = yaml.safe_load((INFRA_DIR / "docker-compose.yml").read_text())
    backend_env = compose["services"]["backend"]["environment"]
    assert "AUSHADHI_MODE=local" in backend_env
    # no GCP/Twilio credential env var is required for the compose file to be valid --
    # only optional ones with safe local defaults appear in backend/config.py's Settings
    forbidden_hardcoded = [e for e in backend_env if "=" in e and any(
        secret_key in e for secret_key in ("API_KEY=", "AUTH_TOKEN=", "SIGNING_KEY=")
    ) and "REPLACE_ME" not in e]
    assert forbidden_hardcoded == [], f"compose file hardcodes what look like real secrets: {forbidden_hardcoded}"


def test_frontend_service_points_at_backend_service():
    compose = yaml.safe_load((INFRA_DIR / "docker-compose.yml").read_text())
    # NEXT_PUBLIC_* is inlined by `next build`, so it must be a build arg, not a runtime env var.
    assert "NEXT_PUBLIC_API_BASE" in compose["services"]["frontend"]["build"]["args"]
    assert "backend" in compose["services"]["frontend"]["depends_on"]


def test_dockerfiles_exist_and_reference_local_mode():
    backend_dockerfile = (INFRA_DIR / "Dockerfile.backend").read_text()
    assert "AUSHADHI_MODE=local" in backend_dockerfile
    assert (INFRA_DIR / "Dockerfile.frontend").exists()


def test_makefile_has_expected_targets():
    makefile = (INFRA_DIR / "Makefile").read_text()
    for target in ("test", "dev-backend", "dev-frontend", "seal-generator", "run-final", "compose-up"):
        assert f"{target}:" in makefile
