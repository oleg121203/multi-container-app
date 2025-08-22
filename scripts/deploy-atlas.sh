#!/bin/bash
# ATLAS Deployment and Verification Script
# Deploys ATLAS infrastructure to Kubernetes and verifies all components

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_header() {
    echo -e "\n${BLUE}=== $1 ===${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_header "ATLAS Infrastructure Deployment"

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    print_error "kubectl is not installed. Please install kubectl first."
    exit 1
fi

# Check if we can connect to Kubernetes cluster
if ! kubectl cluster-info &> /dev/null; then
    print_error "Cannot connect to Kubernetes cluster. Please ensure cluster is running and kubeconfig is set."
    print_warning "For local testing, you can use: kind create cluster --name atlas"
    exit 1
fi

print_success "Kubernetes cluster connection verified"

# Deploy namespace and configuration first
print_header "Deploying Core Configuration"
kubectl apply -f infra/k8s/manual/00-namespace-and-config.yaml
print_success "Namespace and configuration deployed"

# Deploy database
print_header "Deploying Database (MongoDB)"
kubectl apply -f infra/k8s/manual/01-todo-database.yaml
print_success "Database StatefulSet deployed"

# Deploy application
print_header "Deploying Applications"
kubectl apply -f infra/k8s/manual/02-todo-app.yaml
kubectl apply -f infra/k8s/manual/03-tts-services.yaml
print_success "Applications deployed"

# Deploy monitoring
print_header "Deploying Monitoring Stack"
kubectl apply -f infra/k8s/manual/04-prometheus.yaml
kubectl apply -f infra/k8s/manual/05-grafana.yaml
kubectl apply -f infra/k8s/manual/06-grafana-dashboards.yaml
print_success "Monitoring stack deployed"

# Deploy security and limits
print_header "Applying Security Policies"
kubectl apply -f infra/k8s/manual/07-security-and-limits.yaml
print_success "Security policies applied"

# Deploy vector database and cache
print_header "Deploying Vector Database and Cache"
kubectl apply -f infra/k8s/manual/08-vector-database.yaml
print_success "Vector database (Qdrant) and Redis cache deployed"

# Deploy Ollama service
print_header "Deploying Ollama Service"
kubectl apply -f infra/k8s/manual/09-ollama.yaml
print_success "Ollama service deployed"

# Deploy ATLAS agents
print_header "Deploying ATLAS Agents"
echo "Note: Ensure secrets are configured in 11-atlas-secrets.yaml before deploying agents"
if [ -f "infra/k8s/manual/11-atlas-secrets.yaml" ]; then
    kubectl apply -f infra/k8s/manual/11-atlas-secrets.yaml
    print_success "ATLAS secrets applied"
else
    print_warning "ATLAS secrets not found. Copy 11-atlas-secrets-template.yaml to 11-atlas-secrets.yaml and configure API keys"
fi

kubectl apply -f infra/k8s/manual/10-atlas-agents.yaml
print_success "ATLAS agents deployed"

# Wait for pods to be ready
print_header "Waiting for Pods to Start"
echo "Waiting for pods in atlas namespace to be ready..."
kubectl wait --for=condition=ready pod -l app.kubernetes.io/part-of=atlas-system -n atlas --timeout=300s || {
    print_warning "Some pods may still be starting. Check status manually with: kubectl get pods -n atlas"
}

# Show deployment status
print_header "Deployment Status"
echo "Pods:"
kubectl get pods -n atlas
echo ""
echo "Services:"
kubectl get svc -n atlas
echo ""
echo "PVCs:"
kubectl get pvc -n atlas

print_header "Access Information"
echo -e "${YELLOW}To access services:${NC}"
echo "📊 Grafana Dashboard:"
echo "   kubectl port-forward -n atlas svc/grafana 3000:3000"
echo "   Open: http://localhost:3000 (admin/admin)"
echo ""
echo "📈 Prometheus:"
echo "   kubectl port-forward -n atlas svc/prometheus 9090:9090"
echo "   Open: http://localhost:9090"
echo ""
echo "📱 Todo App:"
echo "   kubectl port-forward -n atlas svc/todo-app 3001:3000"
echo "   Open: http://localhost:3001"
echo ""
echo "🔊 MCP TTS:"
echo "   kubectl port-forward -n atlas svc/mcp-tts 4004:4004"
echo ""

print_header "Next Steps"
echo "✨ Phase 1 infrastructure is deployed!"
echo ""
echo "🔍 Verify deployment:"
echo "   ./scripts/test-phase1.sh"
echo ""
echo "📊 Monitor with Grafana:"
echo "   kubectl port-forward -n atlas svc/grafana 3000:3000 &"
echo "   open http://localhost:3000"
echo ""
echo "🚀 Proceed to Phase 2:"
echo "   gh workflow run atlas-execution-plan.yml -f phase=phase2"

print_success "ATLAS Phase 1 deployment complete!"