#!/bin/bash
# Step 5: Run visualization as a Kubernetes Job on EKS.
#
# Downloads ArrivalTime grids from S3 (internal, free), generates the
# probability map PNG, and uploads it back to s3://BUCKET/results/.
# Only ~1MB leaves AWS — no 30GB local download needed.
#
# Usage:
#   bash scripts/05_visualize_on_eks.sh [N_RUNS] [case_name]

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

echo "── Step 5: Visualization job on EKS ──"
echo "Case: $CASE_NAME ($CASE_LABEL)"

REGION=$(terraform -chdir=terraform output -raw aws_region)
CLUSTER=$(terraform -chdir=terraform output -raw cluster_name)
RUNNER_IMAGE=$(terraform -chdir=terraform output -raw runner_image)
S3_BUCKET=$(terraform -chdir=terraform output -raw s3_bucket_name)

# Note: assumes kubectl is already configured (run aws eks update-kubeconfig manually if needed)

# Delete previous visualization job if exists
kubectl delete job farsite-visualize --ignore-not-found

echo "Submitting visualization job..."
kubectl apply -f - <<EOF
apiVersion: batch/v1
kind: Job
metadata:
  name: farsite-visualize
spec:
  ttlSecondsAfterFinished: 3600
  backoffLimit: 1
  template:
    spec:
      restartPolicy: Never
      containers:
        - name: visualize
          image: ${RUNNER_IMAGE}
          command: ["/usr/local/bin/run_visualize.sh"]
          env:
            - name: S3_BUCKET
              value: "${S3_BUCKET}"
            - name: N_RUNS
              value: "${N_RUNS}"
            - name: CASE_LABEL
              value: "${CASE_LABEL}"
            - name: OBSERVED_SHP
              value: "${OBSERVED_SHP}"
            - name: OBSERVED_LABEL
              value: "${OBSERVED_LABEL}"
            - name: IGNITION_SHP
              value: "${IGNITION_FILE%.shp}"
            - name: IGNITION_LABEL
              value: "Ignició"
            # Optional second suptitle line describing the perturbation.
            # Define PERTURBATION_LABEL in the case .env (or export it) to set it;
            # left empty the visualization just shows case + run count.
            - name: PERTURBATION_LABEL
              value: "${PERTURBATION_LABEL:-}"
          resources:
            requests:
              cpu: "1"
              memory: "3Gi"
            limits:
              cpu: "2"
              memory: "4Gi"
EOF

echo "Waiting for visualization job to complete..."
kubectl wait --for=condition=complete job/farsite-visualize --timeout=7200s

echo ""
echo "Downloading result PNG from S3..."
aws s3 cp "s3://$S3_BUCKET/results/farsite_probability.png" farsite_v6_probability.png

echo "Saved: farsite_v6_probability.png"
