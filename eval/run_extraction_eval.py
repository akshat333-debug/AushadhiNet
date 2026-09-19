"""Handwriting-extraction evaluation over the labelled register set
(modular-plan.md step 37, AC1's evaluation half).

HONESTY NOTE: `data/labelled_registers/` (as generated today) holds
programmatically RENDERED text images, not real photographed handwriting
-- see scripts/generate_labelled_registers.py's docstring. The default
predictor here calls the REAL extraction pipeline
(backend.ingest.extract.from_image), which in local mode has no fixture
for these renders and will correctly report them as unscored rather than
fabricate a result. A meaningful accuracy number requires either cloud
mode (a real Gemini key) or a real photographed corpus -- this script
does not paper over that gap.
"""
from __future__ import annotations

import json
import pathlib
from collections import defaultdict

from backend.providers.base import ProviderError

from eval.metrics import char_error_rate

LABELLED_DIR = pathlib.Path(__file__).resolve().parents[1] / "data" / "labelled_registers"


def _default_predictor(image_bytes: bytes, entry: dict) -> dict:
    """Calls the real extraction pipeline. Raises ProviderError (surfaced
    as an "unscored" row, not a fabricated result) whenever no fixture/
    real Gemini connection is available for this image."""
    from backend.ingest.extract import from_image

    result = from_image(image_bytes, "image/png", facility_id="eval", reporter_phone_hash="eval")
    if not result.records:
        raise ProviderError("extraction returned no records")
    record = result.records[0]
    return {"drug_name": record.drug_id, "on_hand": record.on_hand, "batch_no": record.batch_no or ""}


def evaluate(labelled_dir: pathlib.Path = LABELLED_DIR, predictor=None, limit: int | None = None) -> dict:
    predictor = predictor or _default_predictor
    manifest = json.loads((labelled_dir / "manifest.json").read_text())
    if limit is not None:
        manifest = manifest[:limit]

    by_script: dict[str, list[dict]] = defaultdict(list)
    unscored = []

    for entry in manifest:
        image_bytes = (labelled_dir / entry["image"]).read_bytes()
        try:
            pred = predictor(image_bytes, entry)
        except ProviderError as e:
            unscored.append({"image": entry["image"], "reason": str(e)})
            continue

        exact = str(pred.get("drug_name", "")).strip().lower() == str(entry["drug_name"]).strip().lower()
        cer = char_error_rate(str(pred.get("drug_name", "")), str(entry["drug_name"]))
        by_script[entry["script"]].append({"exact": exact, "cer": cer})

    report: dict = {}
    for script, rows in by_script.items():
        report[script] = {
            "n": len(rows),
            "exact_match_rate": sum(r["exact"] for r in rows) / len(rows),
            "mean_cer": sum(r["cer"] for r in rows) / len(rows),
        }
    report["_total_images"] = len(manifest)
    report["_scored"] = sum(len(v) for v in by_script.values())
    report["_unscored"] = len(unscored)
    report["_unscored_sample_reason"] = unscored[0]["reason"] if unscored else None
    return report


if __name__ == "__main__":
    print(json.dumps(evaluate(), indent=2))
