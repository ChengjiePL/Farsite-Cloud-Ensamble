variable "aws_region" {
  description = "AWS region where all resources will be created"
  type        = string
  default     = "eu-west-1"
}

variable "project_name" {
  description = "Name prefix applied to all resources"
  type        = string
  default     = "farsite-tfg"
}

variable "cluster_name" {
  description = "EKS cluster name"
  type        = string
  default     = "farsite-cluster"
}

variable "kubernetes_version" {
  description = "EKS Kubernetes version"
  type        = string
  default     = "1.30"
}

variable "node_instance_type" {
  description = "EC2 instance type for EKS worker nodes"
  type        = string
  default     = "c7i-flex.large"   # 2 vCPU, 4 GB RAM — fits 2 FARSITE pods simultaneously
}

variable "node_desired" {
  description = <<-EOT
    Number of worker nodes to launch.
    Each t3.medium fits 2 FARSITE pods → desired×2 = concurrent simulations.

    Case 7  (1h simulation, ~3s/run):  5 nodes → 10 concurrent → ~10 min for 500 runs
    Case 1+ (4d simulation, ~7m/run): 25 nodes → 50 concurrent → ~60 min for 500 runs
  EOT
  type        = number
  default     = 16  # SPOT quota separate from On-Demand → 32 concurrent pods
}

variable "node_max" {
  description = "Maximum number of worker nodes (auto-scaling ceiling)"
  type        = number
  default     = 16  # SPOT allows more nodes than On-Demand quota
}

variable "runner_image" {
  description = "Full Docker image reference for the farsite-runner container (DockerHub or any registry)"
  type        = string
  default     = "chengjiepl/farsite-runner:latest"   # e.g. "joansmith/farsite-runner:latest"
}
