"""Runs the sealed generator once for real and fills protocol.lock's
generator_seal (content_hash, sealed_at) -- modular-plan.md §2.10, step 11.

This is the ONLY script allowed to write to eval/protocol.lock after its
initial commit, and only the generator_seal block. It refuses to reseal
once content_hash is set unless the regenerated output hashes identically
(idempotent reruns are fine; changing the generator after sealing is not
-- that would silently invalidate every number in eval/reports/).
"""
from __future__ import annotations

import hashlib
import pathlib
import sys
from datetime import datetime, timezone

import yaml

from ml.generator.cli import OUTPUT_DIR, build

LOCK_PATH = pathlib.Path(__file__).resolve().parent / "protocol.lock"
OUTPUT_FILES = ("stock.parquet", "beds.parquet", "attendance.parquet")


def compute_content_hash(output_dir: pathlib.Path = OUTPUT_DIR) -> str:
    """sha256 over the sorted concatenation of output parquet bytes."""
    hasher = hashlib.sha256()
    for name in sorted(OUTPUT_FILES):
        hasher.update((output_dir / name).read_bytes())
    return hasher.hexdigest()


def seal(force: bool = False) -> str:
    raw = yaml.safe_load(LOCK_PATH.read_text())
    seal_block = raw["generator_seal"]

    from eval.protocol import load_protocol

    protocol = load_protocol()
    build(seed=seal_block["seed"], start=protocol.real_benchmark.train_start, end=protocol.real_benchmark.test_end)
    new_hash = compute_content_hash()

    if seal_block["content_hash"] is not None:
        if new_hash == seal_block["content_hash"]:
            print("generator output unchanged; hash already sealed, nothing to do.")
            return new_hash
        if not force:
            raise RuntimeError(
                "generator output has changed since sealing "
                f"(was {seal_block['content_hash']}, now {new_hash}). "
                "The generator must not change after sealing. Pass force=True "
                "only if you are deliberately re-sealing with full awareness "
                "that every eval/reports/ run under the old hash is now stale."
            )

    seal_block["content_hash"] = new_hash
    seal_block["sealed_at"] = datetime.now(timezone.utc).isoformat()
    raw["generator_seal"] = seal_block
    LOCK_PATH.write_text(yaml.safe_dump(raw, sort_keys=False))
    return new_hash


if __name__ == "__main__":
    force = "--force" in sys.argv
    h = seal(force=force)
    print(f"sealed. generator content_hash = {h}")
