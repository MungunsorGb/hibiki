"""
inspect_dataset.py  -  HIBIKI-AI, Step 1

Loads a raw X,Y,Z accelerometer CSV, validates it, prints statistics,
saves a plot, and states honestly whether it is usable for training.

Usage (from the project root):
    python ai/src/inspect_dataset.py
    python ai/src/inspect_dataset.py data/raw/my_file.csv
    python ai/src/inspect_dataset.py data/raw/my_file.csv --fs 800

--fs is the sampling frequency in Hz. It is OPTIONAL. If you do not know it,
leave it out: the script will report it as UNKNOWN and use sample index
on the time axis instead of seconds.
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")  # save plots to file, no window needed
import matplotlib.pyplot as plt

AXES = ["X", "Y", "Z"]
MIN_SAMPLES_FOR_IMPACT = 200   # below this, a vibration event can't be analysed
NEAR_CONSTANT_UNIQUE = 3       # <= this many distinct values => essentially constant


def load_xyz(path: Path) -> pd.DataFrame:
    """Read a CSV of 3 columns; detect an optional header row."""
    raw = pd.read_csv(path, header=None, comment="#", skipinitialspace=True,
                      dtype=str, skip_blank_lines=True)
    if raw.shape[1] != 3:
        print(f"[ERROR] Expected exactly 3 columns (X,Y,Z), found {raw.shape[1]}.")
        print("        If your file has a timestamp column, tell me and we will")
        print("        handle it explicitly. I will not guess which column is which.")
        sys.exit(1)

    numeric = raw.apply(pd.to_numeric, errors="coerce")

    # If the first row is entirely non-numeric, treat it as a header and drop it.
    if numeric.iloc[0].isna().all():
        print(f"[INFO] Header row detected and skipped: {list(raw.iloc[0])}")
        numeric = numeric.iloc[1:].reset_index(drop=True)

    numeric.columns = AXES
    return numeric


def validate(df: pd.DataFrame) -> bool:
    """Print validation results. Returns True if the data is structurally valid."""
    ok = True
    print("\n=== VALIDATION ===")
    print(f"Rows (samples): {len(df)}")

    n_nan = int(df.isna().sum().sum())
    if n_nan:
        print(f"[WARN] {n_nan} non-numeric/missing values found (rows with NaN will be dropped).")
    else:
        print("[OK]   All values are numeric.")

    n_inf = int(np.isinf(df.to_numpy(dtype=float)).sum())
    if n_inf:
        print(f"[WARN] {n_inf} infinite values found.")
        ok = False

    if len(df) == 0:
        print("[ERROR] No data rows.")
        return False
    return ok


def describe_axes(df: pd.DataFrame) -> list:
    """Print per-axis statistics. Returns the list of near-constant axes."""
    print("\n=== PER-AXIS STATISTICS ===")
    print("(Units are UNKNOWN: raw counts, g, mg, or m/s^2 cannot be told from the numbers alone.)\n")
    constant_axes = []
    header = f"{'axis':<5}{'mean':>12}{'std':>12}{'min':>12}{'max':>12}{'peak-peak':>12}{'unique':>9}"
    print(header)
    print("-" * len(header))
    for a in AXES:
        s = df[a]
        n_unique = int(s.nunique())
        print(f"{a:<5}{s.mean():>12.3f}{s.std(ddof=0):>12.3f}{s.min():>12.3f}"
              f"{s.max():>12.3f}{(s.max() - s.min()):>12.3f}{n_unique:>9d}")
        if n_unique <= NEAR_CONSTANT_UNIQUE or s.std(ddof=0) < 1e-6:
            constant_axes.append(a)

    # Consecutive identical rows
    same_as_prev = (df.diff().abs().sum(axis=1) == 0).iloc[1:]
    frac = float(same_as_prev.mean()) if len(same_as_prev) else 1.0
    print(f"\nRows identical to the previous row: {frac * 100:.1f}%")
    print(f"Distinct (X,Y,Z) rows in the whole file: {len(df.drop_duplicates())}")
    return constant_axes


def report_sampling(n: int, fs):
    print("\n=== SAMPLING FREQUENCY ===")
    if fs is None:
        print("Sampling frequency: UNKNOWN (no --fs given). Nothing will be assumed.")
        print("Time axis = sample index. Frequency features (FFT) will need a real fs later.")
    else:
        print(f"Sampling frequency: {fs} Hz (provided by you, not verified from the file)")
        print(f"Duration: {n / fs:.3f} s")


def save_plot(df: pd.DataFrame, fs, out_path: Path, title: str):
    x = np.arange(len(df)) if fs is None else np.arange(len(df)) / fs
    xlabel = "Sample index" if fs is None else "Time (s)"
    fig, axs = plt.subplots(3, 1, figsize=(10, 7), sharex=True)
    for ax, a in zip(axs, AXES):
        ax.plot(x, df[a], marker="." if len(df) < 200 else None, linewidth=1)
        ax.set_ylabel(f"{a} (unit unknown)")
        ax.grid(True, alpha=0.3)
    axs[-1].set_xlabel(xlabel)
    fig.suptitle(title)
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=120)
    plt.close(fig)
    print(f"\nPlot saved to: {out_path}")


def verdict(df: pd.DataFrame, constant_axes: list):
    print("\n=== VERDICT ===")
    reasons = []
    if len(constant_axes) == 3:
        reasons.append("All three axes are constant (or take <= 3 distinct values): "
                       "no vibration signal is present.")
    elif constant_axes:
        reasons.append(f"Axes {constant_axes} are constant.")
    if len(df) < MIN_SAMPLES_FOR_IMPACT:
        reasons.append(f"Only {len(df)} samples; an impact response needs many more "
                       f"(at least ~{MIN_SAMPLES_FOR_IMPACT}, realistically thousands).")
    reasons.append("No labels exist in this file, so supervised training is impossible regardless.")

    if len(constant_axes) == 3 or len(df) < MIN_SAMPLES_FOR_IMPACT:
        print("NOT SUITABLE FOR TRAINING. Reasons:")
    else:
        print("Signal has variation, BUT note:")
    for r in reasons:
        print(f"  - {r}")
    print("\nThis file is useful only to test that the code runs.")
    print("Real impact recordings from the hardware are required for the actual model.")


def main():
    p = argparse.ArgumentParser(description="Inspect a raw X,Y,Z accelerometer CSV.")
    p.add_argument("csv", nargs="?", default="data/raw/sample_vibration.csv")
    p.add_argument("--fs", type=float, default=None,
                   help="Sampling frequency in Hz, only if you actually know it.")
    args = p.parse_args()

    path = Path(args.csv)
    if not path.exists():
        print(f"[ERROR] File not found: {path}")
        print("        Run this from the Hibiki-AI/ folder, and check the filename.")
        sys.exit(1)
    if args.fs is not None and args.fs <= 0:
        print("[ERROR] --fs must be positive.")
        sys.exit(1)

    print(f"Inspecting: {path}")
    df = load_xyz(path)
    ok = validate(df)
    df = df.dropna().reset_index(drop=True)
    if len(df) == 0:
        sys.exit(1)

    constant_axes = describe_axes(df)
    report_sampling(len(df), args.fs)
    out_png = Path("data/processed") / f"inspection_{path.stem}.png"
    save_plot(df, args.fs, out_png, f"Raw signal: {path.name}")
    verdict(df, constant_axes)

    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()