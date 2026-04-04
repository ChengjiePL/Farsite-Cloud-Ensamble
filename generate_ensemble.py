#!/usr/bin/env python3
"""
Layer 2: Parameter Sampling — Monte Carlo Multi-Variable Ensemble v4

Generates N_RUNS FARSITE input files with perturbations across:
  - Wind direction  : Normal(0°, DIR_SIGMA) — one offset per run
  - Wind speed      : direction-dependent amplification:
      * NW sector (270-360°): LogNormal(mean=ln(NW_AMP), SPEED_SIGMA)
        models topographic channeling that amplified NW winds in the real fire
      * Other directions: LogNormal(mean=0, SPEED_SIGMA)
  - Dead fuel moisture (1h, 10h, 100h): LogNormal(×1, MOISTURE_SIGMA)

Justification for NW amplification:
  Wind data analysis shows NW winds (270-360°) dominated Sept 3-6 evenings —
  exactly the period the real fire expanded SE. Station measurements (2-8 mph)
  underestimate local wind due to topographic channeling. Amplification factor
  NW_AMP=2.0 models this unobserved enhancement.

Output layout (inside tests/ensemble/):
    run_001/run_001.input
    ensemble_params.csv

Usage:
    .venv/bin/python3 generate_ensemble.py
"""

import os
import csv
import numpy as np

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
BASE_INPUT   = "tests/case_1_extended.input"
ENSEMBLE_DIR = "tests/ensemble"   # lives inside tests/ so Docker mount works
N_RUNS       = 10000
BASE_SEED    = 253114             # original SPOTTING_SEED from template
RNG_SEED     = 42                 # reproducibility of ensemble generation

# Wind perturbation parameters (v4)
DIR_SIGMA    = 20.0   # degrees, normal distribution
SPEED_SIGMA  = 0.20   # log-normal sigma (base variability for all directions)

# NW topographic amplification (v4: new)
# NW sector = 270-360° — these records drive SE fire spread
# Station underestimates local wind due to topographic channeling
NW_AMP       = 3.5    # mean amplification factor for NW winds (log-normal mean)
NW_MIN_DIR   = 270    # NW sector start (degrees)
NW_MAX_DIR   = 360    # NW sector end (degrees)

# Fuel moisture perturbation
MOISTURE_SIGMA = 0.25
MOISTURE_MIN   = {1: 2, 10: 4, 100: 6}

MIN_SPEED    = 1      # mph floor

# Fixed FARSITE assets (relative to /data/input Docker mount point = tests/)
LCP_PATH     = "/data/input/CASE_1.lcp"
IGN_PATH     = "/data/input/Per1_02092013.shp"


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------
def parse_input_file(path):
    """
    Returns:
        header_lines  -- all lines before FUEL_MOISTURES_DATA block
        fuel_rows     -- list of lists of ints per fuel model row
        mid_lines     -- lines between fuel moisture block and WIND_DATA header
        wind_rows     -- list of dicts: month, day, time, speed, direction, cloud
        post_wind     -- lines after the wind data block
    """
    with open(path, "r") as f:
        lines = [line.rstrip("\n") for line in f.readlines()]

    # Find FUEL_MOISTURES_DATA block
    fuel_start = None
    fuel_count = 0
    for i, line in enumerate(lines):
        if line.startswith("FUEL_MOISTURES_DATA:"):
            fuel_start = i
            fuel_count = int(line.split(":")[1].strip())
            break

    if fuel_start is None:
        raise ValueError("FUEL_MOISTURES_DATA block not found")

    # Find WIND_DATA block
    wind_start = None
    wind_count = 0
    for i, line in enumerate(lines):
        if line.startswith("WIND_DATA:"):
            wind_start = i
            wind_count = int(line.split(":")[1].strip())
            break

    if wind_start is None:
        raise ValueError("WIND_DATA block not found")

    header_lines = lines[: fuel_start + 1]          # up to and including FUEL_MOISTURES_DATA: N
    raw_fuel     = lines[fuel_start + 1 : fuel_start + 1 + fuel_count]
    mid_lines    = lines[fuel_start + 1 + fuel_count : wind_start + 1]  # includes WIND_DATA header
    raw_wind     = lines[wind_start + 1 : wind_start + 1 + wind_count]
    post_wind    = lines[wind_start + 1 + wind_count :]

    fuel_rows = []
    for line in raw_fuel:
        fuel_rows.append([int(x) for x in line.split()])

    wind_rows = []
    for line in raw_wind:
        parts = line.split()
        wind_rows.append({
            "month":     parts[0],
            "day":       parts[1],
            "time":      parts[2],
            "speed":     int(parts[3]),
            "direction": int(parts[4]),
            "cloud":     parts[5],
        })

    return header_lines, fuel_rows, mid_lines, wind_rows, post_wind


# ---------------------------------------------------------------------------
# Writing
# ---------------------------------------------------------------------------
def build_input_content(header_lines, fuel_rows, mid_lines, wind_rows, post_wind,
                        spotting_seed, direction_offset, speed_multiplier,
                        nw_amp_multiplier, moisture_multiplier):
    lines = []

    # Header — swap SPOTTING_SEED for the run-specific value
    for line in header_lines:
        if line.startswith("SPOTTING_SEED:"):
            lines.append(f"SPOTTING_SEED: {spotting_seed}")
        else:
            lines.append(line)

    # Perturbed fuel moisture rows
    for row in fuel_rows:
        fuel_model = row[0]
        m1h   = max(MOISTURE_MIN[1],   round(row[1] * moisture_multiplier))
        m10h  = max(MOISTURE_MIN[10],  round(row[2] * moisture_multiplier))
        m100h = max(MOISTURE_MIN[100], round(row[3] * moisture_multiplier))
        lines.append(f"{fuel_model} {m1h} {m10h} {m100h} {row[4]} {row[5]}")

    # Mid section (unchanged) + WIND_DATA header
    lines.extend(mid_lines)

    # Perturbed wind rows — direction-dependent speed amplification
    for row in wind_rows:
        new_dir = int((row["direction"] + direction_offset) % 360)
        # Apply NW topographic amplification when original direction is in NW sector
        if NW_MIN_DIR <= row["direction"] < NW_MAX_DIR:
            effective_multiplier = speed_multiplier * nw_amp_multiplier
        else:
            effective_multiplier = speed_multiplier
        new_speed = max(MIN_SPEED, round(row["speed"] * effective_multiplier))
        lines.append(
            f"{row['month']} {row['day']} {row['time']} "
            f"{new_speed} {new_dir} {row['cloud']}"
        )

    # Footer (unchanged)
    lines.extend(post_wind)

    return "\n".join(lines)


def write_docker_cmd(path, run_id):
    input_docker = f"/data/input/ensemble/{run_id}/{run_id}.input"
    output_prefix = f"/data/output/{run_id}"
    cmd = f"{LCP_PATH} {input_docker} {IGN_PATH} 0 {output_prefix} 0\n"
    with open(path, "w") as f:
        f.write(cmd)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    rng = np.random.default_rng(RNG_SEED)

    os.makedirs(ENSEMBLE_DIR, exist_ok=True)

    header_lines, fuel_rows, mid_lines, wind_rows, post_wind = parse_input_file(BASE_INPUT)

    params = []

    for i in range(1, N_RUNS + 1):
        run_id  = f"run_{i:03d}"
        run_dir = os.path.join(ENSEMBLE_DIR, run_id)
        os.makedirs(run_dir, exist_ok=True)

        # Sample perturbations — one value per run (coherent across all rows)
        direction_offset    = rng.normal(0, DIR_SIGMA)
        speed_multiplier    = rng.lognormal(mean=0, sigma=SPEED_SIGMA)
        # NW amplification: LogNormal centered on NW_AMP (e.g. mean=2.0)
        nw_amp_multiplier   = rng.lognormal(mean=np.log(NW_AMP), sigma=SPEED_SIGMA)
        moisture_multiplier = rng.lognormal(mean=0, sigma=MOISTURE_SIGMA)
        spotting_seed       = BASE_SEED + i

        # Write .input file
        input_content = build_input_content(
            header_lines, fuel_rows, mid_lines, wind_rows, post_wind,
            spotting_seed, direction_offset, speed_multiplier,
            nw_amp_multiplier, moisture_multiplier,
        )
        input_path = os.path.join(run_dir, f"{run_id}.input")
        with open(input_path, "w") as f:
            f.write(input_content)

        # Write Docker command file
        docker_path = os.path.join(run_dir, f"{run_id}_docker.txt")
        write_docker_cmd(docker_path, run_id)

        params.append({
            "run_id":                 run_id,
            "direction_offset_deg":   round(direction_offset, 4),
            "speed_multiplier":       round(speed_multiplier, 4),
            "nw_amp_multiplier":      round(nw_amp_multiplier, 4),
            "moisture_multiplier":    round(moisture_multiplier, 4),
            "spotting_seed":          spotting_seed,
        })

        if i % 100 == 0:
            print(f"  Generated {i}/{N_RUNS}")

    # Traceability CSV
    csv_path = os.path.join(ENSEMBLE_DIR, "ensemble_params.csv")
    fieldnames = ["run_id", "direction_offset_deg", "speed_multiplier",
                  "nw_amp_multiplier", "moisture_multiplier", "spotting_seed"]
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(params)

    print(f"\nDone. {N_RUNS} runs written to {ENSEMBLE_DIR}/")
    print(f"Traceability log: {csv_path}")


if __name__ == "__main__":
    main()
