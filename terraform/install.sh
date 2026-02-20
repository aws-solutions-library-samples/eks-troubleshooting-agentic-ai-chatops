#!/bin/bash

set -e  # Exit on any error

echo "=========================================="
echo "EKS Agentic Troubleshooting Deployment"
echo "=========================================="
echo ""

# Default values
AWS_REGION="${AWS_REGION:-us-east-1}"
ECR_REPO_NAME="eks-agentic-troubleshooting-agent"
VECTOR_INDEX_NAME="k8s-troubleshooting"

echo "Configuration:"
echo "  AWS Region: $AWS_REGION"
echo "  ECR Repository: $ECR_REPO_NAME"
echo ""

# Check if terraform.tfvars exists
if [ -f "terraform.tfvars" ]; then
    echo "Found existing terraform.tfvars file."
    read -p "Do you want to use the existing configuration? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Using existing terraform.tfvars..."
        USE_EXISTING=true
    else
        USE_EXISTING=false
    fi
else
    USE_EXISTING=false
fi

if [ "$USE_EXISTING" = false ]; then
    echo ""
    echo "=========================================="
    echo "Step 1: Setting up prerequisites"
    echo "=========================================="
    
    # Create ECR repository
    echo ""
    echo "Creating ECR repository..."
    if aws ecr describe-repositories --repository-names $ECR_REPO_NAME --region $AWS_REGION >/dev/null 2>&1; then
        echo "ECR repository already exists."
    else
        aws ecr create-repository \
            --repository-name $ECR_REPO_NAME \
            --region $AWS_REGION \
            --image-scanning-configuration scanOnPush=true
        echo "ECR repository created successfully."
    fi
    
    # Get ECR repository URI
    export ECR_REPO_URL=$(aws ecr describe-repositories \
        --repository-names $ECR_REPO_NAME \
        --region $AWS_REGION \
        --query 'repositories[0].repositoryUri' \
        --output text)
    echo "ECR Repository URL: $ECR_REPO_URL"
    
    # Create S3 vector bucket
    echo ""
    echo "Creating S3 vector bucket..."
    export VECTOR_BUCKET="eks-troubleshooting-vectors-$(date +%s)"
    
    if aws s3vectors create-vector-bucket \
        --vector-bucket-name $VECTOR_BUCKET \
        --region $AWS_REGION 2>/dev/null; then
        echo "Vector bucket created: $VECTOR_BUCKET"
        
        # Create S3 Vectors index
        echo "Creating S3 Vectors index..."
        aws s3vectors create-index \
            --vector-bucket-name $VECTOR_BUCKET \
            --index-name $VECTOR_INDEX_NAME \
            --dimension 1024 \
            --data-type float32 \
            --distance-metric cosine \
            --region $AWS_REGION
        echo "Vector index created: $VECTOR_INDEX_NAME"
    else
        echo "Note: S3 Vectors creation failed. You may need to create it manually."
        echo "Please create the bucket and update terraform.tfvars with the bucket name."
        read -p "Enter your S3 vector bucket name (or press Enter to skip): " VECTOR_BUCKET
        if [ -z "$VECTOR_BUCKET" ]; then
            VECTOR_BUCKET="your-vector-bucket-name"
        fi
    fi
    
    # Build and push Docker image
    echo ""
    echo "=========================================="
    echo "Step 2: Building and pushing Docker image"
    echo "=========================================="
    
    cd ../apps/agentic-troubleshooting/
    
    echo "Logging into ECR..."
    aws ecr get-login-password --region $AWS_REGION | \
        docker login --username AWS --password-stdin $ECR_REPO_URL
    
    echo "Building Docker image (this may take a few minutes)..."
    docker build --platform linux/amd64 -t $ECR_REPO_URL:latest .
    
    echo "Pushing image to ECR..."
    docker push $ECR_REPO_URL:latest
    
    cd ../../terraform/
    
    # Collect Slack credentials
    echo ""
    echo "=========================================="
    echo "Step 3: Configuring Slack integration"
    echo "=========================================="
    echo ""
    echo "Please provide your Slack credentials:"
    echo "(Press Enter to skip and configure manually later)"
    echo ""
    
    read -p "Slack Webhook URL (for AlertManager): " SLACK_WEBHOOK_URL
    if [ -z "$SLACK_WEBHOOK_URL" ]; then
        SLACK_WEBHOOK_URL="https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
    fi
    
    read -p "Slack Channel Name (for alerts, e.g., #alerts): " SLACK_CHANNEL_NAME
    if [ -z "$SLACK_CHANNEL_NAME" ]; then
        SLACK_CHANNEL_NAME="#alerts"
    fi
    
    read -p "Slack Bot Token (xoxb-...): " SLACK_BOT_TOKEN
    if [ -z "$SLACK_BOT_TOKEN" ]; then
        SLACK_BOT_TOKEN="xoxb-your-bot-token"
    fi
    
    read -p "Slack App Token (xapp-...): " SLACK_APP_TOKEN
    if [ -z "$SLACK_APP_TOKEN" ]; then
        SLACK_APP_TOKEN="xapp-your-app-token"
    fi
    
    read -p "Slack Signing Secret: " SLACK_SIGNING_SECRET
    if [ -z "$SLACK_SIGNING_SECRET" ]; then
        SLACK_SIGNING_SECRET="your-signing-secret"
    fi
    
    # Generate terraform.tfvars
    echo ""
    echo "Generating terraform.tfvars..."
    cat > terraform.tfvars <<EOF
# EKS Cluster Configuration
name = "eks-agentic-troubleshooting"

# Slack Configuration for AlertManager
slack_webhook_url  = "$SLACK_WEBHOOK_URL"
slack_channel_name = "$SLACK_CHANNEL_NAME"

# Agentic Agent Configuration
agentic_image_repository = "$ECR_REPO_URL"
agentic_image_tag        = "latest"

# Slack Bot Configuration
slack_bot_token      = "$SLACK_BOT_TOKEN"
slack_app_token      = "$SLACK_APP_TOKEN"
slack_signing_secret = "$SLACK_SIGNING_SECRET"

# Amazon Bedrock Configuration
bedrock_model_id = "us.anthropic.claude-3-7-sonnet-20250219-v1:0"

# S3 Vectors Configuration
vector_bucket_name = "$VECTOR_BUCKET"
vector_index_name  = "$VECTOR_INDEX_NAME"
EOF
    
    echo "terraform.tfvars created successfully!"
    echo ""
    echo "Please review and update terraform.tfvars with your actual Slack credentials."
    echo ""
    read -p "Press Enter to continue with Terraform deployment..."
fi

echo ""
echo "=========================================="
echo "Step 4: Deploying infrastructure with Terraform"
echo "=========================================="

echo ""
echo "Initializing Terraform..."
terraform init

echo ""
echo "Step 4.1: Applying VPC module..."
terraform apply -target=module.vpc --auto-approve

echo ""
echo "Step 4.2: Applying EKS cluster..."
terraform apply -target=module.eks --auto-approve

echo ""
echo "Step 4.3: Applying EKS Blueprints Addons (Prometheus, Metrics Server, etc.)..."
terraform apply -target=module.eks_blueprints_addons --auto-approve

echo ""
echo "Step 4.4: Applying Karpenter autoscaler..."
terraform apply -target=module.karpenter -target=helm_release.karpenter --auto-approve

echo ""
echo "Step 4.5: Applying Karpenter default node pool..."
terraform apply -target=helm_release.karpenter_default --auto-approve

echo ""
echo "Step 4.6: Applying agentic troubleshooting agent IAM resources..."
terraform apply \
    -target=aws_iam_policy.eks_mcp_policy \
    -target=aws_iam_role.agentic_agent_role \
    -target=aws_iam_role_policy_attachment.agentic_agent_eks_mcp \
    -target=aws_eks_pod_identity_association.agentic_agent \
    -target=aws_eks_access_entry.agentic_agent \
    -target=aws_eks_access_policy_association.agentic_agent_admin \
    --auto-approve

echo ""
echo "Step 4.7: Applying Kubernetes secrets..."
terraform apply -target=kubernetes_secret.slack_credentials --auto-approve

echo ""
echo "Step 4.8: Applying remaining Terraform configurations..."
terraform apply --auto-approve

echo ""
echo "=========================================="
echo "Installation complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo ""
echo "1. Configure kubectl:"
echo "   aws eks update-kubeconfig --region $AWS_REGION --name \$(terraform output -raw cluster_name)"
echo ""
echo "2. Verify agent deployment:"
echo "   kubectl get pods -n default -l app=k8s-troubleshooting-agent"
echo ""
echo "3. Check agent logs:"
echo "   kubectl logs -n default -l app=k8s-troubleshooting-agent -f"
echo ""
echo "4. Test in Slack:"
echo "   - Add the bot to your Slack channel"
echo "   - Mention the bot with a K8s question"
echo "   - Example: @k8s-agent My pods are crashing with OOMKilled errors"
echo ""
echo "5. Monitor with Prometheus:"
echo "   kubectl port-forward -n kube-prometheus-stack svc/kube-prometheus-stack-prometheus 9090:9090"
echo "   Open http://localhost:9090"
echo ""
