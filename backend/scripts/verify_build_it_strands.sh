#!/bin/bash
# Comprehensive verification script for BUILD_IT_STRANDS
# Runs all test suites and generates a verification report

set -e

echo "================================================================================"
echo "BUILD_IT_STRANDS COMPREHENSIVE VERIFICATION"
echo "================================================================================"
echo ""

TESTS_PASSED=0
TESTS_FAILED=0
SKIPPED_TESTS=0

run_test() {
    local test_name=$1
    local test_script=$2
    
    echo "Running: $test_name"
    if python "$test_script" > /tmp/test_output.log 2>&1; then
        echo "  ✓ PASSED"
        ((TESTS_PASSED++))
    else
        echo "  ✗ FAILED"
        echo "    See /tmp/test_output.log for details"
        ((TESTS_FAILED++))
    fi
    echo ""
}

echo "PHASE 1: Provider Initialization"
echo "--------"
run_test "Provider initialization" "scripts/test_provider_initialization.py"

echo "PHASE 2: LocalStack & Seed Data Setup"
echo "--------"
run_test "LocalStack initialization" "scripts/test_localstack_init.py"
run_test "Seed household data" "scripts/test_seed_household.py"

echo "PHASE 3: Strands Runtime"
echo "--------"
run_test "Strands runtime integration" "scripts/test_strands_runtime.py"

echo "PHASE 5: Cedar Authorization"
echo "--------"
run_test "Cedar auth/authz integration" "scripts/test_cedar_integration.py"

echo "PHASE 6: End-to-End Workflows"
echo "--------"
run_test "E2E workflows" "scripts/test_e2e_workflows.py"

echo "PHASE 2: Ollama Integration (Optional)"
echo "--------"
if python "shared/providers/test_ollama_integration.py" > /tmp/test_output.log 2>&1; then
    echo "  ✓ Ollama available and configured"
    ((TESTS_PASSED++))
else
    echo "  ⚠ Ollama not available (expected if not installed)"
    ((SKIPPED_TESTS++))
fi
echo ""

echo "================================================================================"
echo "VERIFICATION SUMMARY"
echo "================================================================================"
echo ""
echo "Tests Passed:  $TESTS_PASSED"
echo "Tests Failed:  $TESTS_FAILED"
echo "Tests Skipped: $SKIPPED_TESTS"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo "✓ BUILD_IT_STRANDS VERIFICATION COMPLETE"
    echo ""
    echo "Next steps:"
    echo "  1. Docker: docker-compose up localstack"
    echo "  2. Init:   python backend/scripts/init_localstack_db.py"
    echo "  3. Seed:   python backend/scripts/seed_household.py"
    echo "  4. Start:  python backend/local_dev_server.py"
    echo "  5. Test:   curl http://localhost:5000/status"
    echo ""
    exit 0
else
    echo "✗ VERIFICATION FAILED"
    echo "Failed tests: $TESTS_FAILED"
    exit 1
fi
