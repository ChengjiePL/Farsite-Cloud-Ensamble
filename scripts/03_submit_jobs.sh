#!/bin/bash
# Step 3: Submit N Kubernetes Jobs to the EKS cluster.
#
# Usage:
#   bash scripts/03_submit_jobs.sh [N_RUNS] [case_name]
#   bash scripts/03_submit_jobs.sh 1000 case_7      # default

set -euo pipefail

cd "$(dirname "$0")/.."

N_RUNS="${1:-1000}"
CASE_NAME="${2:-case_7}"
CASE_ENV="cases/${CASE_NAME}.env"

if [ ! -f "$CASE_ENV" ]; then
    echo "ERROR: Case config not found: $CASE_ENV"
    echo "Available cases:"
    ls cases/*.env 2>/dev/null | sed 's|cases/||;s|\.env||' | sed 's/^/  /'
    exit 1
fi

source "$CASE_ENV"

echo "── Step 3: Submit $N_RUNS FARSITE jobs to EKS ──"

REGION=$(terraform -chdir=terraform output -raw aws_region)
CLUSTER=$(terraform -chdir=terraform output -raw cluster_name)
RUNNER_IMAGE=$(terraform -chdir=terraform output -raw runner_image)
S3_BUCKET=$(terraform -chdir=terraform output -raw s3_bucket_name)

echo "Cluster: $CLUSTER  ($REGION)"
echo "Image:   $RUNNER_IMAGE"
echo "Bucket:  s3://$S3_BUCKET"
echo "Case:    $CASE_NAME ($CASE_LABEL)"

# Delete any existing farsite jobs (spec.template is immutable — can't patch existing jobs)
echo "Deleting existing farsite jobs (if any)..."
kubectl delete jobs -l app=farsite --ignore-not-found --wait=false

echo "Generating and submitting $N_RUNS job manifests..."

(
  for i in $(seq 1 "$N_RUNS"); do
    RUN_ID=$(printf "run_%03d" "$i")
    JOB_NAME=$(printf "farsite-run-%03d" "$i")
    cat <<EOF
apiVersion: batch/v1
kind: Job
metadata:
  name: ${JOB_NAME}
  labels:
    app: farsite
    case: ${CASE_NAME}
spec:
  ttlSecondsAfterFinished: 3600
  backoffLimit: 2
  template:
    metadata:
      labels:
        app: farsite
        case: ${CASE_NAME}
    spec:
      activeDeadlineSeconds: 1800
      restartPolicy: OnFailure
      containers:
        - name: farsite
          image: ${RUNNER_IMAGE}
          env:
            - name: RUN_ID
              value: "${RUN_ID}"
            - name: S3_BUCKET
              value: "${S3_BUCKET}"
            - name: LCP_FILE
              value: "${LCP_FILE}"
            - name: INPUT_TEMPLATE
              value: "${INPUT_TEMPLATE}"
            - name: IGNITION_FILE
              value: "${IGNITION_FILE}"
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
