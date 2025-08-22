#!/bin/bash
set -e

# ATLAS Phase 3 Comprehensive Validation Suite
# Executes both infrastructure validation and code quality testing
# to provide 100% validation coverage as described in the problem statement

echo "🧪 ATLAS Phase 3 Comprehensive Validation Suite"
echo "=============================================="
echo ""
echo "This suite performs comprehensive testing and validation of Phase 3 implementation"
echo "including infrastructure validation, code quality testing, and production readiness assessment."
echo ""

# Set up logging
TIMESTAMP=$(date "+%Y-%m-%d_%H-%M-%S")
COMPREHENSIVE_LOG="test-results/comprehensive-validation-$TIMESTAMP.log"
mkdir -p test-results/

# Initialize counters
TOTAL_INFRASTRUCTURE_TESTS=0
TOTAL_CODE_TESTS=0
TOTAL_VALIDATION_TESTS=0

echo "📊 Phase 1: Infrastructure Validation (validate-phase3.sh)"
echo "========================================================="
echo ""

# Run infrastructure validation and capture results
./scripts/validate-phase3.sh > temp_validation.log 2>&1
VALIDATION_EXIT_CODE=$?

# Extract test counts from validation log
VALIDATION_TESTS=$(grep "Total Tests:" temp_validation.log | awk '{print $3}' || echo "0")
VALIDATION_PASSED=$(grep "Passed:" temp_validation.log | awk '{print $2}' || echo "0")
VALIDATION_FAILED=$(grep "Failed:" temp_validation.log | awk '{print $2}' || echo "0")

TOTAL_INFRASTRUCTURE_TESTS=$VALIDATION_TESTS

echo "Infrastructure Validation Results:"
echo "  - Total Tests: $VALIDATION_TESTS"
echo "  - Passed: $VALIDATION_PASSED"
echo "  - Failed: $VALIDATION_FAILED"
echo ""

# Append validation log to comprehensive log
cat temp_validation.log >> "$COMPREHENSIVE_LOG"
rm temp_validation.log

echo "📊 Phase 2: Code Quality Testing (test-phase3.sh)"
echo "================================================="
echo ""

# Run code quality testing and capture results
./scripts/test-phase3.sh > temp_testing.log 2>&1
TESTING_EXIT_CODE=$?

# Extract test counts from testing log
CODE_TESTS=$(grep "Total Tests:" temp_testing.log | awk '{print $3}' || echo "0")
CODE_PASSED=$(grep "Passed:" temp_testing.log | awk '{print $2}' || echo "0")
CODE_FAILED=$(grep "Failed:" temp_testing.log | awk '{print $2}' || echo "0")

TOTAL_CODE_TESTS=$CODE_TESTS

echo "Code Quality Testing Results:"
echo "  - Total Tests: $CODE_TESTS"
echo "  - Passed: $CODE_PASSED"
echo "  - Failed: $CODE_FAILED"
echo ""

# Append testing log to comprehensive log
echo "" >> "$COMPREHENSIVE_LOG"
echo "===== CODE QUALITY TESTING RESULTS =====" >> "$COMPREHENSIVE_LOG"
cat temp_testing.log >> "$COMPREHENSIVE_LOG"
rm temp_testing.log

echo "📊 Phase 3: Production Readiness Assessment"
echo "==========================================="
echo ""

# Additional production readiness checks
PRODUCTION_TESTS=0
PRODUCTION_PASSED=0

# Check for required documentation
if [ -f "VALIDATION_SUMMARY.md" ]; then
    echo "✅ PASS: Production Documentation - VALIDATION_SUMMARY.md exists"
    PRODUCTION_PASSED=$((PRODUCTION_PASSED + 1))
else
    echo "❌ FAIL: Production Documentation - VALIDATION_SUMMARY.md missing"
fi
PRODUCTION_TESTS=$((PRODUCTION_TESTS + 1))

if [ -f "PHASE4_PLANNING.md" ]; then
    echo "✅ PASS: Phase 4 Planning - PHASE4_PLANNING.md exists"
    PRODUCTION_PASSED=$((PRODUCTION_PASSED + 1))
else
    echo "❌ FAIL: Phase 4 Planning - PHASE4_PLANNING.md missing"
fi
PRODUCTION_TESTS=$((PRODUCTION_TESTS + 1))

# Check for demo script
if [ -f "scripts/demo-phase3.py" ]; then
    echo "✅ PASS: Demo Infrastructure - demo-phase3.py exists"
    PRODUCTION_PASSED=$((PRODUCTION_PASSED + 1))
else
    echo "❌ FAIL: Demo Infrastructure - demo-phase3.py missing"
fi
PRODUCTION_TESTS=$((PRODUCTION_TESTS + 1))

# Check for setup script
if [ -f "scripts/setup-phase3.sh" ] && [ -x "scripts/setup-phase3.sh" ]; then
    echo "✅ PASS: Setup Automation - setup-phase3.sh exists and is executable"
    PRODUCTION_PASSED=$((PRODUCTION_PASSED + 1))
else
    echo "❌ FAIL: Setup Automation - setup-phase3.sh missing or not executable"
fi
PRODUCTION_TESTS=$((PRODUCTION_TESTS + 1))

# Check Docker Compose file
if [ -f "compose.yaml" ]; then
    echo "✅ PASS: Container Orchestration - compose.yaml exists"
    PRODUCTION_PASSED=$((PRODUCTION_PASSED + 1))
else
    echo "❌ FAIL: Container Orchestration - compose.yaml missing"
fi
PRODUCTION_TESTS=$((PRODUCTION_TESTS + 1))

# Check for environment example
if [ -f ".env.example" ]; then
    echo "✅ PASS: Environment Configuration - .env.example exists"
    PRODUCTION_PASSED=$((PRODUCTION_PASSED + 1))
else
    echo "❌ FAIL: Environment Configuration - .env.example missing"
fi
PRODUCTION_TESTS=$((PRODUCTION_TESTS + 1))

TOTAL_VALIDATION_TESTS=$PRODUCTION_TESTS

echo ""
echo "Production Readiness Results:"
echo "  - Total Tests: $PRODUCTION_TESTS"
echo "  - Passed: $PRODUCTION_PASSED"
echo "  - Failed: $((PRODUCTION_TESTS - PRODUCTION_PASSED))"
echo ""

# Calculate comprehensive totals
GRAND_TOTAL=$((TOTAL_INFRASTRUCTURE_TESTS + TOTAL_CODE_TESTS + TOTAL_VALIDATION_TESTS))
GRAND_PASSED=$((VALIDATION_PASSED + CODE_PASSED + PRODUCTION_PASSED))
GRAND_FAILED=$((VALIDATION_FAILED + CODE_FAILED + PRODUCTION_TESTS - PRODUCTION_PASSED))

echo "🎉 Comprehensive Validation Summary"
echo "==================================="
echo ""
echo "Infrastructure Validation: $TOTAL_INFRASTRUCTURE_TESTS tests ($VALIDATION_PASSED passed, $VALIDATION_FAILED failed)"
echo "Code Quality Testing:      $TOTAL_CODE_TESTS tests ($CODE_PASSED passed, $CODE_FAILED failed)"
echo "Production Readiness:      $TOTAL_VALIDATION_TESTS tests ($PRODUCTION_PASSED passed, $((PRODUCTION_TESTS - PRODUCTION_PASSED)) failed)"
echo ""
echo "🏆 GRAND TOTAL: $GRAND_TOTAL tests"
echo "   ✅ Passed: $GRAND_PASSED"
echo "   ❌ Failed: $GRAND_FAILED"
echo ""

# Calculate success percentage
if [ "$GRAND_TOTAL" -gt 0 ]; then
    SUCCESS_PERCENTAGE=$(( (GRAND_PASSED * 100) / GRAND_TOTAL ))
    echo "📊 Success Rate: $SUCCESS_PERCENTAGE%"
else
    SUCCESS_PERCENTAGE=0
fi

# Write summary to comprehensive log
{
    echo ""
    echo "===== COMPREHENSIVE VALIDATION SUMMARY ====="
    echo "Validation Date: $(date)"
    echo "Infrastructure Tests: $TOTAL_INFRASTRUCTURE_TESTS ($VALIDATION_PASSED passed)"
    echo "Code Quality Tests: $TOTAL_CODE_TESTS ($CODE_PASSED passed)"
    echo "Production Readiness Tests: $TOTAL_VALIDATION_TESTS ($PRODUCTION_PASSED passed)"
    echo "GRAND TOTAL: $GRAND_TOTAL tests"
    echo "SUCCESS RATE: $SUCCESS_PERCENTAGE%"
} >> "$COMPREHENSIVE_LOG"

echo ""
echo "📝 Comprehensive validation log saved to: $COMPREHENSIVE_LOG"
echo ""

# Determine overall result
if [ "$GRAND_FAILED" -eq 0 ] && [ "$VALIDATION_EXIT_CODE" -eq 0 ] && [ "$TESTING_EXIT_CODE" -eq 0 ]; then
    echo "🎉 ATLAS Phase 3 Comprehensive Validation: PASSED"
    echo "All $GRAND_TOTAL validation tests passed successfully!"
    echo "Phase 3 is ready for production deployment and Phase 4 development."
    exit 0
else
    echo "⚠️  ATLAS Phase 3 Comprehensive Validation: COMPLETED WITH ISSUES"
    echo "$GRAND_FAILED out of $GRAND_TOTAL tests failed or have issues."
    echo "Please review the comprehensive log for details."
    exit 1
fi