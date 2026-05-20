#!/usr/bin/env python3
"""
Generate a perturbed FARSITE ignition perimeter shapefile for one ensemble run.

Perturbation model — homothety (uniform scaling) about the perimeter centroid:

    v' = C + (v - C) * (1 + f),   f ~ Normal(0, IGN_SIGMA)

The ignition perimeter is an observed fire front at t0 and carries delineation
and timing uncertainty. A fixed absolute buffer does not scale: +/-2 m is huge
for a 5 m perimeter and negligible for a 1 km one. Scaling about the centroid
makes the perturbation proportional by construction — the same RELATIVE size
change is applied regardless of the fire's size, matching the multiplicative
treatment already used for wind speed.

The ignition RNG uses a distinct sub-stream key (IGN_STREAM) so adding this
perturbation does not shift the wind/weather draws of pre-existing runs.

Usage:
    python3 generate_ignition.py <run_id> <template_shp> <output_shp>
"""

import os
import sys
import shutil
import numpy as np
import shapefile  # pyshp

RNG_SEED   = 42      # must match generate_run.py / generate_ensemble.py
IGN_SIGMA  = 0.15    # std-dev of the homothety factor (15% relative)
IGN_STREAM = 7       # distinct RNG sub-stream — keeps wind/weather draws stable
F_CLIP     = 0.40    # clip |f| so the polygon never collapses or explodes

# pyshp polygon shape-type codes (POLYGON / POLYGONZ / POLYGONM)
_POLYGON_TYPES = (5, 15, 25)


def _ring_area_centroid(points):
    """Signed area and area-weighted centroid of a ring (shoelace formula).
    Falls back to the vertex mean for degenerate near-zero-area rings."""
    p = np.asarray(points, dtype=float)
    x, y = p[:, 0], p[:, 1]
    x1, y1 = np.roll(x, -1), np.roll(y, -1)
    cross = x * y1 - x1 * y
    area = cross.sum() / 2.0
    if abs(area) < 1e-9:
        return 0.0, x.mean(), y.mean()
    cx = ((x + x1) * cross).sum() / (6.0 * area)
    cy = ((y + y1) * cross).sum() / (6.0 * area)
    return area, cx, cy


def homothety_factor(run_num):
    """Sample the per-run scaling factor (1 + f), reproducible from run_num."""
    rng = np.random.default_rng([RNG_SEED, run_num, IGN_STREAM])
    f = float(np.clip(rng.normal(0.0, IGN_SIGMA), -F_CLIP, F_CLIP))
    return 1.0 + f, f


def perturb_ignition_shp(run_num, template_shp, output_shp):
    """Read template_shp, scale the perimeter about its centroid, write
    output_shp (+ .shx/.dbf, and .prj if present). Returns (scale, f)."""
    scale, f = homothety_factor(run_num)

    reader = shapefile.Reader(template_shp)
    if reader.shapeType not in _POLYGON_TYPES:
        raise ValueError(
            f"{template_shp}: expected a polygon ignition shapefile, "
            f"got shapeType {reader.shapeType}")

    shp = reader.shape(0)
    parts = list(shp.parts) + [len(shp.points)]

    # centroid taken from the largest-area ring (the outer perimeter)
    best_area, cx, cy = -1.0, 0.0, 0.0
    for k in range(len(parts) - 1):
        ring = shp.points[parts[k]:parts[k + 1]]
        area, gx, gy = _ring_area_centroid(ring)
        if abs(area) > best_area:
            best_area, cx, cy = abs(area), gx, gy

    pts = np.asarray(shp.points, dtype=float)
    pts[:, 0] = cx + (pts[:, 0] - cx) * scale
    pts[:, 1] = cy + (pts[:, 1] - cy) * scale

    rings = [[list(xy) for xy in pts[parts[k]:parts[k + 1]]]
             for k in range(len(parts) - 1)]

    out_base = output_shp[:-4] if output_shp.lower().endswith(".shp") else output_shp
    writer = shapefile.Writer(out_base, shapeType=reader.shapeType)
    writer.autoBalance = 1
    for field in reader.fields[1:]:        # skip the DeletionFlag pseudo-field
        writer.field(*field)
    writer.poly(rings)
    writer.record(*reader.record(0))
    writer.close()
    reader.close()

    prj_src = template_shp[:-4] + ".prj"
    if os.path.exists(prj_src):
        shutil.copy(prj_src, out_base + ".prj")

    return scale, f


def main():
    if len(sys.argv) != 4:
        sys.exit("Usage: generate_ignition.py <run_id> <template_shp> <output_shp>")
    run_id, template_shp, output_shp = sys.argv[1], sys.argv[2], sys.argv[3]
    run_num = int(run_id.split("_")[1])
    scale, f = perturb_ignition_shp(run_num, template_shp, output_shp)
    print(f"[generate_ignition] {run_id}: scale=x{scale:.3f} (f={f:+.3f})")


if __name__ == "__main__":
    main()
