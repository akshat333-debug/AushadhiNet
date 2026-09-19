"""Client-side differential privacy: clip the parameter update to a fixed
L2 norm, then add calibrated Gaussian noise (modular-plan.md §2.13). This
is what actually leaves a state's boundary -- a clipped, noised delta,
never a raw row (AC9).
"""
from __future__ import annotations

import numpy as np


def clip_update(delta: list[np.ndarray], clip_norm: float) -> list[np.ndarray]:
    """Clips the flattened update to L2 norm <= clip_norm, scaling every
    array by the same factor so relative structure is preserved."""
    total_norm = float(np.sqrt(sum(np.sum(np.square(d)) for d in delta)))
    if total_norm <= clip_norm or total_norm == 0:
        return [d.copy() for d in delta]
    scale = clip_norm / total_norm
    return [d * scale for d in delta]


def add_noise(delta: list[np.ndarray], clip_norm: float, noise_multiplier: float, rng: np.random.Generator) -> list[np.ndarray]:
    """Gaussian noise with std = noise_multiplier * clip_norm, the
    standard DP-SGD calibration (Abadi et al. 2016)."""
    std = noise_multiplier * clip_norm
    return [d + rng.normal(0.0, std, size=d.shape) for d in delta]


def clip_and_noise(delta: list[np.ndarray], clip_norm: float, noise_multiplier: float, rng: np.random.Generator) -> list[np.ndarray]:
    return add_noise(clip_update(delta, clip_norm), clip_norm, noise_multiplier, rng)
