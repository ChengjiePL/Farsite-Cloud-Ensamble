#!/usr/bin/env python3
"""
Layer 2: Parameter Sampling — Monte Carlo Multi-Variable Ensemble v7

Generates N_RUNS FARSITE input files with perturbations across:
  - Wind direction  : Normal(0°, DIR_SIGMA) — independent offset per wind record
  - Wind speed      : LogNormal(0, SPEED_SIGMA) — independent multiplier per wind record
  - Dead fuel moisture (1h, 10h, 100h): LogNormal(×1, MOISTURE_SIGMA) — one value per run

Key change vs v6:
  Per-record perturbation: each of the N hourly wind records gets its own independent
  direction offset and speed multiplier drawn from the same distributions.
  This produces genuinely diverse meteorological scenarios instead of identical-shifted
  wind profiles. Uses per-run seed np.random.default_rng([RNG_SEED, run_num]) for
  reproducibility without sequential RNG advancement.

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
BASE_INPUT   = "tests/case_7_extended.input"
ENSEMBLE_DIR = "tests/ensemble"   # lives inside tests/ so Docker mount works
N_RUNS       = 10000
BASE_SEED    = 253114             # original SPOTTING_SEED from template
RNG_SEED     = 42                 # reproducibility of ensemble generation

# Wind perturbation parameters (v7 — per-record)
DIR_SIGMA    = 20.0   # degrees, normal distribution — applied independently per wind record
SPEED_SIGMA  = 0.20   # log-normal sigma — applied independently per wind record

# Fuel moisture perturbation (one value per run, correlated across fuel models)
MOISTURE_SIGMA  = 0.25
MOISTURE_MIN    = {1: 2, 10: 4, 100: 6}

MIN_SPEED    = 1      # mph floor

# Fixed FARSITE assets (relative to /data/input Docker mount point = tests/)
LCP_PATH     = "/data/input/CASE_7.lcp"
IGN_PATH     = "/data/input/Case7_ignition.shp"

# RNG configuration (v7)
# Each run uses np.random.default_rng([RNG_SEED, run_num]) — no sequential advancement needed


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
                        spotting_seed, direction_offsets, speed_multipliers,
                        moisture_multiplier):
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

    # Perturbed wind rows — independent perturbation per record
    for i, row in enumerate(wind_rows):
        new_dir   = int((row["direction"] + direction_offsets[i]) % 360)
        new_speed = max(MIN_SPEED, round(row["speed"] * speed_multipliers[i]))
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
    os.makedirs(ENSEMBLE_DIR, exist_ok=True)

    header_lines, fuel_rows, mid_lines, wind_rows, post_wind = parse_input_file(BASE_INPUT)
    n_wind = len(wind_rows)

    params = []

    for i in range(1, N_RUNS + 1):
        run_id  = f"run_{i:03d}"
        run_dir = os.path.join(ENSEMBLE_DIR, run_id)
        os.makedirs(run_dir, exist_ok=True)

        # Per-run seed — reproducible without sequential RNG advancement
        rng = np.random.default_rng([RNG_SEED, i])

        # Per-record perturbations: each wind record gets independent samples
        direction_offsets   = rng.normal(0, DIR_SIGMA, size=n_wind)
        speed_multipliers   = rng.lognormal(mean=0, sigma=SPEED_SIGMA, size=n_wind)
        # Moisture: one value per run (correlated across fuel models — physically consistent)
        moisture_multiplier = rng.lognormal(mean=0, sigma=MOISTURE_SIGMA)
        spotting_seed       = BASE_SEED + i

        # Write .input file
        input_content = build_input_content(
            header_lines, fuel_rows, mid_lines, wind_rows, post_wind,
            spotting_seed, direction_offsets, speed_multipliers,
            moisture_multiplier,
        )
        input_path = os.path.join(run_dir, f"{run_id}.input")
        with open(input_path, "w") as f:
            f.write(input_content)

        # Write Docker command file
        docker_path = os.path.join(run_dir, f"{run_id}_docker.txt")
        write_docker_cmd(docker_path, run_id)

        params.append({
            "run_id":               run_id,
            "dir_offset_mean_deg":  round(float(direction_offsets.mean()), 4),
            "speed_mult_mean":      round(float(speed_multipliers.mean()), 4),
            "moisture_multiplier":  round(moisture_multiplier, 4),
            "spotting_seed":        spotting_seed,
        })

        if i % 100 == 0:
            print(f"  Generated {i}/{N_RUNS}")

    # Traceability CSV
    csv_path = os.path.join(ENSEMBLE_DIR, "ensemble_params.csv")
    fieldnames = ["run_id", "dir_offset_mean_deg", "speed_mult_mean",
                  "moisture_multiplier", "spotting_seed"]
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(params)

    print(f"\nDone. {N_RUNS} runs written to {ENSEMBLE_DIR}/")
    print(f"Traceability log: {csv_path}")


if __name__ == "__main__":
    main()
