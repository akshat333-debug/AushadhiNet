"""Drug-name normalisation against the NLEM master (modular-plan.md §2.4):
exact-alias short-circuit, then embedding cosine search for anything that
doesn't match exactly (misspellings, brand names, local-language
transliterations).
"""
from __future__ import annotations

import functools
from dataclasses import dataclass

import numpy as np

from backend.providers import factory
from ml.data.drugs import load_nlem


@dataclass
class DrugMatch:
    drug_id: str
    score: float


class NLEMIndex:
    def __init__(self, drugs=None, embed_provider=None):
        self.drugs = drugs if drugs is not None else load_nlem()
        self.embed_provider = embed_provider or factory.get("embed")

        self.alias_to_id: dict[str, str] = {}
        alias_texts: list[str] = []
        alias_owner: list[str] = []
        for d in self.drugs:
            for alias in {d.name, *d.aliases}:
                key = alias.strip().lower()
                self.alias_to_id.setdefault(key, d.drug_id)
                alias_texts.append(alias)
                alias_owner.append(d.drug_id)

        self._alias_owner = alias_owner
        self._alias_vectors = (
            self.embed_provider.embed(alias_texts) if alias_texts else np.zeros((0, 1))
        )

    def match(self, raw_name: str, k: int = 3) -> list[DrugMatch]:
        key = raw_name.strip().lower()
        if key in self.alias_to_id:
            return [DrugMatch(drug_id=self.alias_to_id[key], score=1.0)]
        if len(self._alias_owner) == 0:
            return []

        query_vec = self.embed_provider.embed([raw_name])[0]
        sims = self._alias_vectors @ query_vec

        best_per_drug: dict[str, float] = {}
        for sim, drug_id in zip(sims, self._alias_owner):
            if drug_id not in best_per_drug or sim > best_per_drug[drug_id]:
                best_per_drug[drug_id] = float(sim)

        ranked = sorted(best_per_drug.items(), key=lambda item: -item[1])[:k]
        return [DrugMatch(drug_id=drug_id, score=score) for drug_id, score in ranked]


@functools.lru_cache(maxsize=1)
def _default_index() -> NLEMIndex:
    return NLEMIndex()


def match(raw_name: str, k: int = 3) -> list[DrugMatch]:
    return _default_index().match(raw_name, k)
