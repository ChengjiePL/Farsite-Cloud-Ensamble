import numpy as np
import matplotlib.pyplot as plt
import shapefile
import os

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
ensemble_dir = "output"
n_runs       = 10000

observed = [
    ("tests/Case7_ignition", "Ignició (~36 ha)",        "white"),
    ("tests/Per4_utm",       "Final observat (1761 ha)", "#FF3D00"),
]

# ---------------------------------------------------------------------------
# Step 1 — Read all ArrivalTime grids and build burn probability map
# ---------------------------------------------------------------------------
first_path = None
for i in range(1, n_runs + 1):
    candidate = os.path.join(ensemble_dir, f"run_{i:03d}", f"run_{i:03d}_ArrivalTime.asc")
    if os.path.exists(candidate):
        first_path = candidate
        break

if first_path is None:
    print("No ArrivalTime files found in output/. Run the ensemble first.")
    exit(1)

with open(first_path) as f:
    ncols    = int(f.readline().split()[1])
    nrows    = int(f.readline().split()[1])
    xll      = float(f.readline().split()[1])
    yll      = float(f.readline().split()[1])
    cellsize = float(f.readline().split()[1])
xur = xll + ncols * cellsize
yur = yll + nrows * cellsize

print(f"Grid: {ncols}×{nrows} cells, cellsize={cellsize}m")
print(f"Extent: X [{xll:.0f}, {xur:.0f}]  Y [{yll:.0f}, {yur:.0f}]")

burned_count = np.zeros((nrows, ncols), dtype=np.float32)
loaded = 0

for i in range(1, n_runs + 1):
    path = os.path.join(ensemble_dir, f"run_{i:03d}", f"run_{i:03d}_ArrivalTime.asc")
    if not os.path.exists(path):
        continue
    grid = np.loadtxt(path, skiprows=6)
    grid[grid == -9999.0] = np.nan
    burned_count += (~np.isnan(grid)).astype(np.float32)
    loaded += 1

print(f"Loaded {loaded}/{n_runs} runs")

burn_prob = burned_count / loaded
burn_prob[burn_prob == 0] = np.nan

# ---------------------------------------------------------------------------
# Step 2 — Figure: 2 panels
# ---------------------------------------------------------------------------
fig, (ax_obs, ax_prob) = plt.subplots(1, 2, figsize=(22, 10))
fig.suptitle(
    f"FARSITE Case 7 — Dimos Valtetsioy (Arkadia, Grècia) — Ensemble Probabilístic ({loaded} runs)\n"
    "Pertorbació v7: dir Normal(0°,σ=20°) per registre | vel LogNormal(σ=0.20) per registre | Humitat LogNormal(σ=0.25) per run",
    fontsize=13, fontweight="bold"
)

def setup_ax(ax, title):
    bg = np.ones((nrows, ncols)) * 0.95
    ax.imshow(bg, extent=[xll, xur, yll, yur], cmap="gray", vmin=0, vmax=1, origin="upper")
    ax.set_xlim(xll, xur)
    ax.set_ylim(yll, yur)
    ax.set_title(title, fontsize=12, fontweight="bold")
    ax.set_xlabel("Easting (m)", fontsize=10)
    ax.set_ylabel("Northing (m)", fontsize=10)

# ── PANEL 1: Perímetres observats reals ──────────────────────────────────────
setup_ax(ax_obs, "Incendi real observat\n(Nunomoral, Cáceres)")

for i, (filepath, label, color) in enumerate(observed):
    if not os.path.exists(filepath + ".shp"):
        continue
    sf  = shapefile.Reader(filepath)
    pts = np.array(sf.shapes()[0].points)
    if i == 0:
        ax_obs.fill(pts[:, 0], pts[:, 1], color="red", alpha=0.2)
    ax_obs.plot(pts[:, 0], pts[:, 1], color=color, linewidth=2.5, label=label)

ax_obs.legend(loc="upper right", fontsize=9, framealpha=0.9)

# ── PANEL 2: Mapa de probabilitat ────────────────────────────────────────────
setup_ax(ax_prob, f"Mapa de probabilitat de crema\n({loaded} runs)")

cmap_prob = plt.cm.YlOrRd.copy()
cmap_prob.set_bad(color="none")

im = ax_prob.imshow(
    burn_prob,
    extent=[xll, xur, yll, yur],
    cmap=cmap_prob,
    vmin=0, vmax=1,
    interpolation="bilinear",
    alpha=0.85,
    origin="upper",
)
# Colorbar over BOTH panels so it steals space equally and both panels keep
# the same rendered size (otherwise only the right panel shrinks).
cbar = fig.colorbar(im, ax=[ax_obs, ax_prob], shrink=0.6, pad=0.02)
cbar.set_label("Probabilitat de crema", fontsize=11)
cbar.set_ticks([0, 0.25, 0.50, 0.75, 1.0])
cbar.set_ticklabels(["0%", "25%", "50%", "75%", "100%"])

# Contour lines
prob_plot = np.flipud(burn_prob)
prob_plot_filled = np.where(np.isnan(prob_plot), 0, prob_plot)
x_coords = np.linspace(xll, xur, ncols)
y_coords = np.linspace(yll, yur, nrows)

for level, color, lw in [(0.10, "#FFF176", 1.5), (0.50, "#FF6D00", 2.0), (0.90, "#B71C1C", 2.5)]:
    if prob_plot_filled.max() >= level:
        ax_prob.contour(x_coords, y_coords, prob_plot_filled,
                        levels=[level], colors=[color], linewidths=[lw])

# Observed final perimeter as reference
obs_shp_path = observed[1][0]  # Per4_utm path
obs_label    = observed[1][1]
if os.path.exists(obs_shp_path + ".shp"):
    sf = shapefile.Reader(obs_shp_path)
    pts = np.array(sf.shapes()[0].points)
    ax_prob.plot(pts[:, 0], pts[:, 1], color="white",
                 linewidth=2.5, linestyle="--", label=obs_label)

from matplotlib.lines import Line2D
legend_handles = [
    Line2D([0], [0], color="white",   linewidth=2.5, linestyle="--", label=obs_label),
    Line2D([0], [0], color="#FFF176", linewidth=1.5, label="10% probabilitat"),
    Line2D([0], [0], color="#FF6D00", linewidth=2.0, label="50% probabilitat"),
    Line2D([0], [0], color="#B71C1C", linewidth=2.5, label="90% probabilitat"),
]
ax_prob.legend(handles=legend_handles, loc="upper right", fontsize=9, framealpha=0.9)

plt.tight_layout()
plt.savefig("farsite_v6_probability.png", dpi=150, bbox_inches="tight")
plt.show()
print("Saved: farsite_v6_probability.png")
