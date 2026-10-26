"""ID conventions (modular-plan.md §1)."""
from __future__ import annotations

import re

# ISO 3166-2:IN codes for every state/UT name in the national facility directory. Two-letter
# guesses collided (Uttar Pradesh and Uttarakhand both gave "UT"), merging their facilities.
STATE_CODES = {
    "a & n islands": "AN", "andhra pradesh": "AP", "andhra pradesh old": "APO", "arunachal pradesh": "AR",
    "assam": "AS", "bihar": "BR", "chandigarh": "CH", "chhattisgarh": "CT", "dadra & nagar haveli": "DN",
    "daman & diu": "DD", "delhi": "DL", "goa": "GA", "gujarat": "GJ", "haryana": "HR", "himachal pradesh": "HP",
    "jammu & kashmir": "JK", "jharkhand": "JH", "karnataka": "KA", "kerala": "KL", "lakshadweep": "LD",
    "madhya pradesh": "MP", "maharashtra": "MH", "manipur": "MN", "meghalaya": "ML", "mizoram": "MZ",
    "nagaland": "NL", "odisha": "OR", "puducherry": "PY", "punjab": "PB", "rajasthan": "RJ", "sikkim": "SK",
    "tamil nadu": "TN", "telangana": "TG", "tripura": "TR", "uttar pradesh": "UP", "uttarakhand": "UT",
    "west bengal": "WB",
}
assert len(set(STATE_CODES.values())) == len(STATE_CODES), "state codes must be unique"

_SLUG_RE = re.compile(r"[^a-z0-9]+")

# Known spelling variants across government data sources for the same
# district (found while joining HMIS district names against the facility
# directory -- data/README.md). Add entries here as more mismatches turn up;
# this is the one place district-name normalisation happens.
_DISTRICT_ALIASES = {
    "ahmadnagar": "ahmednagar",
}


def slugify(text: str) -> str:
    return _SLUG_RE.sub("-", text.strip().lower()).strip("-")


def state_code(state_name: str) -> str:
    """ISO code, or the full name for a state not in the map (never a lossy two-letter guess)."""
    return STATE_CODES.get(state_name.strip().lower(), slugify(state_name).upper())


def district_id(state_name: str, district_name: str) -> str:
    """e.g. district_id("Maharashtra", "Nashik") -> "mh/nashik"."""
    code = state_code(state_name)
    slug = _DISTRICT_ALIASES.get(slugify(district_name), slugify(district_name))
    return f"{code.lower()}/{slug}"


def facility_id(state_name: str, sequence: int | str) -> str:
    """e.g. facility_id("Maharashtra", 1234) -> "MH-1234" (state-prefixed)."""
    code = state_code(state_name)
    return f"{code}-{int(sequence):07d}" if isinstance(sequence, int) or str(sequence).isdigit() else f"{code}-{sequence}"


def drug_id(name: str, strength: str | None = None) -> str:
    """e.g. drug_id("ORS", "New WHO") -> "ors-new-who"."""
    parts = [name] + ([strength] if strength else [])
    return slugify(" ".join(parts))
