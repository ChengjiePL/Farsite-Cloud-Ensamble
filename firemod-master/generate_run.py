#!/usr/bin/env python3
"""
Generate a single perturbed FARSITE .input file for a given run number.

Called by run_farsite.sh inside the container — replaces the S3 input download.
Reproduces exactly the same parameter sequence as generate_ensemble.py v7.

Per-record perturbation: each wind record gets independent direction and speed samples.
Uses per-run seed np.random.default_rng([RNG_SEED, run_num]) — no sequential advancement.

Usage:
    python3 generate_run.py <run_id> <template_input> <output_input>
    python3 generate_run.py run_042 /data/input/case_1_extended.input /data/input/run_042.input
"""

import sys
import numpy as np

# Must match generate_ensemble.py exactly — v8
RNG_SEED        = 42
BASE_SEED       = 253114
DIR_SIGMA       = 40.0   # increased from 20° — wider directional spread
SPEED_SIGMA     = 0.40   # increased from 0.20 — wider speed spread
MOISTURE_SIGMA  = 0.0    # disabled — moisture not perturbed
MOISTURE_MIN    = {1: 2, 10: 4, 100: 6}
MIN_SPEED       = 1


def parse_input_file(path):
    with open(path) as f:
        lines = [l.rstrip("\n") for l in f]

    fuel_start, fuel_count = None, 0
    wind_start, wind_count = None, 0
    for i, line in enumerate(lines):
        if line.startswith("FUEL_MOISTURES_DATA:"):
            fuel_start = i
            fuel_count = int(line.split(":")[1].strip())
        if line.startswith("WIND_DATA:"):
            wind_start = i
            wind_count = int(line.split(":")[1].strip())

    header_lines = lines[:fuel_start + 1]
    raw_fuel     = lines[fuel_start + 1: fuel_start + 1 + fuel_count]
    mid_lines    = lines[fuel_start + 1 + fuel_count: wind_start + 1]
    raw_wind     = lines[wind_start + 1: wind_start + 1 + wind_count]
    post_wind    = lines[wind_start + 1 + wind_count:]

    fuel_rows = [[int(x) for x in l.split()] for l in raw_fuel]
    wind_rows = []
    for l in raw_wind:
        p = l.split()
        wind_rows.append({"month": p[0], "day": p[1], "time": p[2],
                          "speed": int(p[3]), "direction": int(p[4]), "cloud": p[5]})

    return header_lines, fuel_rows, mid_lines, wind_rows, post_wind


def build_content(header_lines, fuel_rows, mid_lines, wind_rows, post_wind,
                  spotting_seed, direction_offsets, speed_multipliers, moisture_multiplier):
    lines = []
    for line in header_lines:
        lines.append(f"SPOTTING_SEED: {spotting_seed}" if line.startswith("SPOTTING_SEED:") else line)

    for row in fuel_rows:
        m1h   = max(MOISTURE_MIN[1],   round(row[1] * moisture_multiplier))
        m10h  = max(MOISTURE_MIN[10],  round(row[2] * moisture_multiplier))
        m100h = max(MOISTURE_MIN[100], round(row[3] * moisture_multiplier))
        lines.append(f"{row[0]} {m1h} {m10h} {m100h} {row[4]} {row[5]}")

    lines.extend(mid_lines)

    for i, row in enumerate(wind_rows):
        new_dir   = int((row["direction"] + direction_offsets[i]) % 360)
        new_speed = max(MIN_SPEED, round(row["speed"] * speed_multipliers[i]))
        lines.append(f"{row['month']} {row['day']} {row['time']} {new_speed} {new_dir} {row['cloud']}")

    lines.extend(post_wind)
    return "\n".join(lines)


def generate_params(run_num, n_wind_records):
    """Per-run seed — v8: wind-only perturbation, moisture disabled."""
    rng = np.random.default_rng([RNG_SEED, run_num])
    direction_offsets   = rng.normal(0, DIR_SIGMA, size=n_wind_records)
    speed_multipliers   = rng.lognormal(mean=0, sigma=SPEED_SIGMA, size=n_wind_records)
    moisture_multiplier = 1.0  # no perturbation
    return direction_offsets, speed_multipliers, moisture_multiplier, BASE_SEED + run_num


def main():
    run_id        = sys.argv[1]   # e.g. run_042
    template_path = sys.argv[2]   # e.g. /data/input/case_1_extended.input
    output_path   = sys.argv[3]   # e.g. /data/input/run_042.input

    run_num = int(run_id.split("_")[1])

    header_lines, fuel_rows, mid_lines, wind_rows, post_wind = parse_input_file(template_path)

    direction_offsets, speed_multipliers, moisture_multiplier, spotting_seed = \
        generate_params(run_num, len(wind_rows))

    content = build_content(header_lines, fuel_rows, mid_lines, wind_rows, post_wind,
                            spotting_seed, direction_offsets, speed_multipliers,
                            moisture_multiplier)

    with open(output_path, "w") as f:
        f.write(content)

    print(f"[generate_run] {run_id}: dir_mean={direction_offsets.mean():+.1f}° "
          f"spd_mean=x{speed_multipliers.mean():.2f} moist=x{moisture_multiplier:.2f}")


if __name__ == "__main__":
    main()
