import numpy as np
import matplotlib.pyplot as plt
import shapefile
import os

output_dir = "tests/output"

# --- Load arrival time grid (2h simulation) ---
arrival = np.loadtxt(os.path.join(output_dir, "Case_1_ArrivalTime.asc"), skiprows=6)

with open(os.path.join(output_dir, "Case_1_ArrivalTime.asc")) as f:
    ncols = int(f.readline().split()[1])
    nrows = int(f.readline().split()[1])
    xll = float(f.readline().split()[1])
    yll = float(f.readline().split()[1])
    cellsize = float(f.readline().split()[1])

xur = xll + ncols * cellsize
yur = yll + nrows * cellsize

arrival[arrival == -9999.0] = np.nan
burned = ~np.isnan(arrival)

# --- Load simulated perimeters ---
sf_sim = shapefile.Reader("tests/output/Case_1_Perimeters")
sim_shapes = sf_sim.shapes()

# --- Load ignition ---
sf_ign = shapefile.Reader("tests/Per1_02092013")
ign_shape = sf_ign.shapes()[0]

# --- Figure: single clear map ---
fig, ax = plt.subplots(figsize=(12, 9))

# Background
background = np.ones_like(arrival) * 0.95
ax.imshow(background, extent=[xll, xur, yll, yur], cmap="gray", vmin=0, vmax=1)

# Arrival time heatmap
cmap = plt.cm.YlOrRd.copy()
im = ax.imshow(arrival, extent=[xll, xur, yll, yur], cmap=cmap, interpolation="nearest", alpha=0.9)
cbar = fig.colorbar(im, ax=ax, shrink=0.7, pad=0.02)
cbar.set_label("Arrival Time (minutes from ignition)", fontsize=11)

# Simulated perimeters
colors = ["#2196F3", "#1565C0", "#0D47A1"]
labels = ["Perimeter t=60min", "Perimeter t=120min", "Final perimeter"]
for i, shape in enumerate(sim_shapes):
    pts = np.array(shape.points)
    color = colors[i] if i < len(colors) else colors[-1]
    label = labels[i] if i < len(labels) else None
    ax.plot(pts[:, 0], pts[:, 1], color=color, linewidth=1.5, linestyle="--", label=label)

# Ignition perimeter
ign_pts = np.array(ign_shape.points)
ax.fill(ign_pts[:, 0], ign_pts[:, 1], color="red", alpha=0.4, label="Ignition area")
ax.plot(ign_pts[:, 0], ign_pts[:, 1], color="red", linewidth=2)

# Zoom to fire area
pad = 500
fire_rows, fire_cols = np.where(burned)
if len(fire_rows) > 0:
    y_min = yur - (fire_rows.max() + 1) * cellsize - pad
    y_max = yur - fire_rows.min() * cellsize + pad
    x_min = xll + fire_cols.min() * cellsize - pad
    x_max = xll + (fire_cols.max() + 1) * cellsize + pad
    ax.set_xlim(x_min, x_max)
    ax.set_ylim(y_min, y_max)

ax.set_title("FARSITE Case 1 - Fire Spread Simulation\n(2h simulation, Sept 3, 13:38-15:38)", fontsize=14, fontweight="bold")
ax.set_xlabel("Easting (m)")
ax.set_ylabel("Northing (m)")
ax.legend(loc="upper right", fontsize=10)

plt.tight_layout()
plt.savefig("farsite_v2_2h_perimeters.png", dpi=150, bbox_inches="tight")
plt.show()
print("Saved: farsite_v2_2h_perimeters.png")
