#!/bin/bash
set -euo pipefail

# Variables
REGION="${AWS_REGION:-eu-west-1}" # puedes definir AWS_REGION en el runner
BUCKET_NAME="${TF_STATE_BUCKET:-farsite-tfstate}"
DYNAMODB_TABLE="${TF_LOCK_TABLE:-farsite-tfstate-lock}"
PROFILE="${AWS_PROFILE:-default}"

echo "Creating S3 bucket for Terraform state: $BUCKET_NAME in $REGION..."
aws s3api create-bucket \
  --bucket "$BUCKET_NAME" \
  --region "$REGION" \
  --create-bucket-configuration LocationConstraint="$REGION" 2>/dev/null || echo "Bucket exists"

echo "Enabling versioning on the bucket..."
aws s3api put-bucket-versioning \
  --bucket "$BUCKET_NAME" \
  --versioning-configuration Status=Enabled

echo "Creating DynamoDB table for state locking: $DYNAMODB_TABLE..."
aws dynamodb create-table \
  --table-name "$DYNAMODB_TABLE" \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST 2>/dev/null || echo "Table exists"

echo ""
echo "✅ S3 backend and DynamoDB lock table ready."
echo "Next step: terraform init -backend-config=bucket=$BUCKET_NAME -backend-config=key=terraform.tfstate -backend-config=region=$REGION -backend-config=dynamodb_table=$DYNAMODB_TABLE"
