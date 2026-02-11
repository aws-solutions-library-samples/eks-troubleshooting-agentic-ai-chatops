#!/bin/bash

# Add Langfuse Helm repo
helm repo add langfuse https://langfuse.github.io/langfuse-k8s
helm repo update

# Create namespace (ignore if exists)
kubectl create namespace langfuse --dry-run=client -o yaml | kubectl apply -f -

# Install Langfuse with required values
helm upgrade --install langfuse langfuse/langfuse -f values.yaml -n langfuse