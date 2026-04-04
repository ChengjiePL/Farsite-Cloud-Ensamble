#!/bin/bash
# Visualization pod entrypoint.
# Downloads ArrivalTime grids + shapefiles from S3, generates probability map,
# uploads PNG result back to S3. Only ~1MB leaves AWS.
#
# Environment variables:
#   S3_BUCKET    — bucket name (required)
#   N_RUNS       — expected number of runs (default 10000)

set -euo pipefail

S3_BUCKET="${S3_BUCKET:?S3_BUCKET is required}"
N_RUNS="${N_RUNS:-10000}"

echo "[visualize] ── Starting probability map generation ──"
echo "[visualize] Bucket: s3://$S3_BUCKET  N_RUNS: $N_RUNS"

mkdir -p /data/output /data/input/tests

# ── 1. Download only ArrivalTime.asc files (not all outputs) ─────────────────
echo "[visualize] Downloading ArrivalTime grids from S3..."
aws s3 sync "s3://$S3_BUCKET/outputs/" /data/output/ \
    --exclude "*" \
    --include "*ArrivalTime.asc" \
    --quiet

LOADED=$(find /data/output -name "*ArrivalTime.asc" | wc -l)
echo "[visualize] Downloaded $LOADED ArrivalTime.asc files"

# ── 2. Download observed perimeter shapefiles ─────────────────────────────────
echo "[visualize] Downloading shapefiles..."
aws s3 sync "s3://$S3_BUCKET/base/" /data/input/ --quiet

# ── 3. Run visualization ──────────────────────────────────────────────────────
echo "[visualize] Generating probability map..."
ENSEMBLE_DIR=/data/output \
TESTS_DIR=/data/input/tests \
OUTPUT_FILE=/data/output/farsite_probability.png \
N_RUNS=$N_RUNS \
python3 /usr/local/bin/visualize_probability.py

# ── 4. Upload result PNG to S3 ────────────────────────────────────────────────
echo "[visualize] Uploading result to s3://$S3_BUCKET/results/farsite_probability.png"
aws s3 cp /data/output/farsite_probability.png \
    "s3://$S3_BUCKET/results/farsite_probability.png"

echo "[visualize] ── Done ──"
