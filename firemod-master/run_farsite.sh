#!/bin/bash
# Entrypoint for the farsite-runner container.
#
# Environment variables (set by the Kubernetes Job):
#   RUN_ID       — e.g. run_042
#   S3_BUCKET    — bucket name (without s3:// prefix)
#
# Optional overrides (defaults shown):
#   S3_BASE_PREFIX    = base      (landscape + ignition files)
#   S3_INPUT_PREFIX   = inputs    (perturbed .input files)
#   S3_OUTPUT_PREFIX  = outputs   (FARSITE result grids)

set -euo pipefail

RUN_ID="${RUN_ID:?RUN_ID environment variable is required}"
S3_BUCKET="${S3_BUCKET:?S3_BUCKET environment variable is required}"
S3_BASE="${S3_BASE_PREFIX:-base}"
S3_INPUTS="${S3_INPUT_PREFIX:-inputs}"
S3_OUTPUTS="${S3_OUTPUT_PREFIX:-outputs}"

echo "[farsite] ── Starting $RUN_ID ──"

mkdir -p /data/input /data/output/"$RUN_ID"

# ── 1. Download shared base assets (landscape + ignition shapefile) ───────────
echo "[farsite] Downloading base assets from s3://$S3_BUCKET/$S3_BASE/"
aws s3 sync "s3://$S3_BUCKET/$S3_BASE/" /data/input/ --quiet

# ── 2. Generate run-specific perturbed .input file (no S3 download needed) ───
echo "[farsite] Generating perturbation for $RUN_ID"
python3 /usr/local/bin/generate_run.py \
    "$RUN_ID" \
    "/data/input/case_1_extended.input" \
    "/data/input/$RUN_ID.input"

# ── 3. Build command file (TestFARSITE reads a 6-token file, not CLI args) ────
cat > /tmp/cmd.txt <<CMD
/data/input/CASE_1.lcp /data/input/$RUN_ID.input /data/input/Per1_02092013.shp 0 /data/output/$RUN_ID/$RUN_ID 0
CMD

# ── 4. Run FARSITE ────────────────────────────────────────────────────────────
echo "[farsite] Running simulation..."
TestFARSITE /tmp/cmd.txt

# ── 5. Upload outputs ─────────────────────────────────────────────────────────
echo "[farsite] Uploading outputs to s3://$S3_BUCKET/$S3_OUTPUTS/$RUN_ID/"
aws s3 sync \
    "/data/output/$RUN_ID/" \
    "s3://$S3_BUCKET/$S3_OUTPUTS/$RUN_ID/" \
    --quiet

echo "[farsite] ── $RUN_ID completed successfully ──"
