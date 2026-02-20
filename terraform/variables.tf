variable "name" {
  default = "eks-llm-troubleshooting"
}

variable "slack_webhook_url" {
  description = "Slack webhook URL for Prometheus AlertManager notifications (used by both deployments)"
  type        = string
  default     = ""
}

variable "slack_channel_name" {
  description = "Slack channel name for Prometheus AlertManager notifications (used by both deployments)"
  type        = string
  default     = ""
}

variable "opensearch_collection_name" {
  description = "Name for the OpenSearch Serverless collection"
  type        = string
  default     = "vector-col"
}

variable "deployment_type" {
  description = "Type of deployment: 'agentic' for Agentic AI troubleshooting or 'rag' for RAG-based chatbot (deprecated)"
  type        = string
  default     = "agentic"
  validation {
    condition     = contains(["rag", "agentic"], var.deployment_type)
    error_message = "Deployment type must be either 'agentic' or 'rag' (deprecated)."
  }
}

# Agentic deployment specific variables
variable "agentic_image_repository" {
  description = "ECR repository for the Agentic AI troubleshooting agent image"
  type        = string
  default     = ""
}

variable "agentic_image_tag" {
  description = "Tag for the Agentic AI troubleshooting agent image"
  type        = string
  default     = "latest"
}

variable "slack_bot_token" {
  description = "Slack bot token for Agentic AI deployment"
  type        = string
  default     = ""
  sensitive   = true
}

variable "slack_app_token" {
  description = "Slack app token for Agentic AI deployment"
  type        = string
  default     = ""
  sensitive   = true
}

variable "slack_signing_secret" {
  description = "Slack signing secret for Agentic AI deployment"
  type        = string
  default     = ""
  sensitive   = true
}

variable "bedrock_model_id" {
  description = "Bedrock model ID for Agentic AI deployment"
  type        = string
  default     = "us.anthropic.claude-3-7-sonnet-20250219-v1:0"
}

variable "vector_bucket_name" {
  description = "S3 bucket name for vector storage (must be created manually before deployment)"
  type        = string
  default     = ""
}

variable "vector_index_name" {
  description = "S3 Vectors index name for troubleshooting knowledge"
  type        = string
  default     = "k8s-troubleshooting"
}
