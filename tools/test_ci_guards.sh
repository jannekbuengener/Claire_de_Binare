#!/bin/bash
# tools/test_ci_guards.sh
# Tests the CI guard logic for STUB mode protection.

set -u

# Returns 0 if guard allows the run, 1 if guard blocks (FAIL)
evaluate_guard() {
    local mode=$1
    local ref=$2
    local event=$3
    local allow_stub=$4
    local labels=$5

    if [[ "$mode" == "STUB" ]]; then
        if [[ "$ref" == "refs/heads/main" ]]; then return 1; fi
        if [[ "$ref" == refs/heads/release/* ]]; then return 1; fi
        if [[ "$ref" == refs/heads/soak/* ]]; then return 1; fi
        if [[ "$ref" == refs/heads/shadow/* ]]; then return 1; fi
        if [[ "$event" == "schedule" ]]; then return 1; fi

        # Opt-in check
        local opt_in=0
        if [[ "$allow_stub" == "true" ]]; then opt_in=1; fi
        if [[ "$labels" =~ "allow-stub" ]]; then opt_in=1; fi

        if [[ "$opt_in" == "0" ]]; then
            return 1 # Blocked because no opt-in
        fi
    fi

    return 0 # Allowed
}

test_case() {
    local expected=$1 # "ALLOW" or "BLOCK"
    local mode=$2
    local ref=$3
    local event=$4
    local allow_stub=$5
    local labels=$6

    evaluate_guard "$mode" "$ref" "$event" "$allow_stub" "$labels"
    local result=$?

    local actual="ALLOW"
    if [[ "$result" == "1" ]]; then actual="BLOCK"; fi

    if [[ "$actual" == "$expected" ]]; then
        echo "✅ [OK]    $mode | $ref | $event | stub=$allow_stub | labels=[$labels] -> $actual"
    else
        echo "❌ [ERROR] $mode | $ref | $event | stub=$allow_stub | labels=[$labels] -> Expected $expected, got $actual"
        return 1
    fi
    return 0
}

echo "Running CI Guard Logic Tests..."
echo "--------------------------------------------------------------------------------"
errs=0

test_case "BLOCK" "STUB" "refs/heads/main" "push" "false" "" || errs=$((errs+1))
test_case "BLOCK" "STUB" "refs/heads/release/v1" "push" "false" "" || errs=$((errs+1))
test_case "BLOCK" "STUB" "refs/heads/soak/test" "push" "false" "" || errs=$((errs+1))
test_case "BLOCK" "STUB" "refs/heads/shadow/v1" "push" "false" "" || errs=$((errs+1))
test_case "BLOCK" "STUB" "refs/heads/any" "schedule" "false" "" || errs=$((errs+1))
test_case "BLOCK" "STUB" "refs/heads/feat/xyz" "push" "false" "" || errs=$((errs+1))
test_case "ALLOW" "STUB" "refs/heads/feat/xyz" "workflow_dispatch" "true" "" || errs=$((errs+1))
test_case "ALLOW" "STUB" "refs/heads/feat/xyz" "pull_request" "false" "allow-stub" || errs=$((errs+1))
test_case "BLOCK" "STUB" "refs/heads/main" "workflow_dispatch" "true" "" || errs=$((errs+1))
test_case "ALLOW" "REAL" "refs/heads/main" "push" "false" "" || errs=$((errs+1))

echo "--------------------------------------------------------------------------------"
if [ $errs -eq 0 ]; then
    echo "Summary: ALL TESTS PASSED"
else
    echo "Summary: $errs TESTS FAILED"
fi
