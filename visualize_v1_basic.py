import numpy as np
import matplotlib.pyplot as plt
import os

output_dir = "tests/output"

grids = {
    "Arrival Time (min)": "Case_1_ArrivalTime.asc",
    "Flame Length (m)": "Case_1_FlameLength.asc",
    "Fireline Intensity": "Case_1_Intensity.asc",
    "Spread Rate": "Case_1_SpreadRate.asc",
}

fig, axes = plt.subplots(2, 2, figsize=(14, 10))
fig.suptitle("FARSITE Case 1 - Simulation Outputs", fontsize=16, fontweight="bold")

for ax, (title, filename) in zip(axes.flat, grids.items()):
    path = os.path.join(output_dir, filename)
    data = np.loadtxt(path, skiprows=6)
    data[data == -9999.0] = np.nan

    im = ax.imshow(data, cmap="inferno", interpolation="nearest")
    ax.set_title(title)
    ax.axis("off")
    fig.colorbar(im, ax=ax, shrink=0.8)

plt.tight_layout()
plt.savefig("farsite_v1_basic_grids.png", dpi=150, bbox_inches="tight")
plt.show()
print("Saved: farsite_v1_basic_grids.png")
