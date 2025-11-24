#!/bin/bash

echo "=== Checking Langfuse Deployment Status ==="
echo ""

echo "Pods:"
kubectl get pods -n langfuse
echo ""

echo "PVCs:"
kubectl get pvc -n langfuse
echo ""

echo "Services:"
kubectl get svc -n langfuse
echo ""

echo "PostgreSQL Pod Logs (last 20 lines):"
kubectl logs -n langfuse -l app.kubernetes.io/name=postgresql --tail=20
echo ""

echo "Langfuse Web Pod Logs (last 20 lines):"
kubectl logs -n langfuse -l app.kubernetes.io/name=langfuse,app.kubernetes.io/component=web --tail=20
