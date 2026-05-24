import os
import numpy as np

# ---------------------------------------------------------------------------
# Config — overridable via environment variables (container use)
# ---------------------------------------------------------------------------
ensemble_dir = os.environ.get("ENSEMBLE_DIR", "output")
n_runs       = int(os.environ.get("N_RUNS", "10000"))
output_csv   = os.environ.get("OUTPUT_CSV", "convergence.csv")
output_png   = os.environ.get("OUTPUT_PNG", "convergence.png")
output_npy   = os.environ.get("OUTPUT_NPY", "prob_final.npy")
case_label   = os.environ.get("CASE_LABEL", "")

# A convergence curve is built by aggregating the first K runs of a SINGLE
# ensemble. Runs are independent and seeded by run number, so the first K runs
# are a valid K-run ensemble — no need to launch the pipeline once per N.
CHECKPOINTS = [30, 50, 100, 200, 500, 1000, 2000, 5000, 10000]
NODATA = -9999.0


def grid_path(i):
    return os.path.join(ensemble_dir, f"run_{i:03d}", f"run_{i:03d}_ArrivalTime.asc")


# ---------------------------------------------------------------------------
# Step 1 — Locate a reference grid to fix the array shape
# ---------------------------------------------------------------------------
ref_shape = None
for i in range(1, n_runs + 1):
    p = grid_path(i)
    if os.path.exists(p):
        ref_shape = np.loadtxt(p, skiprows=6).shape
        break

if ref_shape is None:
    print("No ArrivalTime files found. Run the ensemble first.")
    raise SystemExit(1)

print(f"Reference grid shape: {ref_shape}")

# ---------------------------------------------------------------------------
# Step 2 — Incremental aggregation. Accumulate burned counts cell by cell and
# snapshot the probability field at each checkpoint. Memory-light: one int32
# grid in memory, not N grids.
# ---------------------------------------------------------------------------
cumcount = np.zeros(ref_shape, dtype=np.int32)
used = 0
skipped = 0
prob_at = {}            # K -> probability field aggregated over the first K runs
checkpoints = sorted(c for c in CHECKPOINTS if c <= n_runs)

for i in range(1, n_runs + 1):
    p = grid_path(i)
    if not os.path.exists(p):
        continue
    grid = np.loadtxt(p, skiprows=6)
    if grid.shape != ref_shape:        # leftover grids from another case in the bucket
        skipped += 1
        continue
    cumcount += (grid != NODATA)
    used += 1
    if used in checkpoints:
        prob_at[used] = cumcount / used

# Always snapshot the final state (full ensemble) as the convergence reference.
prob_final = cumcount / used
if used not in prob_at:
    prob_at[used] = prob_final

print(f"Aggregated {used} runs" + (f" (skipped {skipped} mismatched)" if skipped else ""))

# ---------------------------------------------------------------------------
# Step 3 — Self-convergence metric: how close is the K-run map to the final map?
#   IoU of the 50% footprint  → does the SHAPE stop changing?
#   mean |Δ| per cell         → does the per-cell probability stop changing?
# ---------------------------------------------------------------------------
def iou(a, b, thr=0.5):
    A, B = a >= thr, b >= thr
    union = (A | B).sum()
    return float((A & B).sum() / union) if union else 1.0


rows = []
for k in sorted(prob_at):
    rows.append((k,
                 iou(prob_at[k], prob_final),
                 float(np.abs(prob_at[k] - prob_final).mean())))

# ---------------------------------------------------------------------------
# Step 4 — Persist: CSV + final probability grid (.npy, so it never needs to be
# recomputed from the raw grids) + convergence plot.
# ---------------------------------------------------------------------------
np.save(output_npy, prob_final)

with open(output_csv, "w") as f:
    f.write("N,iou_vs_final,mean_abs_diff\n")
    for k, i_, d in rows:
        f.write(f"{k},{i_:.4f},{d:.6f}\n")
print(f"Saved: {output_csv}, {output_npy}")

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ks = [r[0] for r in rows]
fig, ax1 = plt.subplots(figsize=(8, 4.5))
ax1.plot(ks, [r[1] for r in rows], "o-", color="#B71C1C", label="IoU vs camp final (50%)")
ax1.set_xscale("log")
ax1.set_xlabel("Nombre de simulacions (N)")
ax1.set_ylabel("IoU respecte el camp final", color="#B71C1C")
ax1.tick_params(axis="y", labelcolor="#B71C1C")
ax1.set_ylim(0, 1.02)
ax1.grid(True, which="both", alpha=0.3)

ax2 = ax1.twinx()
ax2.plot(ks, [r[2] for r in rows], "s--", color="#1565C0", label="Δ mitjà per cel·la")
ax2.set_ylabel("Diferència mitjana de probabilitat per cel·la", color="#1565C0")
ax2.tick_params(axis="y", labelcolor="#1565C0")

title = "Convergència de l'ensemble"
if case_label:
    title += f" — {case_label}"
fig.suptitle(title, fontsize=12, fontweight="bold")
fig.tight_layout()
fig.savefig(output_png, dpi=150, bbox_inches="tight")
print(f"Saved: {output_png}")
