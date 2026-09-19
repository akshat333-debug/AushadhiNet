"""Enforces architecture.md §5: nothing outside ml/generator/ and eval/ may
import ml.generator. This is what makes "the forecaster cannot learn back
the generator's formula" a checked fact rather than a promise.

Passes on the current (empty) tree. If ml/generator/ does not exist yet,
there is nothing to isolate, so the AST scan trivially passes -- but the
scratch-module check below still proves the *scanner itself* would catch
a violation once ml/generator/ exists.
"""
from __future__ import annotations

import ast
import pathlib

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
ALLOWED_IMPORTER_PREFIXES = ("ml/generator/", "eval/")


def _iter_python_files():
    for pkg in ("backend", "ml", "eval"):
        base = REPO_ROOT / pkg
        if not base.exists():
            continue
        yield from base.rglob("*.py")


def _imports_ml_generator(py_file: pathlib.Path) -> bool:
    tree = ast.parse(py_file.read_text(), filename=str(py_file))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            if any(alias.name == "ml.generator" or alias.name.startswith("ml.generator.") for alias in node.names):
                return True
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module == "ml.generator" or module.startswith("ml.generator."):
                return True
            # relative "from . import generator" inside ml/ package
            if node.level and node.module == "generator":
                return True
    return False


def _relative_posix(py_file: pathlib.Path) -> str:
    return py_file.relative_to(REPO_ROOT).as_posix()


def test_no_forbidden_module_imports_ml_generator():
    violations = []
    for py_file in _iter_python_files():
        rel = _relative_posix(py_file)
        if any(rel.startswith(prefix) for prefix in ALLOWED_IMPORTER_PREFIXES):
            continue
        if _imports_ml_generator(py_file):
            violations.append(rel)
    assert not violations, f"ml.generator imported outside generator/eval: {violations}"


def test_scanner_actually_detects_a_violation(tmp_path, monkeypatch):
    import tests.test_isolation as this_module
    """Prove the scanner has teeth: point it at a scratch tree containing a
    deliberate violation and confirm it is caught."""
    fake_root = tmp_path
    (fake_root / "backend").mkdir()
    offender = fake_root / "backend" / "leaky.py"
    offender.write_text("import ml.generator\n")

    monkeypatch.setattr(this_module, "REPO_ROOT", fake_root)
    violations = []
    for py_file in _iter_python_files():
        rel = _relative_posix(py_file)
        if any(rel.startswith(prefix) for prefix in ALLOWED_IMPORTER_PREFIXES):
            continue
        if _imports_ml_generator(py_file):
            violations.append(rel)
    assert violations == ["backend/leaky.py"]


def test_scanner_allows_eval_and_generator_to_import_it(tmp_path, monkeypatch):
    import tests.test_isolation as this_module
    fake_root = tmp_path
    (fake_root / "eval").mkdir()
    (fake_root / "eval" / "seal_generator.py").write_text("import ml.generator\n")
    (fake_root / "ml").mkdir()
    (fake_root / "ml" / "generator").mkdir()
    (fake_root / "ml" / "generator" / "cli.py").write_text("from . import ledger\n")

    monkeypatch.setattr(this_module, "REPO_ROOT", fake_root)
    violations = []
    for py_file in _iter_python_files():
        rel = _relative_posix(py_file)
        if any(rel.startswith(prefix) for prefix in ALLOWED_IMPORTER_PREFIXES):
            continue
        if _imports_ml_generator(py_file):
            violations.append(rel)
    assert violations == []

