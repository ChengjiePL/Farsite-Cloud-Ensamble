#!/usr/bin/env python3
"""
Generate a single perturbed FARSITE .input file for a given run number.

Called by run_farsite.sh inside the container — replaces the S3 input download.
Reproduces exactly the same parameter sequence as generate_ensemble.py v4.

Usage:
    python3 generate_run.py <run_id> <template_input> <output_input>
    python3 generate_run.py run_042 /data/input/case_1_extended.input /data/input/run_042.input
"""

import sys
import numpy as np

# Must match generate_ensemble.py exactly
RNG_SEED       = 42
BASE_SEED      = 253114
DIR_SIGMA      = 20.0
SPEED_SIGMA    = 0.20
NW_AMP         = 3.5
NW_MIN_DIR     = 270
NW_MAX_DIR     = 360
MOISTURE_SIGMA = 0.25
MOISTURE_MIN   = {1: 2, 10: 4, 100: 6}
MIN_SPEED      = 1


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
                  spotting_seed, direction_offset, speed_multiplier,
                  nw_amp_multiplier, moisture_multiplier):
    lines = []
    for line in header_lines:
        lines.append(f"SPOTTING_SEED: {spotting_seed}" if line.startswith("SPOTTING_SEED:") else line)

    for row in fuel_rows:
        m1h   = max(MOISTURE_MIN[1],   round(row[1] * moisture_multiplier))
        m10h  = max(MOISTURE_MIN[10],  round(row[2] * moisture_multiplier))
        m100h = max(MOISTURE_MIN[100], round(row[3] * moisture_multiplier))
        lines.append(f"{row[0]} {m1h} {m10h} {m100h} {row[4]} {row[5]}")

    lines.extend(mid_lines)

    for row in wind_rows:
        new_dir = int((row["direction"] + direction_offset) % 360)
        amp = nw_amp_multiplier if NW_MIN_DIR <= row["direction"] < NW_MAX_DIR else speed_multiplier
        new_speed = max(MIN_SPEED, round(row["speed"] * amp))
        lines.append(f"{row['month']} {row['day']} {row['time']} {new_speed} {new_dir} {row['cloud']}")

    lines.extend(post_wind)
    return "\n".join(lines)


def sample_params(run_num):
    """Advance RNG to run_num — produces identical sequence to generate_ensemble.py."""
    rng = np.random.default_rng(RNG_SEED)
    for _ in range(run_num - 1):
        rng.normal(0, DIR_SIGMA)
        rng.lognormal(0, SPEED_SIGMA)
        rng.lognormal(np.log(NW_AMP), SPEED_SIGMA)
        rng.lognormal(0, MOISTURE_SIGMA)

    return (
        rng.normal(0, DIR_SIGMA),
        rng.lognormal(0, SPEED_SIGMA),
        rng.lognormal(np.log(NW_AMP), SPEED_SIGMA),
        rng.lognormal(0, MOISTURE_SIGMA),
        BASE_SEED + run_num,
    )


def main():
    run_id        = sys.argv[1]   # e.g. run_042
    template_path = sys.argv[2]   # e.g. /data/input/case_1_extended.input
    output_path   = sys.argv[3]   # e.g. /data/input/run_042.input

    run_num = int(run_id.split("_")[1])
    direction_offset, speed_multiplier, nw_amp_multiplier, moisture_multiplier, spotting_seed = \
        sample_params(run_num)

    header_lines, fuel_rows, mid_lines, wind_rows, post_wind = parse_input_file(template_path)
    content = build_content(header_lines, fuel_rows, mid_lines, wind_rows, post_wind,
                            spotting_seed, direction_offset, speed_multiplier,
                            nw_amp_multiplier, moisture_multiplier)

    with open(output_path, "w") as f:
        f.write(content)

    print(f"[generate_run] {run_id}: dir={direction_offset:+.1f}° spd=x{speed_multiplier:.2f} "
          f"nw_amp=x{nw_amp_multiplier:.2f} moist=x{moisture_multiplier:.2f}")


if __name__ == "__main__":
    main()
