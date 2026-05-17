# S3 bucket for simulation data.
# Layout:
#   base/        — shared assets: CASE_1.lcp, Per1_02092013.* (uploaded once)
#   inputs/      — run_001/ ... run_500/  (one .input file each)
#   outputs/     — run_001/ ... run_500/  (ArrivalTime.asc + other FARSITE outputs)

resource "aws_s3_bucket" "farsite" {
  # Account ID suffix ensures the bucket name is globally unique.
  bucket = "${local.project}-simulations-${data.aws_caller_identity.current.account_id}"

  # Allow `terraform destroy` to remove the bucket even when it still contains
  # objects. Uses parallel BatchDelete under the hood — much faster than the
  # serial `aws s3 rm --recursive`, which was taking ~2h on 10k+ run buckets.
  force_destroy = true

  tags = local.common_tags
}

resource "aws_s3_bucket_public_access_block" "farsite" {
  bucket = aws_s3_bucket.farsite.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Versioning is unnecessary for simulation data — saves cost.
resource "aws_s3_bucket_versioning" "farsite" {
  bucket = aws_s3_bucket.farsite.id
  versioning_configuration {
    status = "Disabled"
  }
}
