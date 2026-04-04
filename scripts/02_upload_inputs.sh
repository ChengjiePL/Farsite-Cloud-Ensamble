#!/bin/bash
# Step 2: Upload base assets to S3 (Case 1 extended).
#
# Uploads to base/:
#   - CASE_1.lcp                  — landscape file
#   - case_1_extended.input       — wind/fuel template (pods generate perturbations on-the-fly)
#   - Per1_02092013.*             — ignition shapefile
#   - Per1..Per4_*.shp/shx/prj   — observed perimeters (for visualization pod)
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
aws s3 cp tests/CASE_1.lcp                  "s3://$BUCKET/base/CASE_1.lcp"
aws s3 cp tests/case_1_extended.input       "s3://$BUCKET/base/case_1_extended.input"

# ── Ignition shapefile (Per1 — simulation start) ───────────────────────────────
echo "Uploading ignition shapefile..."
for ext in shp shx prj dbf sbn sbx; do
    [ -f "tests/Per1_02092013.$ext" ] && \
        aws s3 cp "tests/Per1_02092013.$ext" "s3://$BUCKET/base/tests/Per1_02092013.$ext"
done

# ── Observed perimeters (Per1-Per4 — for visualization) ───────────────────────
echo "Uploading observed perimeter shapefiles..."
for per in Per1_02092013 Per2_03092013 Per3_04092013 Per4_06092013; do
    for ext in shp shx prj dbf sbn sbx; do
        [ -f "tests/$per.$ext" ] && \
            aws s3 cp "tests/$per.$ext" "s3://$BUCKET/base/tests/$per.$ext"
    done
done

echo ""
echo "Upload complete. Summary:"
aws s3 ls "s3://$BUCKET/base/" --recursive --human-readable --summarize 2>/dev/null | tail -2
echo ""
echo "No perturbed .input files needed — pods generate them on-the-fly."
