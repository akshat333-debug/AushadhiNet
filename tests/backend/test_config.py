"""DoD test for backend/config.py (step 4)."""
from __future__ import annotations

import ast
import pathlib
import re

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]


def test_env_example_has_key_for_every_settings_field():
    from backend.config import Settings

    env_text = (REPO_ROOT / ".env.example").read_text()
    env_keys = {line.split("=", 1)[0] for line in env_text.splitlines()
                if line.strip() and not line.strip().startswith("#") and "=" in line}

    for name, field in Settings.model_fields.items():
        alias = field.validation_alias or name.upper()
        assert str(alias) in env_keys, f"{name} (alias {alias}) missing from .env.example"


def test_env_example_has_no_real_looking_secrets():
    env_text = (REPO_ROOT / ".env.example").read_text()
    # placeholders and known-safe defaults only; nothing that looks like a live key
    suspicious = re.findall(r"=([A-Za-z0-9_\-]{30,})", env_text)
    for value in suspicious:
        assert value in ("REPLACE_ME",) or value.startswith("whatsapp:"), (
            f"suspicious non-placeholder value in .env.example: {value}"
        )


def test_settings_loads_with_defaults(monkeypatch):
    for key in ("AUSHADHI_MODE", "GCP_PROJECT", "GEMINI_API_KEY"):
        monkeypatch.delenv(key, raising=False)
    from backend.config import Settings

    s = Settings(_env_file=None)
    assert s.mode == "local"
    assert s.gcp_project == "REPLACE_ME"
    assert s.confidence_threshold == 0.85


def test_settings_reads_aushadhi_mode_env_var(monkeypatch):
    monkeypatch.setenv("AUSHADHI_MODE", "cloud")
    from backend.config import Settings

    s = Settings(_env_file=None)
    assert s.mode == "cloud"


def test_only_config_module_reads_os_environ():
    """architecture.md §2: ml/ and eval/ never read env; only backend/config.py does."""
    violations = []
    for pkg in ("backend", "ml", "eval"):
        base = REPO_ROOT / pkg
        if not base.exists():
            continue
        for py_file in base.rglob("*.py"):
            rel = py_file.relative_to(REPO_ROOT).as_posix()
            if rel == "backend/config.py":
                continue
            tree = ast.parse(py_file.read_text(), filename=str(py_file))
            for node in ast.walk(tree):
                if isinstance(node, ast.Attribute) and node.attr in ("environ", "getenv"):
                    violations.append(rel)
    assert not violations, f"os.environ/getenv used outside backend/config.py: {violations}"
