"""
features.py - time-domain features and threshold-based classification.

IMPORTANT: This is NOT a trained ML model. It classifies each tap using
FIXED placeholder thresholds on the signal's own peak-to-peak magnitude.
These threshold values have NOT been calibrated against any real damaged
specimen -- they exist only so the pipeline runs end-to-end today.
Replace classify_by_magnitude() with a trained model once labeled data
from real healthy/damaged taps exists.
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


# PLACEHOLDER thresholds on peak-to-peak magnitude (m/s^2). NOT calibrated
# against any real damage data. Adjust once you have real healthy vs.
# damaged tap comparisons.
WARNING_THRESHOLD = 1.0
ATTENTION_THRESHOLD = 2.0


def classify_by_magnitude(summary: Dict) -> Dict:
    pp = summary["peak_to_peak_magnitude"]

    if pp >= ATTENTION_THRESHOLD:
        label = "Attention"
    elif pp >= WARNING_THRESHOLD:
        label = "Warning"
    else:
        label = "Normal"

    return {
        "classification": label,
        "peak_to_peak_magnitude": pp,
        "method": "fixed-threshold-on-peak-to-peak (NOT a trained ML model, NOT calibrated)",
    }