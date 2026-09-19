"""Parses the NLEM 2022 PDF into a drug master list (modular-plan.md step 8).

The PDF is a multi-column government layout; text extraction is not
perfectly clean (a handful of entries pick up stray table-of-contents
fragments as prefixes -- see `_clean_name`). This gets ~300+ of the ~384
listed medicines with usable names and levels of care, which is the
target: this module builds the master list that the ingest-layer
embedding matcher (built later, backend/ingest/nlem.py) searches against,
not a definitive digitisation of the NLEM document.

ponytail: regex-based PDF text parsing, not a layout-aware parser. Upgrade
to pdfplumber table extraction if the miss rate on real register photos
turns out to matter.

The 16 stock items reported by HMIS M19 do not use NLEM's formal names, and
several are not medicines at all (gloves, transfusion sets, kits). They come
from a hand-curated table (`M19_CATALOGUE`), one distinct drug_id each, listed
first so their short aliases ("ORS", "Zinc") win exact-alias lookups. An
earlier substring matcher mapped "Calcium Tablets" to calcium gluconate
injection and "Blood Transfusion sets" to a mis-parsed entry "B".
"""
from __future__ import annotations

import functools
import pathlib
import re

import pypdf

from backend.domain import Drug
from backend.domain.ids import drug_id

DEFAULT_PDF = pathlib.Path(__file__).resolve().parents[2] / "data" / "raw" / "nlem" / "nlem2022.pdf"

_ENTRY_RE = re.compile(
    r"(?m)^\s*(\d{1,2}\.\d{1,2}\.\d{1,3})\s+"
    r"([A-Za-z][A-Za-z0-9()\-\s/,+.]*?)\s*"
    r"(\*{1,2})?\s+"
    r"((?:P|S|T)(?:\s*,\s*(?:P|S|T))*)\b"
)

# The exact "Parameters" strings HMIS M19 uses (data/README.md).
M19_ITEMS = [
    "Gloves", "MVA Syringes", "Tab. Fluconazole", "Blood Transfusion sets",
    "Gluteraldehyde 2%", "IFA tablets ( Adult)", "IFA - Blue ( Adolescent 10-19 yrs)",
    "IFA- Pink ( Junior 6-10 yrs)", "IFA Syrup (Paediatric)",
    "Paediatrics Antibiotics ( Amoxycillin and Injectable Gentamicin)",
    "Vit A syrup", "ORS (New WHO)", "RTI /STI colour coded syndromic kits ( I to VII)",
    "Zinc 20 mg tablet", "Albendazole 400 mg tablet", "Calcium Tablets",
]

# One entry per M19 item, in M19_ITEMS order. Plain "IFA" is deliberately not an
# alias: it is ambiguous across four products, so it goes to a confirmation card.
M19_CATALOGUE = [
    {"drug_id": "gloves", "name": "Gloves", "form": "consumable", "unit": "pair", "nlem_level": "P", "aliases": ["Gloves", "gloves"]},
    {"drug_id": "mva-syringe", "name": "MVA Syringe", "form": "device", "unit": "piece", "nlem_level": "S", "aliases": ["MVA Syringes", "MVA", "MVA syringe"]},
    {"drug_id": "fluconazole-tab", "name": "Fluconazole tablet", "form": "tablet", "unit": "tablet", "nlem_level": "P", "aliases": ["Tab. Fluconazole", "Fluconazole tablet", "Fluconazole"]},
    {"drug_id": "blood-transfusion-set", "name": "Blood transfusion set", "form": "consumable", "unit": "set", "nlem_level": "S", "aliases": ["Blood Transfusion sets", "BT set", "Transfusion set"]},
    {"drug_id": "glutaraldehyde-2pct", "name": "Glutaraldehyde 2%", "form": "solution", "unit": "bottle", "nlem_level": "P", "aliases": ["Gluteraldehyde 2%", "Glutaraldehyde", "Cidex"]},
    {"drug_id": "ifa-adult", "name": "IFA tablet (adult, red)", "strength": "60 mg iron + 500 mcg folic acid", "form": "tablet", "unit": "tablet", "nlem_level": "P", "aliases": ["IFA tablets ( Adult)", "IFA adult", "IFA red", "Red IFA"]},
    {"drug_id": "ifa-blue", "name": "IFA tablet (adolescent 10-19, blue)", "form": "tablet", "unit": "tablet", "nlem_level": "P", "aliases": ["IFA - Blue ( Adolescent 10-19 yrs)", "IFA blue", "Blue IFA"]},
    {"drug_id": "ifa-pink", "name": "IFA tablet (junior 6-10, pink)", "form": "tablet", "unit": "tablet", "nlem_level": "P", "aliases": ["IFA- Pink ( Junior 6-10 yrs)", "IFA pink", "Pink IFA"]},
    {"drug_id": "ifa-syrup", "name": "IFA syrup (paediatric)", "form": "syrup", "unit": "bottle", "nlem_level": "P", "aliases": ["IFA Syrup (Paediatric)", "IFA syrup"]},
    {"drug_id": "paed-antibiotics", "name": "Paediatric antibiotics (amoxicillin, injectable gentamicin)", "form": "mixed", "unit": "unit", "nlem_level": "P", "aliases": ["Paediatrics Antibiotics ( Amoxycillin and Injectable Gentamicin)", "Paediatric antibiotics"]},
    {"drug_id": "vitamin-a-syrup", "name": "Vitamin A syrup", "form": "syrup", "unit": "bottle", "nlem_level": "P", "aliases": ["Vit A syrup", "Vit A", "Vitamin A", "Vitamin A syrup"]},
    {"drug_id": "ors", "name": "ORS (WHO low-osmolarity)", "form": "sachet", "unit": "sachet", "nlem_level": "P", "aliases": ["ORS (New WHO)", "ORS", "Oral rehydration salts"]},
    {"drug_id": "rti-sti-kit", "name": "RTI/STI colour-coded syndromic kit (I-VII)", "form": "kit", "unit": "kit", "nlem_level": "S", "aliases": ["RTI /STI colour coded syndromic kits ( I to VII)", "RTI kit", "STI kit"]},
    {"drug_id": "zinc-20mg", "name": "Zinc 20 mg dispersible tablet", "strength": "20 mg", "form": "tablet", "unit": "tablet", "nlem_level": "P", "aliases": ["Zinc 20 mg tablet", "Zinc", "Zinc 20mg"]},
    {"drug_id": "albendazole-400mg", "name": "Albendazole 400 mg tablet", "strength": "400 mg", "form": "tablet", "unit": "tablet", "nlem_level": "P", "aliases": ["Albendazole 400 mg tablet", "Albendazole", "Albendazole 400"]},
    {"drug_id": "calcium-tab", "name": "Calcium tablet", "form": "tablet", "unit": "tablet", "nlem_level": "P", "aliases": ["Calcium Tablets", "Calcium", "Calcium tablet"]},
]


def _clean_name(raw: str) -> str:
    """Collapse whitespace/newlines; if the match swallowed a heading and
    a page-footnote number before the real name, keep the text after the
    last newline (empirically where the actual medicine name ends up)."""
    parts = [p.strip() for p in raw.split("\n") if p.strip()]
    candidate = parts[-1] if parts else raw.strip()
    candidate = re.sub(r"^\d+\s+", "", candidate)  # drop a leading footnote number
    return re.sub(r"\s+", " ", candidate).strip()


@functools.lru_cache(maxsize=4)
def _extract_pdf_text(pdf_path: pathlib.Path) -> str:
    # ponytail: process-lifetime cache -- the PDF parse (~3s) is the one
    # slow step here and the file never changes mid-run; upgrade to an
    # on-disk cache if this module starts being called across processes.
    reader = pypdf.PdfReader(pdf_path)
    return "\n".join(page.extract_text() for page in reader.pages)


def load_nlem(pdf_path: pathlib.Path | str = DEFAULT_PDF) -> list[Drug]:
    text = _extract_pdf_text(pathlib.Path(pdf_path))
    drugs: dict[str, Drug] = {}

    for entry_no, raw_name, _star, levels in _ENTRY_RE.findall(text):
        name = _clean_name(raw_name)
        if len(name) < 3:
            continue
        level = sorted(set(levels.replace(" ", "").split(",")), key="PST".index)
        nlem_level = level[0]  # lowest tier it is available at, in P < S < T
        did = drug_id(name)
        if did in drugs:
            continue  # duplicate section cross-reference (NLEM lists some drugs twice)
        drugs[did] = Drug(drug_id=did, name=name, unit="unit", nlem_level=nlem_level, aliases=[name])

    curated = [Drug(**entry) for entry in M19_CATALOGUE]
    curated_ids = {d.drug_id for d in curated}
    return curated + [d for d in drugs.values() if d.drug_id not in curated_ids]
