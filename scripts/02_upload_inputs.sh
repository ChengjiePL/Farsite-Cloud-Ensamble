#!/bin/bash
# Step 2: Upload base assets to S3 (Case 7 extended — Nunomoral, Cáceres).
#
# Uploads to base/:
#   - CASE_7.lcp                  — landscape file
#   - case_7_extended.input       — wind/fuel template (pods generate perturbations on-the-fly)
#   - Per1_utm.*                  — ignition shapefile (fire start, 222 ha)
#   - Per2_utm.*, Per3_utm.*      — observed perimeters (for visualization pod)
#
# NOTE: perturbed .input files are NO LONGER uploaded — each pod generates its
# own using generate_run.py. This reduces upload from ~2-3h to ~30 seconds.
#
# Usage:
#   cd <project-root> && bash scripts/02_upload_inputs.sh

set -euo pipefail

cd "$(dirname "$0")/.."

echo "── Step 2: Upload base assets to S3 ──"

BUCKET=$(terraform -chdir=terraform output -raw s3_bucket_name)
echo "Bucket: s3://$BUCKET"
echo ""

# ── Landscape + wind template ──────────────────────────────────────────────────
echo "Uploading landscape and wind template..."
aws s3 cp tests/CASE_7.lcp                  "s3://$BUCKET/base/CASE_7.lcp"
aws s3 cp tests/case_7_extended.input       "s3://$BUCKET/base/case_7_extended.input"

# ── Ignition shapefile (Case7_ignition — ~36 ha, centre de l'incendi) ─────────
echo "Uploading ignition shapefile..."
for ext in shp shx prj dbf; do
    [ -f "tests/Case7_ignition.$ext" ] && \
        aws s3 cp "tests/Case7_ignition.$ext" "s3://$BUCKET/base/Case7_ignition.$ext"
done

# ── Observed final perimeter (Per4_utm — 1761 ha, per visualització) ──────────
echo "Uploading observed perimeter shapefile..."
for ext in shp shx prj dbf; do
    [ -f "tests/Per4_utm.$ext" ] && \
        aws s3 cp "tests/Per4_utm.$ext" "s3://$BUCKET/base/Per4_utm.$ext"
done

echo ""
echo "Upload complete. Summary:"
aws s3 ls "s3://$BUCKET/base/" --recursive --human-readable --summarize 2>/dev/null | tail -2
echo ""
echo "No perturbed .input files needed — pods generate them on-the-fly."
