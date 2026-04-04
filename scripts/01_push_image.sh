#!/bin/bash
# Step 1: Build the farsite-runner Docker image and push it to DockerHub.
#
# Prerequisites:
#   - docker login  (run once: docker login --username YOUR_USERNAME)
#   - Edit variables.tf: set runner_image = "YOUR_USERNAME/farsite-runner:latest"
#   - terraform apply must have been run at least once (to read outputs)
#
# Usage:
#   cd <project-root> && bash scripts/01_push_image.sh

set -euo pipefail

cd "$(dirname "$0")/.."

echo "── Step 1: Build and push farsite-runner to DockerHub ──"

RUNNER_IMAGE=$(terraform -chdir=terraform output -raw runner_image)

if [[ "$RUNNER_IMAGE" == "CHANGE_ME/"* ]]; then
    echo "ERROR: Set the runner_image variable in terraform/variables.tf first."
    echo "       Example: default = \"yourname/farsite-runner:latest\""
    exit 1
fi

echo "Image: $RUNNER_IMAGE"
echo ""

echo "Building farsite-runner image..."
docker build \
    -t farsite-runner:latest \
    -f firemod-master/Dockerfile.runner \
    firemod-master/

echo ""
echo "Tagging as $RUNNER_IMAGE ..."
docker tag farsite-runner:latest "$RUNNER_IMAGE"

echo "Pushing to DockerHub..."
docker push "$RUNNER_IMAGE"

echo ""
echo "Done. Image available at: $RUNNER_IMAGE"
echo "(Make sure the repository is set to PUBLIC in DockerHub settings)"
