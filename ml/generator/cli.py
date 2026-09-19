"""Wires real facility/drug/anchor data into ml.generator.generate() and
writes data/synthetic/*.parquet (modular-plan.md §2.8). This is the ONE
file in ml/generator/ allowed to import ml/data/ (the core generator
modules take facilities/drugs/anchors as plain arguments so they stay
testable without ml/data -- see ml/generator/__init__.py's ordering note).

Run via `eval/seal_generator.py`, not directly, so the output is always
paired with sealing the content hash into eval/protocol.lock.
"""
from __future__ import annotations

import pathlib

import pandas as pd

from ml.data.drugs import M19_ITEMS, load_nlem
from ml.data.facilities import load_facilities
from ml.data.hmis_m19 import load_m19
from ml.generator import LedgerBundle, generate
from ml.generator.params import GeneratorParams

OUTPUT_DIR = pathlib.Path(__file__).resolve().parents[2] / "data" / "synthetic"


def _m19_drug_subset() -> tuple[list, dict[str, str]]:
    """Returns (drugs restricted to the 16 HMIS M19 items, {drug_name: drug_id})."""
    all_drugs = load_nlem()
    subset = []
    name_to_id: dict[str, str] = {}
    for item in M19_ITEMS:
        for d in all_drugs:
            if item in d.aliases:
                if d.drug_id not in {x.drug_id for x in subset}:
                    subset.append(d)
                name_to_id[item] = d.drug_id
                break
    return subset, name_to_id


def _build_anchors(district_name: str, name_to_id: dict[str, str]) -> pd.DataFrame:
    panel = load_m19(states=["mah"])
    nashik = panel[panel["district_name"] == district_name].copy()
    nashik["drug_id"] = nashik["drug_name"].map(name_to_id)
    nashik = nashik.dropna(subset=["drug_id", "distributed"])
    return nashik[["district_id", "drug_id", "month", "distributed"]]


def build(seed: int, start, end, output_dir: pathlib.Path = OUTPUT_DIR) -> LedgerBundle:
    facilities = load_facilities(state="Maharashtra", district="Nashik")
    drugs, name_to_id = _m19_drug_subset()
    anchors = _build_anchors("Nashik", name_to_id)

    bundle = generate(
        seed=seed, facilities=facilities, drugs=drugs, start=start, end=end,
        anchors=anchors, params=GeneratorParams(seed=seed),
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    bundle.stock.to_parquet(output_dir / "stock.parquet", index=False)
    bundle.beds.to_parquet(output_dir / "beds.parquet", index=False)
    bundle.attendance.to_parquet(output_dir / "attendance.parquet", index=False)
    return bundle


def main() -> None:
    from eval.protocol import load_protocol

    protocol = load_protocol()
    build(
        seed=protocol.generator_seal.seed,
        start=protocol.real_benchmark.train_start,
        end=protocol.real_benchmark.test_end,
    )
    print(f"wrote synthetic ledger to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
