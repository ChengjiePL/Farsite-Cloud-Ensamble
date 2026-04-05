# ── EKS Cluster ──────────────────────────────────────────────────────────────

resource "aws_eks_cluster" "farsite" {
  name     = var.cluster_name
  role_arn = aws_iam_role.eks_cluster.arn
  version  = var.kubernetes_version

  vpc_config {
    subnet_ids             = aws_subnet.public[*].id
    endpoint_public_access = true   # kubectl accessible from your laptop
  }

  tags = local.common_tags

  depends_on = [
    aws_iam_role_policy_attachment.eks_cluster_policy,
  ]
}

# ── EKS Managed Node Group ───────────────────────────────────────────────────
# SPOT instances: up to 70% cheaper than On-Demand.
# FARSITE is stateless — if a Spot node is reclaimed, Kubernetes restarts the Job.

resource "aws_launch_template" "farsite" {
  name_prefix = "${local.project}-node-"

  # IMDSv2 hop limit = 2 so pods inside containers can reach EC2 metadata
  # (default hop limit of 1 blocks pods from assuming the node IAM role)
  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required"
    http_put_response_hop_limit = 2
  }

  tag_specifications {
    resource_type = "instance"
    tags          = local.common_tags
  }
}

resource "aws_eks_node_group" "farsite" {
  cluster_name    = aws_eks_cluster.farsite.name
  node_group_name = "${local.project}-workers"
  node_role_arn   = aws_iam_role.eks_node.arn
  subnet_ids      = aws_subnet.public[*].id

  instance_types = [var.node_instance_type]
  capacity_type  = "SPOT"

  launch_template {
    id      = aws_launch_template.farsite.id
    version = aws_launch_template.farsite.latest_version
  }

  scaling_config {
    desired_size = var.node_desired
    min_size     = 0
    max_size     = var.node_max
  }

  update_config {
    max_unavailable = 1
  }

  tags = local.common_tags

  depends_on = [
    aws_iam_role_policy_attachment.eks_worker_node_policy,
    aws_iam_role_policy_attachment.eks_cni_policy,
    aws_iam_role_policy_attachment.eks_ecr_read,
    aws_iam_role_policy.eks_node_s3,
  ]
}
