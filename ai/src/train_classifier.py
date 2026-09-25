"""
train_classifier.py - HIBIKI-AI, trains the real 3-class damage classifier.

Classes (fixed, must match folder names exactly):
    Healthy
    Corrosion
    LooseBolt

Expected data layout (create this yourself; it is NOT invented/generated):

    data/sample/
        Healthy/    *.csv   (each file: one tap, 3 columns X,Y,Z, no header
                              OR a header row -- both are auto-detected,
                              same as ai/src/inspect_dataset.py)
        Corrosion/  *.csv
        LooseBolt/  *.csv

Each CSV = one recorded tap. Put as many labeled tap recordings as you have
in the matching class folder. There is no minimum enforced by this script,
but scikit-learn needs at least 2 samples per class to fit, and cross-
validation needs more than that to mean anything -- see the honesty check
below, which will tell you plainly if you don't have enough yet.

Usage (from the project root):
    python ai/src/train_classifier.py

Output:
    ai/models/classifier.joblib   - {"model": ..., "classes": [...]}
    Printed accuracy / per-class report if there's enough data to hold out
    a test split, otherwise a plain statement that there wasn't.

This script does not fabricate metrics. If there isn't enough data to
evaluate honestly, it says so instead of printing a misleading number.
"""
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from backend.features import extract_feature_vector, FEATURE_NAMES  # noqa: E402

CLASSES = ["Healthy", "Corrosion", "LooseBolt"]
DATA_DIR = Path("data/sample")
MODEL_OUT = Path("ai/models/classifier.joblib")
MIN_FOR_TEST_SPLIT = 6  # need at least this many samples total before a held-out test means anything


def load_tap_csv(path: Path):
    raw = pd.read_csv(path, header=None, comment="#", skipinitialspace=True,
                       dtype=str, skip_blank_lines=True)
    if raw.shape[1] != 3:
        print(f"[SKIP] {path}: expected 3 columns (X,Y,Z), found {raw.shape[1]}.")
        return None
    numeric = raw.apply(pd.to_numeric, errors="coerce")
    if numeric.iloc[0].isna().all():
        numeric = numeric.iloc[1:].reset_index(drop=True)
    numeric = numeric.dropna()
    if len(numeric) == 0:
        print(f"[SKIP] {path}: no usable numeric rows.")
        return None
    numeric.columns = ["X", "Y", "Z"]
    return numeric


def main():
    X, y = [], []
    counts = {}

    for cls in CLASSES:
        folder = DATA_DIR / cls
        counts[cls] = 0
        if not folder.exists():
            print(f"[WARN] {folder} does not exist yet.")
            continue
        for csv_path in sorted(folder.glob("*.csv")):
            df = load_tap_csv(csv_path)
            if df is None:
                continue
            feats = extract_feature_vector(df["X"].tolist(), df["Y"].tolist(), df["Z"].tolist())
            X.append(feats)
            y.append(cls)
            counts[cls] += 1

    print("\n=== SAMPLES FOUND ===")
    for cls in CLASSES:
        print(f"  {cls:<12} {counts[cls]} tap(s)")
    total = sum(counts.values())
    print(f"  TOTAL        {total}")

    if total == 0:
        print("\n[NOT SUITABLE FOR TRAINING] No labeled data found in data/sample/.")
        print("This is expected until real labeled taps are added -- nothing is")
        print("invented here. Add CSVs under data/sample/<ClassName>/ and re-run.")
        sys.exit(1)

    zero_classes = [c for c in CLASSES if counts[c] == 0]
    if zero_classes:
        print(f"\n[NOT SUITABLE FOR TRAINING] No samples at all for: {zero_classes}.")
        print("A classifier cannot be trained on classes it has never seen.")
        sys.exit(1)

    min_class_count = min(counts.values())
    if min_class_count < 2:
        print("\n[NOT SUITABLE FOR TRAINING] At least one class has only 1 sample.")
        print("scikit-learn needs at least 2 samples per class to fit at all.")
        sys.exit(1)

    X = np.array(X)
    y = np.array(y)

    do_test_split = total >= MIN_FOR_TEST_SPLIT and min_class_count >= 2
    if do_test_split:
        try:
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.25, random_state=42, stratify=y
            )
        except ValueError:
            # Stratified split not possible with this little data per class.
            do_test_split = False

    if do_test_split:
        model = RandomForestClassifier(n_estimators=200, random_state=42)
        model.fit(X_train, y_train)
        preds = model.predict(X_test)
        acc = accuracy_score(y_test, preds)
        print(f"\n=== HELD-OUT TEST ACCURACY: {acc:.3f} ({len(y_test)} samples) ===")
        print("NOTE: with this few total samples, this number is only a rough")
        print("signal, not a reliable estimate of real-world performance.")
        print(classification_report(y_test, preds, zero_division=0))
        # Refit on everything for the model we actually ship.
        model.fit(X, y)
    else:
        print(f"\n[NO HELD-OUT TEST] Only {total} total samples "
              f"(need >= {MIN_FOR_TEST_SPLIT} with >=2 per class to split honestly).")
        print("Training on all available data with no evaluation held out.")
        print("Treat this model as UNVALIDATED until more labeled data exists.")
        model = RandomForestClassifier(n_estimators=200, random_state=42)
        model.fit(X, y)

    MODEL_OUT.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": model, "classes": list(model.classes_), "feature_names": FEATURE_NAMES}, MODEL_OUT)
    print(f"\nSaved trained model to: {MODEL_OUT}")


if __name__ == "__main__":
    main()
