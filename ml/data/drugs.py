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

The 15 stock items reported by HMIS M19 do not use NLEM's formal medicine
names (e.g. "ORS (New WHO)" vs NLEM's "Oral Rehydration Salts"), so this
loader also guarantees each M19 item is present, either as an alias on an
already-parsed NLEM entry (matched by simple substring) or, failing that,
as its own drug entry -- this is what step 8's DoD test checks.
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

    _ensure_m19_items_present(drugs)
    return list(drugs.values())


def _ensure_m19_items_present(drugs: dict[str, Drug]) -> None:
    for item in M19_ITEMS:
        item_key = re.sub(r"[^a-z0-9]+", "", item.lower())
        matched = False
        for d in drugs.values():
            name_key = re.sub(r"[^a-z0-9]+", "", d.name.lower())
            if name_key in item_key or item_key in name_key or _share_first_word(d.name, item):
                if item not in d.aliases:
                    d.aliases.append(item)
                matched = True
                break
        if not matched:
            did = drug_id(item)
            if did not in drugs:
                drugs[did] = Drug(drug_id=did, name=item, unit="unit", nlem_level="P", aliases=[item])


def _share_first_word(a: str, b: str) -> bool:
    wa = re.findall(r"[a-z]+", a.lower())
    wb = re.findall(r"[a-z]+", b.lower())
    return bool(wa) and bool(wb) and wa[0] == wb[0] and len(wa[0]) > 3
