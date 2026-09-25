"""
features.py - time-domain feature extraction, used by BOTH:
  - ai/src/train_classifier.py   (training, offline)
  - backend/main.py              (inference, live)

so the exact same numbers are computed both times.

Two classification paths exist, and the backend picks between them honestly
at request time (see backend/main.py):

  1. TRAINED MODEL (ai/models/classifier.joblib), if it exists. A real
     scikit-learn classifier trained on labeled Healthy / Corrosion /
     Loose Bolt samples (see ai/src/train_classifier.py). This is only
     ever loaded if the file is actually present -- nothing here pretends
     a model exists when it doesn't.

  2. FIXED-THRESHOLD FALLBACK (classify_by_magnitude), used only when no
     trained model file is found. This is NOT a trained ML model. It
     classifies on peak-to-peak magnitude alone and has not been
     calibrated against real damaged specimens. Every result produced
     this way is labeled accordingly so it can never be mistaken for a
     real model's output.
"""
import math
from typing import Dict, List


def magnitude(xs: List[float], ys: List[float], zs: List[float]) -> List[float]:
    return [math.sqrt(x * x + y * y + z * z) for x, y, z in zip(xs, ys, zs)]


def summarize(xs, ys, zs) -> Dict:
    """Human-readable summary shown in the UI/report. Kept separate from
    the feature vector below so UI fields don't silently change if the
    model's feature set changes."""
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


FEATURE_NAMES = [
    "mean_x", "std_x", "ptp_x",
    "mean_y", "std_y", "ptp_y",
    "mean_z", "std_z", "ptp_z",
    "mean_mag", "std_mag", "ptp_mag", "rms_mag",
]


def _axis_stats(vals: List[float]):
    n = len(vals)
    mean_v = sum(vals) / n
    std_v = math.sqrt(sum((v - mean_v) ** 2 for v in vals) / n)
    ptp_v = max(vals) - min(vals)
    return mean_v, std_v, ptp_v


def extract_feature_vector(xs: List[float], ys: List[float], zs: List[float]) -> List[float]:
    """Fixed-length numeric feature vector for the ML classifier.
    Order MUST match FEATURE_NAMES and must be identical between
    training and inference -- both call this same function."""
    mx, sx, px = _axis_stats(xs)
    my, sy, py = _axis_stats(ys)
    mz, sz, pz = _axis_stats(zs)
    mag = magnitude(xs, ys, zs)
    mm, sm, pm = _axis_stats(mag)
    rms_m = math.sqrt(sum(m * m for m in mag) / len(mag))
    return [mx, sx, px, my, sy, py, mz, sz, pz, mm, sm, pm, rms_m]


# PLACEHOLDER thresholds on peak-to-peak magnitude (sensor units). NOT
# calibrated against any real damage data. Used only as a fallback when
# no trained model file is present -- see module docstring above.
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
        "confidence": None,
        "peak_to_peak_magnitude": pp,
        "method": "fixed-threshold-on-peak-to-peak (NOT a trained ML model, "
                  "NOT calibrated -- no trained classifier file was found)",
    }
