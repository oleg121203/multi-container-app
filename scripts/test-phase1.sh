#!/bin/bash
# ATLAS Phase 1 Infrastructure Test Script
# Tests Kubernetes manifests, storage, networking, and monitoring

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test results tracking
TESTS_PASSED=0
TESTS_FAILED=0

print_header() {
    echo -e "\n${YELLOW}=== $1 ===${NC}"
}

test_passed() {
    echo -e "${GREEN}✅ $1${NC}"
    ((TESTS_PASSED++))
}

test_failed() {
    echo -e "${RED}❌ $1${NC}"
    ((TESTS_FAILED++))
}

print_header "ATLAS Phase 1 Infrastructure Tests"

# Test 1: YAML Syntax Validation
print_header "Test 1: YAML Syntax Validation"
for file in infra/k8s/manual/*.yaml; do
    if python3 -c "import yaml; list(yaml.safe_load_all(open('$file')))" 2>/dev/null; then
        test_passed "$(basename $file) syntax valid"
    else
        test_failed "$(basename $file) syntax invalid"
    fi
done

# Test 2: Kubernetes Resource Validation
print_header "Test 2: Kubernetes Resource Validation"
if command -v kubeval >/dev/null 2>&1; then
    echo "Running kubeval validation..."
    if kubeval infra/k8s/manual/*.yaml >/dev/null 2>&1; then
        test_passed "Kubernetes manifests validation"
    else
        test_failed "Kubernetes manifests validation (network issues may cause false failures)"
    fi
else
    echo "kubeval not available, skipping detailed validation"
fi

# Test 3: Required Files and Structure
print_header "Test 3: Required Files and Structure"
required_files=(
    "infra/k8s/manual/00-namespace-and-config.yaml"
    "infra/k8s/manual/01-todo-database.yaml"
    "infra/k8s/manual/02-todo-app.yaml"
    "infra/k8s/manual/03-tts-services.yaml"
    "infra/k8s/manual/04-prometheus.yaml"
    "infra/k8s/manual/05-grafana.yaml"
    "infra/k8s/manual/07-security-and-limits.yaml"
    "docs/adr/0001-llm2-ollama.md"
    ".github/workflows/atlas-execution-plan.yml"
    ".github/workflows/ci.yml"
)

for file in "${required_files[@]}"; do
    if [[ -f "$file" ]]; then
        test_passed "Required file: $file"
    else
        test_failed "Missing file: $file"
    fi
done

# Test 4: Configuration Completeness
print_header "Test 4: Configuration Completeness"

# Check namespace configuration
if grep -q "name: atlas" infra/k8s/manual/00-namespace-and-config.yaml; then
    test_passed "Namespace 'atlas' configured"
else
    test_failed "Namespace 'atlas' not found"
fi

# Check storage class
if grep -q "name: atlas-storage" infra/k8s/manual/00-namespace-and-config.yaml; then
    test_passed "StorageClass 'atlas-storage' configured"
else
    test_failed "StorageClass 'atlas-storage' not found"
fi

# Check StatefulSet for database
if grep -q "kind: StatefulSet" infra/k8s/manual/01-todo-database.yaml; then
    test_passed "Database StatefulSet configured"
else
    test_failed "Database StatefulSet not found"
fi

# Check monitoring components
if grep -q "name: prometheus" infra/k8s/manual/04-prometheus.yaml; then
    test_passed "Prometheus configured"
else
    test_failed "Prometheus not found"
fi

if grep -q "name: grafana" infra/k8s/manual/05-grafana.yaml; then
    test_passed "Grafana configured"
else
    test_failed "Grafana not found"
fi

# Test 5: Security Configuration
print_header "Test 5: Security Configuration"

# Check NetworkPolicy
if grep -q "kind: NetworkPolicy" infra/k8s/manual/07-security-and-limits.yaml; then
    test_passed "NetworkPolicy configured"
else
    test_failed "NetworkPolicy not found"
fi

# Check ResourceQuota
if grep -q "kind: ResourceQuota" infra/k8s/manual/07-security-and-limits.yaml; then
    test_passed "ResourceQuota configured"
else
    test_failed "ResourceQuota not found"
fi

# Check Secrets
if grep -q "kind: Secret" infra/k8s/manual/01-todo-database.yaml; then
    test_passed "Database secrets configured"
else
    test_failed "Database secrets not found"
fi

# Test 6: Workflow Validation
print_header "Test 6: Workflow Validation"

# Check execution plan workflow
if grep -q "ATLAS Execution Plan" .github/workflows/atlas-execution-plan.yml; then
    test_passed "Execution plan workflow configured"
else
    test_failed "Execution plan workflow not found"
fi

# Check CI workflow
if grep -q "ATLAS CI Pipeline" .github/workflows/ci.yml; then
    test_passed "CI pipeline workflow configured"
else
    test_failed "CI pipeline workflow not found"
fi

# Test 7: Documentation Completeness
print_header "Test 7: Documentation Completeness"

# Check ADR
if grep -q "Ollama" docs/adr/0001-llm2-ollama.md; then
    test_passed "LLM2 Ollama ADR documented"
else
    test_failed "LLM2 Ollama ADR incomplete"
fi

# Check runbook
if [[ -f "docs/runbooks/infrastructure-deployment-recovery.md" ]]; then
    test_passed "Infrastructure recovery runbook exists"
else
    test_failed "Infrastructure recovery runbook missing"
fi

# Final Results
print_header "Test Results Summary"
echo -e "Tests Passed: ${GREEN}$TESTS_PASSED${NC}"
echo -e "Tests Failed: ${RED}$TESTS_FAILED${NC}"

if [[ $TESTS_FAILED -eq 0 ]]; then
    echo -e "\n${GREEN}🎉 All tests passed! Phase 1 infrastructure is ready.${NC}"
    echo -e "\n${YELLOW}Next steps:${NC}"
    echo "1. Deploy to Kubernetes cluster: kubectl apply -f infra/k8s/manual/"
    echo "2. Verify services: kubectl get pods -n atlas"
    echo "3. Access Grafana: kubectl port-forward -n atlas svc/grafana 3000:3000"
    echo "4. Run Phase 2 tests: ./scripts/test-phase2.sh"
    exit 0
else
    echo -e "\n${RED}❌ Some tests failed. Please fix the issues above.${NC}"
    exit 1
fi