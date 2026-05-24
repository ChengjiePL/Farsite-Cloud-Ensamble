#!/usr/bin/env python3
"""
Generate a single perturbed FARSITE .input file for a given run number.

v9 — wind + weather perturbation (fuel moisture disabled).
Per-record perturbation: each WIND_DATA and WEATHER_DATA record gets independent
samples. Uses per-run seed np.random.default_rng([RNG_SEED, run_num]).

Usage:
    python3 generate_run.py <run_id> <template_input> <output_input>
"""

import sys
import numpy as np

# Must match generate_ensemble.py — v9
RNG_SEED        = 42
BASE_SEED       = 253114

# Wind perturbation (per WIND_DATA record)
DIR_SIGMA       = 20.0   # degrees, Normal additive
SPEED_SIGMA     = 0.20   # log-normal sigma, multiplicative
MIN_SPEED       = 1

# Weather perturbation (per WEATHER_DATA record)
TEMP_SIGMA      = 5.0    # °F, Normal additive offset (applied to mT and xT)
HUM_SIGMA       = 8.0    # %, Normal additive offset (applied to mH and xH)
HUM_MIN         = 1      # clip floor
HUM_MAX         = 99     # clip ceiling

# Fuel moisture — disabled
MOISTURE_MIN    = {1: 2, 10: 4, 100: 6}


def parse_input_file(path):
    with open(path) as f:
        lines = [l.rstrip("\n") for l in f]

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

    header_lines = lines[:fuel_start + 1]
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
        # Mo Dy Rain mTH xTH mT xT mH xH Elev
        wx_rows.append({"month": p[0], "day": p[1], "rain": p[2],
                        "mTH": p[3], "xTH": p[4],
                        "mT": int(p[5]),  "xT": int(p[6]),
                        "mH": int(p[7]),  "xH": int(p[8]),
                        "elev": p[9]})

    wind_rows = []
    for l in raw_wind:
        p = l.split()
        wind_rows.append({"month": p[0], "day": p[1], "time": p[2],
                          "speed": int(p[3]), "direction": int(p[4]), "cloud": p[5]})

    return header_lines, fuel_rows, pre_wx, wx_rows, pre_wind, wind_rows, post_wind


def build_content(header_lines, fuel_rows, pre_wx, wx_rows, pre_wind, wind_rows, post_wind,
                  spotting_seed,
                  temp_offsets, hum_offsets,
                  direction_offsets, speed_multipliers):
    lines = []
    for line in header_lines:
        lines.append(f"SPOTTING_SEED: {spotting_seed}" if line.startswith("SPOTTING_SEED:") else line)

    # Fuel moisture — unperturbed (mins still enforced)
    for row in fuel_rows:
        m1h   = max(MOISTURE_MIN[1],   row[1])
        m10h  = max(MOISTURE_MIN[10],  row[2])
        m100h = max(MOISTURE_MIN[100], row[3])
        lines.append(f"{row[0]} {m1h} {m10h} {m100h} {row[4]} {row[5]}")

    # Pre-weather block (RAWS_ELEVATION, RAWS_UNITS, WEATHER_DATA: N header)
    lines.extend(pre_wx)

    # Perturbed weather rows
    for i, row in enumerate(wx_rows):
        new_mT = int(round(row["mT"] + temp_offsets[i]))
        new_xT = int(round(row["xT"] + temp_offsets[i]))
        new_mH = int(np.clip(round(row["mH"] + hum_offsets[i]), HUM_MIN, HUM_MAX))
        new_xH = int(np.clip(round(row["xH"] + hum_offsets[i]), HUM_MIN, HUM_MAX))
        # Preserve mT < xT and xH < mH ordering
        if new_xT < new_mT:
            new_xT = new_mT
        if new_xH > new_mH:
            new_xH = new_mH
        lines.append(
            f"{row['month']} {row['day']} {row['rain']} "
            f"{row['mTH']} {row['xTH']} "
            f"{new_mT} {new_xT} {new_mH} {new_xH} {row['elev']}"
        )

    # Pre-wind (blank line + WIND_DATA: N header)
    lines.extend(pre_wind)

    # Perturbed wind rows
    for i, row in enumerate(wind_rows):
        new_dir   = int((row["direction"] + direction_offsets[i]) % 360)
        new_speed = max(MIN_SPEED, round(row["speed"] * speed_multipliers[i]))
        lines.append(f"{row['month']} {row['day']} {row['time']} {new_speed} {new_dir} {row['cloud']}")

    lines.extend(post_wind)
    return "\n".join(lines)


def generate_params(run_num, n_wx_records, n_wind_records):
    """v9: wind + weather perturbation per-record."""
    rng = np.random.default_rng([RNG_SEED, run_num])
    temp_offsets        = rng.normal(0, TEMP_SIGMA,  size=n_wx_records)
    hum_offsets         = rng.normal(0, HUM_SIGMA,   size=n_wx_records)
    direction_offsets   = rng.normal(0, DIR_SIGMA,   size=n_wind_records)
    speed_multipliers   = rng.lognormal(mean=0, sigma=SPEED_SIGMA, size=n_wind_records)
    return temp_offsets, hum_offsets, direction_offsets, speed_multipliers, BASE_SEED + run_num


def main():
    run_id        = sys.argv[1]
    template_path = sys.argv[2]
    output_path   = sys.argv[3]

    run_num = int(run_id.split("_")[1])

    header_lines, fuel_rows, pre_wx, wx_rows, pre_wind, wind_rows, post_wind = \
        parse_input_file(template_path)

    temp_offsets, hum_offsets, direction_offsets, speed_multipliers, spotting_seed = \
        generate_params(run_num, len(wx_rows), len(wind_rows))

    content = build_content(header_lines, fuel_rows, pre_wx, wx_rows, pre_wind, wind_rows, post_wind,
                            spotting_seed,
                            temp_offsets, hum_offsets,
                            direction_offsets, speed_multipliers)

    with open(output_path, "w") as f:
        f.write(content)

    print(f"[generate_run] {run_id}: "
          f"dir={direction_offsets.mean():+.1f}° "
          f"spd=x{speed_multipliers.mean():.2f} "
          f"T={temp_offsets.mean():+.1f}°F "
          f"H={hum_offsets.mean():+.1f}%")


if __name__ == "__main__":
    main()
