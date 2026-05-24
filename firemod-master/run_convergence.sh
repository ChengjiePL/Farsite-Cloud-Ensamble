#!/bin/bash
# Convergence-analysis pod entrypoint.
# Downloads ArrivalTime grids from S3, builds the convergence curve (metric vs N)
# by subsampling a single ensemble, and uploads the CSV + PNG + final
# probability grid. Only a few KB/MB leave AWS.
#
# Environment variables:
#   S3_BUCKET    — bucket name (required)
#   N_RUNS       — total runs in the ensemble (default 10000)
#   CASE_LABEL   — optional, used in the plot title

set -euo pipefail

S3_BUCKET="${S3_BUCKET:?S3_BUCKET is required}"
N_RUNS="${N_RUNS:-10000}"

echo "[convergence] ── Starting convergence analysis ──"
echo "[convergence] Bucket: s3://$S3_BUCKET  N_RUNS: $N_RUNS"

mkdir -p /data/output

# ── 1. Download only ArrivalTime.asc files (not all outputs) ──────────────────
echo "[convergence] Downloading ArrivalTime grids from S3..."
aws s3 sync "s3://$S3_BUCKET/outputs/" /data/output/ \
    --exclude "*" \
    --include "*ArrivalTime.asc" \
    --quiet

LOADED=$(find /data/output -name "*ArrivalTime.asc" | wc -l)
echo "[convergence] Downloaded $LOADED ArrivalTime.asc files"

# ── 2. Run convergence analysis ───────────────────────────────────────────────
echo "[convergence] Computing convergence curve..."
ENSEMBLE_DIR=/data/output \
N_RUNS=$N_RUNS \
CASE_LABEL="${CASE_LABEL:-}" \
OUTPUT_CSV=/data/output/convergence.csv \
OUTPUT_PNG=/data/output/convergence.png \
OUTPUT_NPY=/data/output/prob_final.npy \
python3 /usr/local/bin/convergence.py

# ── 3. Upload results to S3 ────────────────────────────────────────────────────
echo "[convergence] Uploading results to s3://$S3_BUCKET/results/"
aws s3 cp /data/output/convergence.png "s3://$S3_BUCKET/results/convergence.png"
aws s3 cp /data/output/convergence.csv "s3://$S3_BUCKET/results/convergence.csv"
aws s3 cp /data/output/prob_final.npy  "s3://$S3_BUCKET/results/prob_final.npy"

echo "[convergence] ── Done ──"
