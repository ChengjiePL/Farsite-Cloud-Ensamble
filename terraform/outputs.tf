output "aws_region" {
  description = "AWS region"
  value       = var.aws_region
}

output "runner_image" {
  description = "Docker image reference used in Kubernetes Job specs"
  value       = var.runner_image
}

output "s3_bucket_name" {
  description = "S3 bucket name for simulation inputs and outputs"
  value       = aws_s3_bucket.farsite.id
}

output "cluster_name" {
  description = "EKS cluster name — used in aws eks update-kubeconfig"
  value       = aws_eks_cluster.farsite.name
}

output "cluster_endpoint" {
  description = "EKS API server endpoint"
  value       = aws_eks_cluster.farsite.endpoint
}

output "kubeconfig_command" {
  description = "Run this command to configure kubectl after the cluster is ready"
  value       = "aws eks update-kubeconfig --region ${var.aws_region} --name ${var.cluster_name}"
}
