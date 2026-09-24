"""
features.py - time-domain features and threshold-based comparison.

IMPORTANT: This is NOT a trained ML model. It compares each tap's signal
against a baseline you capture yourself, using placeholder thresholds.
It has NOT been validated against any real damaged specimen. Replace
classify_against_baseline() with a trained model once labeled data exists.
"""
import math
from typing import List, Dict


def magnitude(xs: List[float], ys: List[float], zs: List[float]) -> List[float]:
    return [math.sqrt(x * x + y * y + z * z) for x, y, z in zip(xs, ys, zs)]


def summarize(xs, ys, zs) -> Dict:
    mag = magnitude(xs, ys, zs)
    n = len(mag)
    mean_m = sum(mag) / n
    std_m = math.sqrt(sum((m - mean_m) ** 2 for m in mag) / n)
    pp_m = max(mag) - min(mag)
    rms_m = math.sqrt(sum(m * m for m in mag) / n)
    return {
        "n_samples": n,
        "mean_magnitude": round(mean_m, 4),
        "std_magnitude": round(std_m, 4),
        "peak_to_peak_magnitude": round(pp_m, 4),
        "rms_magnitude": round(rms_m, 4),
    }


# PLACEHOLDER thresholds. Not calibrated against any real damage data.
WARNING_DEVIATION_PCT = 25.0
ATTENTION_DEVIATION_PCT = 60.0


def classify_against_baseline(current: Dict, baseline: Dict) -> Dict:
    base_pp = baseline["peak_to_peak_magnitude"] or 1e-9
    dev_pct = abs(current["peak_to_peak_magnitude"] - base_pp) / base_pp * 100.0

    if dev_pct >= ATTENTION_DEVIATION_PCT:
        label = "Attention"
    elif dev_pct >= WARNING_DEVIATION_PCT:
        label = "Warning"
    else:
        label = "Normal"

    return {
        "classification": label,
        "deviation_pct": round(dev_pct, 2),
        "method": "threshold-on-baseline-deviation (NOT a trained ML model)",
    }