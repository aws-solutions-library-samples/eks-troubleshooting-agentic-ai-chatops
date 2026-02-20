################################################################################
# Cluster Outputs
################################################################################

output "cluster_name" {
  description = "EKS cluster name"
  value       = module.eks.cluster_name
}

output "cluster_endpoint" {
  description = "EKS cluster endpoint"
  value       = module.eks.cluster_endpoint
}

output "cluster_security_group_id" {
  description = "Security group ID attached to the EKS cluster"
  value       = module.eks.cluster_security_group_id
}

output "cluster_oidc_provider_arn" {
  description = "OIDC provider ARN for the EKS cluster"
  value       = module.eks.oidc_provider_arn
}

output "region" {
  description = "AWS region"
  value       = local.region
}

################################################################################
# VPC Outputs
################################################################################

output "vpc_id" {
  description = "VPC ID"
  value       = module.vpc.vpc_id
}

output "private_subnets" {
  description = "Private subnet IDs"
  value       = module.vpc.private_subnets
}

output "public_subnets" {
  description = "Public subnet IDs"
  value       = module.vpc.public_subnets
}

################################################################################
# Agentic Agent Outputs
################################################################################

output "agentic_agent_role_arn" {
  description = "IAM role ARN for the agentic troubleshooting agent"
  value       = aws_iam_role.agentic_agent_role.arn
}

output "agentic_agent_service_account" {
  description = "Kubernetes service account name for the agentic agent"
  value       = "k8s-troubleshooting-agent"
}

################################################################################
# Configuration Commands
################################################################################

output "configure_kubectl" {
  description = "Command to configure kubectl"
  value       = "aws eks update-kubeconfig --region ${local.region} --name ${module.eks.cluster_name}"
}

output "helm_status_command" {
  description = "Command to check agentic agent deployment status"
  value       = "helm status k8s-troubleshooting-agent -n default"
}
