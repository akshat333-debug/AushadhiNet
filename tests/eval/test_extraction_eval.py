"""DoD test for eval/run_extraction_eval.py (step 37, AC1's evaluation
half). Uses a fake predictor with controlled, known errors -- NOT real
Gemini -- to prove the metric computation and per-language reporting are
correct. The real, honest result of the default (real-pipeline) predictor
against the current rendered fixture set is separately asserted to be
"unscored, explained why" (see data/README.md / eval/run_extraction_eval.py
docstrings: no real Gemini fixtures exist for the rendered set)."""
from __future__ import annotations

import json

from eval.run_extraction_eval import LABELLED_DIR, evaluate


def test_at_least_200_labelled_images_with_required_scripts():
    manifest = json.loads((LABELLED_DIR / "manifest.json").read_text())
    assert len(manifest) >= 200
    scripts = {entry["script"] for entry in manifest}
    assert {"devanagari", "tamil", "bengali"} <= scripts


def _noisy_predictor_factory(error_rate: float, seed: int = 0):
    import random
    rng = random.Random(seed)

    def predictor(image_bytes: bytes, entry: dict) -> dict:
        if rng.random() < error_rate:
            return {"drug_name": "wrong-drug-xyz", "on_hand": entry["on_hand"], "batch_no": entry["batch_no"]}
        return {"drug_name": entry["drug_name"], "on_hand": entry["on_hand"], "batch_no": entry["batch_no"]}

    return predictor


def test_perfect_predictor_scores_100_percent_and_zero_cer():
    perfect = _noisy_predictor_factory(error_rate=0.0)
    report = evaluate(predictor=perfect, limit=40)
    assert report["_scored"] == 40
    assert report["_unscored"] == 0
    for script in ("devanagari", "tamil", "bengali", "english"):
        if script in report:
            assert report[script]["exact_match_rate"] == 1.0
            assert report[script]["mean_cer"] == 0.0


def test_noisy_predictor_reports_proportional_error_rate():
    noisy = _noisy_predictor_factory(error_rate=0.5, seed=1)
    report = evaluate(predictor=noisy, limit=100)
    overall_exact = sum(report[s]["exact_match_rate"] * report[s]["n"] for s in report if not s.startswith("_")) / report["_scored"]
    assert 0.3 < overall_exact < 0.7  # roughly matches the injected 50% error rate


def test_report_breaks_down_by_language():
    perfect = _noisy_predictor_factory(error_rate=0.0)
    report = evaluate(predictor=perfect, limit=80)
    per_script_keys = {k for k in report if not k.startswith("_")}
    assert {"devanagari", "tamil", "bengali"} <= per_script_keys


def test_default_predictor_against_real_pipeline_is_honestly_unscored():
    """The real, non-noisy result: no Gemini fixtures exist for these
    renders in local mode, so every image is correctly reported as
    unscored with a clear reason -- not silently skipped, not faked."""
    report = evaluate(limit=5)  # default predictor = the real extraction pipeline
    assert report["_scored"] == 0
    assert report["_unscored"] == 5
    assert "fixture" in report["_unscored_sample_reason"] or "Gemini" in report["_unscored_sample_reason"]
