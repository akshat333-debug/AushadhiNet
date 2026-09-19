"""Forecasting and stock-out evaluation metrics (modular-plan.md §2.10).

WAPE/MASE, not MAPE: PHC drug demand has many zero weeks, where MAPE is
undefined (division by zero) -- project.md §7's reporting rule.
"""
from __future__ import annotations

import numpy as np


def wape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Weighted Absolute Percentage Error: sum|error| / sum|actual|."""
    y_true, y_pred = np.asarray(y_true, dtype=float), np.asarray(y_pred, dtype=float)
    denom = np.abs(y_true).sum()
    if denom == 0:
        return 0.0 if np.abs(y_pred).sum() == 0 else float("inf")
    return float(np.abs(y_true - y_pred).sum() / denom)


def mase(y_true: np.ndarray, y_pred: np.ndarray, train_series: np.ndarray, season_length: int = 1) -> float:
    """Mean Absolute Scaled Error. The denominator is the mean absolute
    seasonal-naive error on the TRAINING window only (never the series
    being scored) -- this is what keeps MASE comparable across series and
    is exactly what tests/eval/test_metrics.py checks."""
    y_true, y_pred = np.asarray(y_true, dtype=float), np.asarray(y_pred, dtype=float)
    train_series = np.asarray(train_series, dtype=float)
    if len(train_series) <= season_length:
        raise ValueError("train_series must be longer than season_length")
    naive_errors = np.abs(train_series[season_length:] - train_series[:-season_length])
    scale = naive_errors.mean()
    if scale == 0:
        return 0.0 if np.allclose(y_true, y_pred) else float("inf")
    return float(np.abs(y_true - y_pred).mean() / scale)


def pinball(y_true: np.ndarray, y_pred_quantile: np.ndarray, quantile: float) -> float:
    """Pinball (quantile) loss for one quantile level in (0, 1)."""
    if not (0.0 < quantile < 1.0):
        raise ValueError("quantile must be in (0, 1)")
    y_true, y_pred_quantile = np.asarray(y_true, dtype=float), np.asarray(y_pred_quantile, dtype=float)
    diff = y_true - y_pred_quantile
    return float(np.mean(np.maximum(quantile * diff, (quantile - 1) * diff)))


def brier(y_true_binary: np.ndarray, p_hat: np.ndarray) -> float:
    """Brier score for probabilistic stock-out predictions."""
    y_true_binary, p_hat = np.asarray(y_true_binary, dtype=float), np.asarray(p_hat, dtype=float)
    return float(np.mean((p_hat - y_true_binary) ** 2))


def stockout_scores(y_true_binary: np.ndarray, p_hat: np.ndarray, horizon: int, threshold: float = 0.5) -> dict:
    """Recall/precision at a probability threshold, plus calibration
    (Brier score), for one forecast horizon."""
    y_true_binary, p_hat = np.asarray(y_true_binary, dtype=bool), np.asarray(p_hat, dtype=float)
    predicted_positive = p_hat >= threshold
    tp = int(np.sum(predicted_positive & y_true_binary))
    fp = int(np.sum(predicted_positive & ~y_true_binary))
    fn = int(np.sum(~predicted_positive & y_true_binary))
    recall = tp / (tp + fn) if (tp + fn) > 0 else float("nan")
    precision = tp / (tp + fp) if (tp + fp) > 0 else float("nan")
    return {
        "horizon": horizon, "recall": recall, "precision": precision,
        "brier": brier(y_true_binary, p_hat), "n": int(len(y_true_binary)),
    }


def char_error_rate(predicted: str, reference: str) -> float:
    """Levenshtein edit distance / len(reference), the standard CER used
    for OCR/ASR evaluation (modular-plan.md step 37)."""
    if reference == "":
        return 0.0 if predicted == "" else 1.0
    prev_row = list(range(len(predicted) + 1))
    for i, r_char in enumerate(reference, start=1):
        curr_row = [i] + [0] * len(predicted)
        for j, p_char in enumerate(predicted, start=1):
            cost = 0 if r_char == p_char else 1
            curr_row[j] = min(curr_row[j - 1] + 1, prev_row[j] + 1, prev_row[j - 1] + cost)
        prev_row = curr_row
    return prev_row[-1] / len(reference)
