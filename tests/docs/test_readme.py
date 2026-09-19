"""DoD test for README.md + docs/api/ (step 46, the final build step)."""
from __future__ import annotations

import pathlib

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]


def test_readme_exists_and_covers_setup_run_test():
    readme = (REPO_ROOT / "README.md").read_text()
    for required in ("Quickstart", "uv sync", "npm install", "pytest", "playwright"):
        assert required in readme, f"README.md missing expected section/command: {required}"


def test_readme_documents_known_limitations_honestly():
    readme = (REPO_ROOT / "README.md").read_text()
    assert "not done yet" in readme.lower() or "honest" in readme.lower()


def test_api_docs_exist_and_list_every_router_prefix():
    api_docs = (REPO_ROOT / "docs" / "api" / "endpoints.md").read_text()
    for prefix in ("/webhooks", "/officer", "/agent", "/public", "/simulator"):
        assert prefix in api_docs, f"docs/api/endpoints.md missing endpoint group: {prefix}"


def test_fresh_clone_script_exists_and_is_executable():
    script = REPO_ROOT / "scripts" / "fresh_clone_check.sh"
    assert script.exists()
    import os
    assert os.access(script, os.X_OK)
