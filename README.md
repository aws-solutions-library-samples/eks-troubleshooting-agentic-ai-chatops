# Guidance for Troubleshooting of Amazon EKS using Agentic AI workflow on AWS

This project provides two different approaches for troubleshooting EKS (Elastic Kubernetes Service) issues:

1. **Strands-based AI Agentic workflow Troubleshooting**: An intelligent agent using AWS Strands Agent framework with EKS MCP server integration for real-time troubleshooting

Both solutions are deployed using Terraform, which provisions the necessary AWS resources including EKS cluster, monitoring tools, and application-specific infrastructure.

## Project Structure

```
├── apps/                           # Application code
│   ├── agentic-troubleshooting/   # Strands-based agentic troubleshooting agent
│   │   ├── src/agents/            # Strands agent implementations
│   │   ├── src/tools/             # EKS MCP tools integration
│   │   ├── helm/                  # Kubernetes deployment charts
│   │   └── main.py                # Strands agent entry point
├── terraform/                      # Infrastructure as Code
│   ├── main.tf                    # Main EKS cluster configuration
│   ├── agentic.tf                 # Strands agent deployment resources
│   ├── modules/                   # Terraform modules
│   ├── variables.tf               # Terraform variables
│   └── outputs.tf                 # Terraform outputs
├── static/                        # Static assets
└── demo/                          # Demo scripts and manifests
```

## Prerequisites

Before running this project, make sure you have the following installed:

- [Terraform](https://www.terraform.io/downloads.html)
- [AWS CLI](https://aws.amazon.com/cli/)
- [Python 3.8+](https://www.python.org/downloads/)
- [Docker](https://www.docker.com/) (for agentic deployment)
- [Helm](https://helm.sh/) (for agentic deployment)

### Slack Configuration (Required)

#### For Both Deployments:
1. **Slack Webhook** (Alert Manager notifications):
   - Create incoming webhook in your Slack workspace
   - Note the webhook URL and target channel name

#### For Strands Agentic Deployment Only:
2. **Slack Bot Configuration**:
   - Create a Slack app with the following **Bot Token Scopes**:
     - `app_mentions:read` - View messages mentioning the bot
     - `channels:history` - View messages in public channels
     - `channels:read` - View basic channel information
     - `chat:write` - Send messages as the bot
     - `groups:history` - View messages in private channels
     - `groups:read` - View basic private channel information
     - `im:history` - View direct messages
     - `im:read` - View basic DM information
   
   - **Event Subscriptions** (enable these events):
     - `app_mention` - Bot mentions
     - `message.channels` - Channel messages
     - `message.groups` - Private channel messages
     - `message.im` - Direct messages
   
   - **Enable Socket Mode** for real-time events
   - Note the Bot Token (`xoxb-...`), App Token (`xapp-...`), and Signing Secret

## Deployment Options

### Option 1: Strands-based Agentic AI Workflow Troubleshooting Deployment

The agentic approach uses the AWS Strands Agent framework with EKS MCP server integration for intelligent, real-time troubleshooting.

```mermaid
graph LR
    U[User] --> S[Slack Interface]
    S --> OA[K8s Orchestrator Agent]
    
    OA --> MA[Memory Agent]
    OA --> KS[K8s Specialist]
    
    MA --> S3V[S3 Vectors DB]
    KS --> EKS[EKS MCP Server]
    KS --> K8S[Local K8s Tools]
    
    EKS --> AWS[AWS EKS Cluster]
    K8S --> KUBE[Kubernetes API]
    
    style U fill:#1976d2,color:#fff
    style S fill:#f57c00,color:#fff
    style OA fill:#ff6f00,color:#fff
    style MA fill:#7b1fa2,color:#fff
    style KS fill:#388e3c,color:#fff
    style EKS fill:#d32f2f,color:#fff
    style S3V fill:#9c27b0,color:#fff
```

#### Setup Steps

1. **Set your AWS region:**
   ```bash
   export AWS_REGION="us-east-1"  # Change to your preferred region
   ```

2. **Create ECR repository manually:**
   ```bash
   # Create ECR repository
   aws ecr create-repository --repository-name eks-llm-troubleshooting-agentic-agent --region $AWS_REGION
   
   # Get the repository URI
   export ECR_REPO_URL=$(aws ecr describe-repositories --repository-names eks-llm-troubleshooting-agentic-agent --region $AWS_REGION --query 'repositories[0].repositoryUri' --output text)
   echo "ECR Repository URL: $ECR_REPO_URL"
   ```

3. **Create S3 vector bucket and index:**
   ```bash
   # Create S3 vector bucket with unique name
   export VECTOR_BUCKET="eks-llm-troubleshooting-vector-storage-$(date +%s)"
   aws s3vectors create-vector-bucket \
     --vector-bucket-name $VECTOR_BUCKET \
     --region $AWS_REGION
   
   # Create S3 Vectors index with 1024 dimensions
   aws s3vectors create-index \
     --vector-bucket-name $VECTOR_BUCKET \
     --index-name "k8s-troubleshooting" \
     --dimension 1024 \
     --data-type float32 \
     --distance-metric cosine \
     --region $AWS_REGION
   
   echo "Vector bucket: $VECTOR_BUCKET"
   echo "Index name: k8s-troubleshooting"
   ```

4. **Build and push the Docker images for Agents :**
   ```bash
   cd apps/agentic-troubleshooting/
   
   # Login to ECR
   aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_REPO_URL
   
   # Build and tag the image
   docker build --platform linux/amd64 -t $ECR_REPO_URL .
   
   # Push to ECR
   docker push $ECR_REPO_URL
   ```

5. **Configure Terraform variables:**
   Create `terraform/terraform.tfvars` file (replace with your actual values):
   ```hcl
   deployment_type = "agentic"
   agentic_image_repository = "your-account.dkr.ecr.us-east-1.amazonaws.com/eks-llm-troubleshooting-agentic-agent"
   agentic_image_tag = "latest"
   slack_webhook_url = "https://hooks.slack.com/services/[YOUR-WEBHOOK]"
   slack_channel_name = "alert-manager-alerts"
   slack_bot_token = "xoxb-your-bot-token"
   slack_app_token = "xapp-your-app-token"
   slack_signing_secret = "your-signing-secret"
   bedrock_model_id = "us.anthropic.claude-3-7-sonnet-20250219-v1:0"
   vector_bucket_name = "eks-llm-troubleshooting-vector-storage-1234567890"  # Use the bucket created above
   vector_index_name = "k8s-troubleshooting"
   ```

6. **Deploy infrastructure:**
   ```bash
   cd terraform/
   terraform init
   terraform apply -auto-approve
   ```

The agentic deployment will automatically:
- Create IAM roles with EKS MCP permissions
- Set up Pod Identity associations
- Deploy the Helm chart with the troubleshooting agent
- Configure Slack integration


## Key Features

### Strands-based Agentic AI workflow Troubleshooting
- Multi-agent orchestration with EKS MCP integration
- S3 Vectors storage for tribal knowledge
- Slack bot integration with Pod Identity security
- Real-time cluster monitoring and troubleshooting

## Configuration

### Terraform Variables
- **deployment_type**: `"rag"` (default) or `"agentic"`
- **name**: Project name (default: `"eks-llm-troubleshooting"`)
- **slack_webhook_url**: Slack webhook for alerts (both deployments)
- **slack_channel_name**: Slack channel name (both deployments)
- **agentic_image_repository**: ECR repository for agent image (Agentic only)
- **slack_bot_token**: Slack bot token (Agentic only)
- **bedrock_model_id**: Bedrock model identifier (Agentic only)
- **vector_bucket_name**: S3 vector bucket name (Agentic only)

## Testing

<!--
### RAG Deployment
1. Deploy problematic pods: `./provision-delete-error-pods.sh -p db-migration`
2. Access Gradio interface at `http://localhost:7860/`
3. Query the chatbot about EKS issues
-->

### Strands Agentic AI Workflow
See [Demo Script](demo/demo-script.md) for complete testing instructions and example scenarios.
<TODO> Add instructions for testing Slack based ChatOps scenario with Agentic AI workflow.

## Cleanup

1. **Destroy infrastructure:**
   ```bash
   cd terraform/
   terraform destroy --auto-approve
   ```

2. **Clean up additional resources** (Agentic only):
   ```bash
   # Delete ECR repository
   aws ecr delete-repository --repository-name eks-llm-troubleshooting-agentic-agent --force --region $AWS_REGION
   
   # Delete S3 vector bucket (if created)
   aws s3vectors delete-index --vector-bucket-name $VECTOR_BUCKET --index-name k8s-troubleshooting --region $AWS_REGION
   aws s3vectors delete-vector-bucket --vector-bucket-name $VECTOR_BUCKET --region $AWS_REGION
   ```

## Architecture

### RAG Architecture
- EKS Cluster with Fluent Bit → Kinesis → OpenSearch → Gradio Interface
- Bedrock for AI-powered responses

### Strands-based Agentic Architecture
- Multi-agent system with EKS MCP integration
- S3 Vectors for knowledge storage
- Slack bot with Pod Identity security

## Troubleshooting

### Common Issues
- **Access Denied (Bedrock)**: Ensure your AWS account has access to the specified Bedrock model
- **Image Pull Errors**: Verify ECR repository exists and credentials are correct
- **Slack Integration**: Check bot tokens and permissions
- **Pod Identity**: Ensure EKS Pod Identity Agent is enabled

## Acknowledgments

This project uses:
<!-- - [Gradio](https://www.gradio.app/) for the user interface -->
- [Terraform AWS EKS Blueprints](https://github.com/aws-ia/terraform-aws-eks-blueprints) for infrastructure
- [AWS Strands Agent Framework](https://github.com/aws/strands) for multi-agent orchestration (Agentic deployment)
- [EKS MCP Server](https://github.com/aws/eks-mcp-server) for Kubernetes integration via Model Context Protocol (Agentic deployment)

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the LICENSE file.
