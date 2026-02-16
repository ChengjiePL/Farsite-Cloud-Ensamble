import numpy as np
import matplotlib.pyplot as plt
import shapefile
import os

output_dir = "tests/output"

# --- Load arrival time grid (extended simulation) ---
arrival = np.loadtxt(os.path.join(output_dir, "Case_1_ext_ArrivalTime.asc"), skiprows=6)

with open(os.path.join(output_dir, "Case_1_ext_ArrivalTime.asc")) as f:
    ncols = int(f.readline().split()[1])
    nrows = int(f.readline().split()[1])
    xll = float(f.readline().split()[1])
    yll = float(f.readline().split()[1])
    cellsize = float(f.readline().split()[1])

xur = xll + ncols * cellsize
yur = yll + nrows * cellsize

arrival[arrival == -9999.0] = np.nan

# --- Load simulated perimeters ---
sf_sim = shapefile.Reader("tests/output/Case_1_ext_Perimeters")
sim_shapes = sf_sim.shapes()
sim_records = sf_sim.records()

# --- Observed perimeters ---
observed = [
    ("tests/Per1_02092013", "Observed Sept 2 (ignition)", "red"),
    ("tests/Per2_03092013", "Observed Sept 3", "#00C853"),
    ("tests/Per3_04092013", "Observed Sept 4", "#00BFA5"),
    ("tests/Per4_06092013", "Observed Sept 6 (final)", "#006064"),
]

# --- Figure ---
fig, ax = plt.subplots(figsize=(14, 10))

# Background
background = np.ones_like(arrival) * 0.95
ax.imshow(background, extent=[xll, xur, yll, yur], cmap="gray", vmin=0, vmax=1)

# Simulated fire spread
cmap = plt.cm.YlOrRd.copy()
im = ax.imshow(arrival, extent=[xll, xur, yll, yur], cmap=cmap, interpolation="nearest", alpha=0.85)
cbar = fig.colorbar(im, ax=ax, shrink=0.6, pad=0.02)
cbar.set_label("Simulated Arrival Time (minutes from ignition)", fontsize=11)

# Simulated perimeters
for i, (shape, rec) in enumerate(zip(sim_shapes, sim_records)):
    pts = np.array(shape.points)
    elapsed = rec["Elapsed_Mi"]
    hours = int(elapsed / 60)
    label = f"Simulated {hours}h" if i < 5 else None
    ax.plot(pts[:, 0], pts[:, 1], color="#1E88E5", linewidth=1.5, linestyle="--", alpha=0.6, label=label)

# Last simulated perimeter
last_pts = np.array(sim_shapes[-1].points)
ax.plot(last_pts[:, 0], last_pts[:, 1], color="#0D47A1", linewidth=2.5, linestyle="--", label="Simulated final perimeter")

# Observed perimeters
for filepath, label, color in observed:
    sf = shapefile.Reader(filepath)
    s = sf.shapes()[0]
    pts = np.array(s.points)
    if label.endswith("(ignition)"):
        ax.fill(pts[:, 0], pts[:, 1], color="red", alpha=0.3)
        ax.plot(pts[:, 0], pts[:, 1], color="red", linewidth=2.5, label=label)
    else:
        lw = 3 if "final" in label else 2
        ax.plot(pts[:, 0], pts[:, 1], color=color, linewidth=lw, linestyle="-", label=label)

# Zoom
ax.set_xlim(2824500, 2834000)
ax.set_ylim(2148500, 2162000)

ax.set_title(
    "FARSITE Case 1: Simulated vs Observed Fire Spread\n"
    "Simulation: Sept 2-6, 2013 | Blue dashed = simulated | Green solid = observed",
    fontsize=14, fontweight="bold"
)
ax.set_xlabel("Easting (m)")
ax.set_ylabel("Northing (m)")
ax.legend(loc="upper right", fontsize=9, framealpha=0.9)

plt.tight_layout()
plt.savefig("farsite_v3_vs_observed.png", dpi=150, bbox_inches="tight")
plt.show()
print("Saved: farsite_v3_vs_observed.png")
