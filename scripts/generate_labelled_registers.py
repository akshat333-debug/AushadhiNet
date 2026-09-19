"""Generates the handwriting-extraction evaluation set (data/README.md
§6.3, modular-plan.md step 37).

HONESTY NOTE, read before citing any number this produces: these are
programmatically RENDERED text images (PIL drawing text in a Devanagari/
Tamil/Bengali/Latin font onto a paper-like background), not photographs
of real handwritten PHC stock registers. They are a stand-in that lets
the extraction-evaluation PIPELINE be built and tested end-to-end now.
They are NOT a substitute for the real ≥200-image, two-annotator-labelled
corpus of actual photographed handwriting that data/README.md §6.3
describes and that AC1's evaluation half requires -- real handwriting
recognition difficulty (stroke variation, degradation, mixed scripts
written by hand) is exactly what a rendered font cannot simulate.
Do not report accuracy figures from this set as real-world extraction
accuracy in the pitch deck; report them as "extraction pipeline verified
end-to-end on N rendered fixtures" instead, and replace this set with
real photographs before citing a real number.
"""
from __future__ import annotations

import json
import pathlib
import random

from PIL import Image, ImageDraw, ImageFont

OUT_DIR = pathlib.Path(__file__).resolve().parents[1] / "data" / "labelled_registers"

_FONTS = {
    "devanagari": "/System/Library/Fonts/Supplemental/DevanagariMT.ttc",
    "tamil": "/System/Library/Fonts/Supplemental/Tamil MN.ttc",
    "bengali": "/System/Library/Fonts/Supplemental/Bangla MN.ttc",
}
_FALLBACK_FONT = "/System/Library/Fonts/Supplemental/Arial Unicode.ttf"

_DRUG_LINES = {
    "devanagari": [("ओआरएस", "ORS"), ("झिंक २० मिग्रॅ", "Zinc 20mg"), ("पॅरासिटामॉल", "Paracetamol"), ("अल्बेंडाझोल", "Albendazole")],
    "tamil": [("ஓஆர்எஸ்", "ORS"), ("ஜிங்க் 20 மி.கி.", "Zinc 20mg"), ("பாராசிட்டமால்", "Paracetamol")],
    "bengali": [("ওআরএস", "ORS"), ("জিঙ্ক ২০ মিগ্রা", "Zinc 20mg"), ("প্যারাসিটামল", "Paracetamol")],
    "english": [("ORS", "ORS"), ("Zinc 20mg", "Zinc 20mg"), ("Paracetamol", "Paracetamol"), ("Albendazole", "Albendazole")],
}


def _render_one(script: str, drug_native: str, drug_canonical: str, quantity: int, batch: str, seed: int) -> tuple[Image.Image, dict]:
    rng = random.Random(seed)
    img = Image.new("RGB", (500, 140), color=(250, 246, 232))  # off-white "paper"
    draw = ImageDraw.Draw(img)
    font_path = _FONTS.get(script, _FALLBACK_FONT)
    try:
        font = ImageFont.truetype(font_path, 32)
    except OSError:
        font = ImageFont.truetype(_FALLBACK_FONT, 32)

    degrade = rng.random() < 0.3  # a third of the set gets a legibility hit, like the real set will
    line = f"{drug_native}   {quantity}   {batch}"
    color = (90, 90, 90) if degrade else (20, 20, 20)
    draw.text((20 + rng.randint(-3, 3), 40 + rng.randint(-3, 3)), line, font=font, fill=color)
    if degrade:
        # a crude strikethrough / fade artifact, standing in for real degradation
        draw.line([(20, 90), (300, 88)], fill=(200, 200, 200), width=2)

    label = {
        "script": script, "drug_name": drug_canonical, "on_hand": quantity, "batch_no": batch,
        "degraded": degrade, "source": "rendered", "annotators": ["auto-gen-1", "auto-gen-1"],
    }
    return img, label


def generate(n: int = 220, seed: int = 20260918) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)
    scripts = list(_DRUG_LINES.keys())

    manifest = []
    for i in range(n):
        script = scripts[i % len(scripts)]
        drug_native, drug_canonical = rng.choice(_DRUG_LINES[script])
        quantity = rng.randint(1, 200)
        batch = f"B{rng.randint(100, 999)}"
        img, label = _render_one(script, drug_native, drug_canonical, quantity, batch, seed=seed + i)

        name = f"reg_{i:04d}"
        img.save(OUT_DIR / f"{name}.png")
        label["image"] = f"{name}.png"
        (OUT_DIR / f"{name}.json").write_text(json.dumps(label, ensure_ascii=False, indent=2))
        manifest.append(label)

    (OUT_DIR / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    (OUT_DIR / "README.md").write_text(
        "# Rendered extraction-evaluation set (NOT real handwriting)\n\n"
        "See scripts/generate_labelled_registers.py's module docstring for the honesty note this "
        "directory needs read before its numbers are cited anywhere.\n"
    )
    print(f"wrote {len(manifest)} labelled images to {OUT_DIR}")


if __name__ == "__main__":
    generate()
