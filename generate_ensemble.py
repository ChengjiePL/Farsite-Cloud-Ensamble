#!/usr/bin/env python3
"""
Layer 2: Parameter Sampling — Monte Carlo Multi-Variable Ensemble v9

Generates N_RUNS FARSITE input files with per-record perturbations across:
  - Wind direction  : Normal(0°, DIR_SIGMA) per WIND_DATA record
  - Wind speed      : LogNormal(0, SPEED_SIGMA) multiplier per WIND_DATA record
  - Temperature     : Normal(0, TEMP_SIGMA) °F additive offset per WEATHER_DATA record
                      (same offset applied to mT and xT to preserve diurnal range)
  - Humidity        : Normal(0, HUM_SIGMA) % additive offset per WEATHER_DATA record
                      (same offset applied to mH and xH, clipped [1, 99])

Fuel moisture: disabled in v9.

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
ENSEMBLE_DIR = "tests/ensemble"
N_RUNS       = 10000
BASE_SEED    = 253114
RNG_SEED     = 42

# Wind perturbation (per WIND_DATA record)
DIR_SIGMA    = 20.0
SPEED_SIGMA  = 0.20
MIN_SPEED    = 1

# Weather perturbation (per WEATHER_DATA record)
TEMP_SIGMA   = 5.0
HUM_SIGMA    = 8.0
HUM_MIN      = 1
HUM_MAX      = 99

# Fuel moisture — disabled, mins still enforced
MOISTURE_MIN = {1: 2, 10: 4, 100: 6}

# Fixed FARSITE assets (Docker mount = tests/)
LCP_PATH     = "/data/input/CASE_7.lcp"
IGN_PATH     = "/data/input/Case7_ignition.shp"


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------
def parse_input_file(path):
    with open(path, "r") as f:
        lines = [line.rstrip("\n") for line in f.readlines()]

    fuel_start = fuel_count = None
    wx_start   = wx_count   = None
    wind_start = wind_count = None
    for i, line in enumerate(lines):
        if line.startswith("FUEL_MOISTURES_DATA:"):
            fuel_start = i
            fuel_count = int(line.split(":")[1].strip())
        elif line.startswith("WEATHER_DATA:"):
            wx_start = i
            wx_count = int(line.split(":")[1].strip())
        elif line.startswith("WIND_DATA:"):
            wind_start = i
            wind_count = int(line.split(":")[1].strip())

    if fuel_start is None or wx_start is None or wind_start is None:
        raise ValueError("Required block (FUEL_MOISTURES_DATA / WEATHER_DATA / WIND_DATA) not found")

    header_lines = lines[: fuel_start + 1]
    raw_fuel     = lines[fuel_start + 1: fuel_start + 1 + fuel_count]
    pre_wx       = lines[fuel_start + 1 + fuel_count: wx_start + 1]
    raw_wx       = lines[wx_start + 1: wx_start + 1 + wx_count]
    pre_wind     = lines[wx_start + 1 + wx_count: wind_start + 1]
    raw_wind     = lines[wind_start + 1: wind_start + 1 + wind_count]
    post_wind    = lines[wind_start + 1 + wind_count:]

    fuel_rows = [[int(x) for x in l.split()] for l in raw_fuel]

    wx_rows = []
    for l in raw_wx:
        p = l.split()
        wx_rows.append({"month": p[0], "day": p[1], "rain": p[2],
                        "mTH": p[3], "xTH": p[4],
                        "mT": int(p[5]), "xT": int(p[6]),
                        "mH": int(p[7]), "xH": int(p[8]),
                        "elev": p[9]})

    wind_rows = []
    for l in raw_wind:
        p = l.split()
        wind_rows.append({"month": p[0], "day": p[1], "time": p[2],
                          "speed": int(p[3]), "direction": int(p[4]), "cloud": p[5]})

    return header_lines, fuel_rows, pre_wx, wx_rows, pre_wind, wind_rows, post_wind


# ---------------------------------------------------------------------------
# Writing
# ---------------------------------------------------------------------------
def build_input_content(header_lines, fuel_rows, pre_wx, wx_rows, pre_wind, wind_rows, post_wind,
                        spotting_seed,
                        temp_offsets, hum_offsets,
                        direction_offsets, speed_multipliers):
    lines = []

    for line in header_lines:
        lines.append(f"SPOTTING_SEED: {spotting_seed}" if line.startswith("SPOTTING_SEED:") else line)

    for row in fuel_rows:
        m1h   = max(MOISTURE_MIN[1],   row[1])
        m10h  = max(MOISTURE_MIN[10],  row[2])
        m100h = max(MOISTURE_MIN[100], row[3])
        lines.append(f"{row[0]} {m1h} {m10h} {m100h} {row[4]} {row[5]}")

    lines.extend(pre_wx)

    for i, row in enumerate(wx_rows):
        new_mT = int(round(row["mT"] + temp_offsets[i]))
        new_xT = int(round(row["xT"] + temp_offsets[i]))
        new_mH = int(np.clip(round(row["mH"] + hum_offsets[i]), HUM_MIN, HUM_MAX))
        new_xH = int(np.clip(round(row["xH"] + hum_offsets[i]), HUM_MIN, HUM_MAX))
        if new_xT < new_mT:
            new_xT = new_mT
        if new_xH > new_mH:
            new_xH = new_mH
        lines.append(
            f"{row['month']} {row['day']} {row['rain']} "
            f"{row['mTH']} {row['xTH']} "
            f"{new_mT} {new_xT} {new_mH} {new_xH} {row['elev']}"
        )

    lines.extend(pre_wind)

    for i, row in enumerate(wind_rows):
        new_dir   = int((row["direction"] + direction_offsets[i]) % 360)
        new_speed = max(MIN_SPEED, round(row["speed"] * speed_multipliers[i]))
        lines.append(
            f"{row['month']} {row['day']} {row['time']} "
            f"{new_speed} {new_dir} {row['cloud']}"
        )

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

    header_lines, fuel_rows, pre_wx, wx_rows, pre_wind, wind_rows, post_wind = \
        parse_input_file(BASE_INPUT)
    n_wx   = len(wx_rows)
    n_wind = len(wind_rows)

    params = []

    for i in range(1, N_RUNS + 1):
        run_id  = f"run_{i:03d}"
        run_dir = os.path.join(ENSEMBLE_DIR, run_id)
        os.makedirs(run_dir, exist_ok=True)

        rng = np.random.default_rng([RNG_SEED, i])

        temp_offsets        = rng.normal(0, TEMP_SIGMA,  size=n_wx)
        hum_offsets         = rng.normal(0, HUM_SIGMA,   size=n_wx)
        direction_offsets   = rng.normal(0, DIR_SIGMA,   size=n_wind)
        speed_multipliers   = rng.lognormal(mean=0, sigma=SPEED_SIGMA, size=n_wind)
        spotting_seed       = BASE_SEED + i

        input_content = build_input_content(
            header_lines, fuel_rows, pre_wx, wx_rows, pre_wind, wind_rows, post_wind,
            spotting_seed,
            temp_offsets, hum_offsets,
            direction_offsets, speed_multipliers,
        )
        input_path = os.path.join(run_dir, f"{run_id}.input")
        with open(input_path, "w") as f:
            f.write(input_content)

        docker_path = os.path.join(run_dir, f"{run_id}_docker.txt")
        write_docker_cmd(docker_path, run_id)

        params.append({
            "run_id":              run_id,
            "dir_offset_mean_deg": round(float(direction_offsets.mean()), 4),
            "speed_mult_mean":     round(float(speed_multipliers.mean()), 4),
            "temp_offset_mean_F":  round(float(temp_offsets.mean()), 4),
            "hum_offset_mean_pct": round(float(hum_offsets.mean()), 4),
            "spotting_seed":       spotting_seed,
        })

        if i % 100 == 0:
            print(f"  Generated {i}/{N_RUNS}")

    csv_path = os.path.join(ENSEMBLE_DIR, "ensemble_params.csv")
    fieldnames = ["run_id", "dir_offset_mean_deg", "speed_mult_mean",
                  "temp_offset_mean_F", "hum_offset_mean_pct", "spotting_seed"]
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(params)

    print(f"\nDone. {N_RUNS} runs written to {ENSEMBLE_DIR}/")
    print(f"Traceability log: {csv_path}")


if __name__ == "__main__":
    main()
