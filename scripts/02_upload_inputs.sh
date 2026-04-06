#!/bin/bash
# Step 2: Upload base assets to S3 for a given fire case.
#
# Reads case configuration from cases/<CASE_NAME>.env which defines:
#   LCP_FILE, INPUT_TEMPLATE, IGNITION_FILE, OBSERVED_SHP
#
# NOTE: perturbed .input files are NOT uploaded — each pod generates its
# own using generate_run.py. This reduces upload from ~2-3h to ~30 seconds.
#
# Usage:
#   bash scripts/02_upload_inputs.sh [case_name]
#   bash scripts/02_upload_inputs.sh case_7      # default

set -euo pipefail

cd "$(dirname "$0")/.."

CASE_NAME="${1:-case_7}"
CASE_ENV="cases/${CASE_NAME}.env"

if [ ! -f "$CASE_ENV" ]; then
    echo "ERROR: Case config not found: $CASE_ENV"
    echo "Available cases:"
    ls cases/*.env 2>/dev/null | sed 's|cases/||;s|\.env||' | sed 's/^/  /'
    exit 1
fi

# Load case config
source "$CASE_ENV"

echo "── Step 2: Upload base assets to S3 ──"
echo "Case:   $CASE_NAME ($CASE_LABEL)"

BUCKET=$(terraform -chdir=terraform output -raw s3_bucket_name)
echo "Bucket: s3://$BUCKET"
echo ""

# Strip .shp extension from IGNITION_FILE for shapefile upload loop
IGNITION_BASE="${IGNITION_FILE%.shp}"
OBSERVED_BASE="${OBSERVED_SHP}"

# ── Landscape + wind template ──────────────────────────────────────────────────
echo "Uploading landscape and wind template..."
aws s3 cp "tests/$LCP_FILE"        "s3://$BUCKET/base/$LCP_FILE"
aws s3 cp "tests/$INPUT_TEMPLATE"  "s3://$BUCKET/base/$INPUT_TEMPLATE"

# ── Ignition shapefile ─────────────────────────────────────────────────────────
echo "Uploading ignition shapefile ($IGNITION_BASE)..."
for ext in shp shx prj dbf; do
    [ -f "tests/${IGNITION_BASE}.${ext}" ] && \
        aws s3 cp "tests/${IGNITION_BASE}.${ext}" "s3://$BUCKET/base/${IGNITION_BASE}.${ext}"
done

# ── Observed perimeter (for visualization) ────────────────────────────────────
echo "Uploading observed perimeter shapefile ($OBSERVED_BASE)..."
for ext in shp shx prj dbf; do
    [ -f "tests/${OBSERVED_BASE}.${ext}" ] && \
        aws s3 cp "tests/${OBSERVED_BASE}.${ext}" "s3://$BUCKET/base/${OBSERVED_BASE}.${ext}"
done

echo ""
echo "Upload complete. Summary:"
aws s3 ls "s3://$BUCKET/base/" --recursive --human-readable --summarize 2>/dev/null | tail -2
echo ""
echo "No perturbed .input files needed — pods generate them on-the-fly."
