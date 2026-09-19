"""TimesFM zero-shot forecaster (modular-plan.md §2.11): an ensemble
member that needs no training, useful for facilities with short history.

TimesFM's real backend (torch or jax) plus its hosted checkpoint (a
multi-GB download from Hugging Face) are a heavy, optional dependency --
not installed by default here, the same class of gap as
ml/forecast/arima_bqml.py's cloud-only baseline, just for a different
reason (local resource cost, not cloud-only availability). `is_available()`
checks for the backend without triggering a download; `ensemble.py` must
work correctly whether or not this member is available.
"""
from __future__ import annotations

import numpy as np


def is_available() -> bool:
    """True if a TimesFM inference backend (torch or jax) is importable.
    Does not download or load the checkpoint -- that only happens inside
    fit_predict(), the first time it is actually called."""
    try:
        import torch  # noqa: F401
        return True
    except ImportError:
        pass
    try:
        import jax  # noqa: F401
        return True
    except ImportError:
        return False


_MODEL_CACHE: dict[str, object] = {}


def _load_model():
    """Loads the TimesFM 2.5 checkpoint (downloaded once, then cached for
    the process lifetime). Only called when is_available() is True and a
    caller actually requests a zero-shot forecast."""
    if "model" in _MODEL_CACHE:
        return _MODEL_CACHE["model"]
    import timesfm

    model = timesfm.timesfm_2p5.TimesFM_2p5_200M_torch.from_pretrained("google/timesfm-2.5-200m-pytorch")
    model.compile(timesfm.ForecastConfig(max_context=512, max_horizon=64))
    _MODEL_CACHE["model"] = model
    return model


def fit_predict(history: np.ndarray, horizon: int) -> np.ndarray:
    """Zero-shot point forecast for one series. Raises RuntimeError with a
    clear message if no backend is available, rather than a cryptic
    ImportError deep in a dependency."""
    if not is_available():
        raise RuntimeError(
            "TimesFM backend (torch or jax) is not installed. This is an "
            "optional ensemble member -- ml/forecast/ensemble.py runs "
            "without it. Install `timesfm[torch]` to enable it."
        )
    history = np.asarray(history, dtype=float)
    if len(history) == 0:
        raise ValueError("empty history")
    model = _load_model()
    point_forecast, _quantiles = model.forecast(horizon=horizon, inputs=[history])
    return np.asarray(point_forecast[0][:horizon], dtype=float)
