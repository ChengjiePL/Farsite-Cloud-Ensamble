terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket         = "farsite-tfstate-v2"       # Nombre del bucket
    key            = "terraform.tfstate"     # Ruta dentro del bucket
    region         = "eu-west-1"
    dynamodb_table = "farsite-tfstate-lock-v2"
    encrypt        = true
  }
}

provider "aws" {
  region = var.aws_region
}

data "aws_caller_identity" "current" {}
data "aws_availability_zones" "available" { state = "available" }

locals {
  project = var.project_name

  common_tags = {
    Project     = var.project_name
    ManagedBy   = "terraform"
    Environment = "tfg"
  }
}
