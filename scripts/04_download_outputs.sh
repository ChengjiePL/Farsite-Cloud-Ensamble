#!/bin/bash
# Step 4: Wait for all jobs to finish, then download outputs from S3.
#
# Polls Kubernetes until all Jobs are Complete or Failed.
# Downloads all ArrivalTime.asc files (the key output for burn probability maps)
# plus any other FARSITE outputs.
#
# Usage:
#   cd <project-root> && bash scripts/04_download_outputs.sh [N_RUNS]
#   Default N_RUNS = 500

set -eo pipefail

cd "$(dirname "$0")/.."

N_RUNS="${1:-1000}"
POLL_INTERVAL=30

echo "── Step 4: Wait for jobs and download outputs ──"

BUCKET=$(terraform -chdir=terraform output -raw s3_bucket_name 2>/dev/null) || {
    echo "ERROR: could not get bucket name from terraform. Run: terraform -chdir=terraform output"
    exit 1
}
echo "Bucket: s3://$BUCKET"
echo ""

# ── Wait for completion (S3 as source of truth) ──────────────────────────────
echo "Polling every ${POLL_INTERVAL}s until $N_RUNS run folders appear in S3..."
echo "(Ctrl-C to skip waiting and download whatever is ready)"
echo ""

while true; do
    S3_COUNT=$(aws s3 ls "s3://$BUCKET/outputs/" 2>/dev/null | grep -c "PRE " || echo 0)

    echo "  $(date +%H:%M:%S)  S3 runs: $S3_COUNT / $N_RUNS"

    if [ "$S3_COUNT" -ge "$N_RUNS" ]; then
        echo ""
        echo "All $N_RUNS runs found in S3."
        break
    fi

    sleep "$POLL_INTERVAL"
done

# ── Download outputs ──────────────────────────────────────────────────────────
echo ""
echo "Syncing outputs from s3://$BUCKET/outputs/ → output/"
mkdir -p output

aws s3 sync "s3://$BUCKET/outputs/" output/ --quiet

DOWNLOADED=$(find output -name "*ArrivalTime.asc" | wc -l | tr -d ' ')
echo ""
echo "Downloaded $DOWNLOADED ArrivalTime.asc files to output/"
echo ""
echo "Next step — generate burn probability map:"
echo "  .venv/bin/python3 visualize_v6_probability.py"
