"""Every module the cloud code imports must be installed by the gcp extra.
Regression: pubsub, kms and firebase_admin were imported but never declared,
so cloud mode would have crashed on publish, signing and every officer login."""
from __future__ import annotations

import ast
import importlib
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[3]
CLOUD_FILES = [*sorted((ROOT / "backend" / "providers").glob("*_google.py")), ROOT / "backend" / "deps.py", ROOT / "backend" / "api" / "pubsub_push.py"]


def _cloud_imports() -> set[str]:
    modules = set()
    for path in CLOUD_FILES:
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.ImportFrom) and node.module and node.module.split(".")[0] in ("google", "firebase_admin"):
                modules.add(node.module if node.module != "google" else f"google.{node.names[0].name}")
                if node.module.startswith("google.cloud"):
                    modules.update(f"{node.module}.{a.name}" for a in node.names)
            elif isinstance(node, ast.Import):
                modules.update(a.name for a in node.names if a.name.split(".")[0] in ("google", "firebase_admin"))
    return modules


def test_every_cloud_import_is_installed():
    pytest.importorskip("google.cloud.firestore", reason="gcp extra not installed")
    missing = []
    for name in sorted(_cloud_imports()):
        try:
            importlib.import_module(name)
        except ImportError:
            missing.append(name)
    assert not missing, f"cloud code imports modules the gcp extra does not install: {missing}"
