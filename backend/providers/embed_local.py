"""Local embedding provider (modular-plan.md §2.2): a deterministic hashed
bag-of-character-ngrams vector, good enough for exact/near-duplicate drug-
name matching in tests and the offline demo without a real embedding API.
"""
from __future__ import annotations

import hashlib

import numpy as np

_DIM = 256


class LocalEmbedProvider:
    def embed(self, texts: list[str]) -> np.ndarray:
        vectors = np.zeros((len(texts), _DIM), dtype=float)
        for i, text in enumerate(texts):
            normalized = text.strip().lower()
            for n in (2, 3, 4):
                for j in range(max(0, len(normalized) - n + 1)):
                    gram = normalized[j:j + n]
                    bucket = int(hashlib.sha256(gram.encode()).hexdigest(), 16) % _DIM
                    vectors[i, bucket] += 1.0
            norm = np.linalg.norm(vectors[i])
            if norm > 0:
                vectors[i] /= norm
        return vectors
