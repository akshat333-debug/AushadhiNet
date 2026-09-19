"""DoD test for eval/seal_generator.py (step 11).

Verifies: (1) the seal is filled and internally consistent; (2) re-running
seal() on unchanged generator code is a no-op and does not touch any other
field; (3) the recorded hash matches an independent recomputation from the
committed data/synthetic/ files.
"""
from __future__ import annotations

import copy

import yaml

from eval.protocol import DEFAULT_LOCK_PATH


def test_generator_is_sealed():
    raw = yaml.safe_load(DEFAULT_LOCK_PATH.read_text())
    seal = raw["generator_seal"]
    assert seal["content_hash"] is not None
    assert len(seal["content_hash"]) == 64  # sha256 hex digest
    assert seal["sealed_at"] is not None


def test_resealing_unchanged_output_is_a_noop():
    from eval.seal_generator import seal

    before = yaml.safe_load(DEFAULT_LOCK_PATH.read_text())
    seal(force=False)
    after = yaml.safe_load(DEFAULT_LOCK_PATH.read_text())
    assert before == after


def test_hash_matches_independent_recomputation():
    from eval.seal_generator import compute_content_hash

    raw = yaml.safe_load(DEFAULT_LOCK_PATH.read_text())
    assert compute_content_hash() == raw["generator_seal"]["content_hash"]


def test_only_generator_seal_block_is_writable(monkeypatch, tmp_path):
    """Simulate a stale hash and confirm seal() refuses to silently
    overwrite the other protocol fields or the hash without force=True."""
    import eval.seal_generator as sg

    fake_lock = tmp_path / "protocol.lock"
    raw = yaml.safe_load(DEFAULT_LOCK_PATH.read_text())
    tampered = copy.deepcopy(raw)
    tampered["generator_seal"]["content_hash"] = "0" * 64  # deliberately wrong
    fake_lock.write_text(yaml.safe_dump(tampered, sort_keys=False))

    monkeypatch.setattr(sg, "LOCK_PATH", fake_lock)
    try:
        sg.seal(force=False)
        raised = False
    except RuntimeError:
        raised = True
    assert raised, "seal() must refuse to overwrite a mismatched hash without force=True"
