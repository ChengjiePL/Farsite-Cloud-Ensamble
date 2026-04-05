#!/bin/bash
# Step 3: Submit N Kubernetes Jobs to the EKS cluster.
#
# Cluster architecture:
#   25 worker nodes (t3.medium SPOT) × 2 pods per node = 50 concurrent runs
#   500 runs / 50 concurrent = ~10 min total (1h simulation per run)
#
# All 500 manifests are piped to kubectl in a single API call.
#
# Usage:
#   cd <project-root> && bash scripts/03_submit_jobs.sh [N_RUNS]

set -euo pipefail

cd "$(dirname "$0")/.."

N_RUNS="${1:-1000}"

echo "── Step 3: Submit $N_RUNS FARSITE jobs to EKS ──"

REGION=$(terraform -chdir=terraform output -raw aws_region)
CLUSTER=$(terraform -chdir=terraform output -raw cluster_name)
RUNNER_IMAGE=$(terraform -chdir=terraform output -raw runner_image)
S3_BUCKET=$(terraform -chdir=terraform output -raw s3_bucket_name)

echo "Cluster: $CLUSTER  ($REGION)"
echo "Image:   $RUNNER_IMAGE"
echo "Bucket:  s3://$S3_BUCKET"

echo ""
echo "Configuring kubectl..."
aws eks update-kubeconfig --region "$REGION" --name "$CLUSTER"

echo "Generating and submitting $N_RUNS job manifests..."

(
for i in $(seq 1 "$N_RUNS"); do
    RUN_ID=$(printf "run_%03d" "$i")        # matches S3 files: run_001.input
    JOB_NAME=$(printf "farsite-run-%03d" "$i")  # k8s name: no underscores allowed
    cat <<EOF
apiVersion: batch/v1
kind: Job
metadata:
  name: ${JOB_NAME}
  labels:
    app: farsite
spec:
  ttlSecondsAfterFinished: 3600
  activeDeadlineSeconds: 600
  backoffLimit: 1
  template:
    spec:
      restartPolicy: OnFailure
      containers:
        - name: farsite
          image: ${RUNNER_IMAGE}
          env:
            - name: RUN_ID
              value: "${RUN_ID}"
            - name: S3_BUCKET
              value: "${S3_BUCKET}"
          resources:
            requests:
              cpu: "900m"
              memory: "700Mi"
            limits:
              cpu: "1"
              memory: "1.5Gi"
---
EOF
done
) | kubectl apply -f -

echo ""
echo "All $N_RUNS jobs submitted."
echo ""
echo "Monitor progress:"
echo "  kubectl get pods -l app=farsite --no-headers | awk '{print \$3}' | sort | uniq -c"
