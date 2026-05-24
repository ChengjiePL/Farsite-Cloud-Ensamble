#!/bin/bash
# Step 6: Run convergence analysis as a Kubernetes Job on EKS.
#
# Builds the convergence curve (metric vs N) by subsampling the ensemble already
# in S3 — no need to launch the pipeline once per N. Downloads only the CSV + PNG
# (a few KB); the raw 30GB of grids never leave AWS.
#
# Usage:
#   bash scripts/06_convergence_on_eks.sh [N_RUNS] [case_name]
#   bash scripts/06_convergence_on_eks.sh 10000 case_7

set -euo pipefail

cd "$(dirname "$0")/.."

N_RUNS="${1:-10000}"
CASE_NAME="${2:-case_7}"
CASE_ENV="cases/${CASE_NAME}.env"

if [ ! -f "$CASE_ENV" ]; then
    echo "ERROR: Case config not found: $CASE_ENV"
    exit 1
fi
source "$CASE_ENV"

echo "── Step 6: Convergence analysis on EKS ──"
echo "Case: $CASE_NAME ($CASE_LABEL)"

RUNNER_IMAGE=$(terraform -chdir=terraform output -raw runner_image)
S3_BUCKET=$(terraform -chdir=terraform output -raw s3_bucket_name)

# Delete previous convergence job if exists
kubectl delete job farsite-convergence --ignore-not-found

echo "Submitting convergence job..."
kubectl apply -f - <<EOF
apiVersion: batch/v1
kind: Job
metadata:
  name: farsite-convergence
spec:
  ttlSecondsAfterFinished: 3600
  backoffLimit: 1
  template:
    spec:
      restartPolicy: Never
      containers:
        - name: convergence
          image: ${RUNNER_IMAGE}
          command: ["/usr/local/bin/run_convergence.sh"]
          env:
            - name: S3_BUCKET
              value: "${S3_BUCKET}"
            - name: N_RUNS
              value: "${N_RUNS}"
            - name: CASE_LABEL
              value: "${CASE_LABEL}"
          resources:
            requests:
              cpu: "1"
              memory: "3Gi"
            limits:
              cpu: "2"
              memory: "4Gi"
EOF

echo "Waiting for convergence job to complete..."
kubectl wait --for=condition=complete job/farsite-convergence --timeout=7200s

echo ""
echo "Downloading results from S3..."
aws s3 cp "s3://$S3_BUCKET/results/convergence.png" convergence.png
aws s3 cp "s3://$S3_BUCKET/results/convergence.csv" convergence.csv
# Also keep the aggregated probability grid — reused later for coverage/precision
# without re-running the ensemble.
aws s3 cp "s3://$S3_BUCKET/results/prob_final.npy"  prob_final.npy

echo "Saved: convergence.png, convergence.csv, prob_final.npy"
