#!/bin/bash

# HestAI MCP Server - Code Quality Checks
# This script runs all required linting and testing checks before committing changes.
# ALL checks must pass 100% for CI/CD to succeed.

set -e  # Exit on any error

echo "🔍 Running Code Quality Checks for HestAI MCP Server"
echo "================================================="

# Function to get main repo path if we're in a worktree
get_main_repo_path() {
    if [[ -f ".git" ]]; then
        # We're in a worktree - .git is a file pointing to main repo
        local gitdir=$(cat .git | sed 's/gitdir: //')
        # gitdir looks like: /path/to/main/.git/worktrees/worktree-name
        # We need: /path/to/main
        echo "$gitdir" | sed 's|/.git/worktrees/.*||'
    fi
}

# Function to create minimal venv for quality checks (no MCP registration)
create_minimal_venv() {
    echo "📦 Creating minimal venv for quality checks..."

    # Find Python
    local python_cmd=""
    for cmd in python3.12 python3.13 python3.11 python3.10 python3 python; do
        if command -v "$cmd" &> /dev/null; then
            local version=$($cmd --version 2>&1)
            if [[ $version =~ Python\ 3\.([0-9]+) ]]; then
                local minor=${BASH_REMATCH[1]}
                if [[ $minor -ge 10 ]]; then
                    python_cmd="$cmd"
                    break
                fi
            fi
        fi
    done

    if [[ -z "$python_cmd" ]]; then
        echo "❌ Python 3.10+ not found"
        return 1
    fi

    # Create venv
    $python_cmd -m venv .hestai_venv

    # Install minimal dependencies
    .hestai_venv/bin/pip install -q -r requirements.txt

    echo "✅ Minimal venv created"
    return 0
}

# Determine Python command
PYTHON_CMD=""
PIP_CMD=""

# Option 1: Local venv exists
if [[ -f ".hestai_venv/bin/python" ]]; then
    PYTHON_CMD=".hestai_venv/bin/python"
    PIP_CMD=".hestai_venv/bin/pip"
    echo "✅ Using local venv"

# Option 2: Activated virtual environment
elif [[ -n "$VIRTUAL_ENV" ]]; then
    PYTHON_CMD="python"
    PIP_CMD="pip"
    echo "✅ Using activated virtual environment: $VIRTUAL_ENV"

# Option 3: Check if we're in a worktree and can use main repo's venv
elif [[ -f ".git" ]]; then
    MAIN_REPO=$(get_main_repo_path)
    if [[ -n "$MAIN_REPO" ]] && [[ -f "$MAIN_REPO/.hestai_venv/bin/python" ]]; then
        PYTHON_CMD="$MAIN_REPO/.hestai_venv/bin/python"
        PIP_CMD="$MAIN_REPO/.hestai_venv/bin/pip"
        echo "✅ Using main repo venv (worktree mode): $MAIN_REPO/.hestai_venv"
    fi
fi

# Option 4: Create minimal venv if nothing found
if [[ -z "$PYTHON_CMD" ]]; then
    echo "⚠️  No virtual environment found"
    echo "   Creating minimal venv for quality checks..."
    if create_minimal_venv; then
        PYTHON_CMD=".hestai_venv/bin/python"
        PIP_CMD=".hestai_venv/bin/pip"
    else
        echo "❌ Failed to create venv!"
        echo "Please run: ./run-server.sh first to set up the environment"
        exit 1
    fi
fi
echo ""

# Determine venv bin directory (local or main repo)
VENV_BIN_DIR=""
if [[ -d ".hestai_venv/bin" ]]; then
    VENV_BIN_DIR=".hestai_venv/bin"
elif [[ -n "$MAIN_REPO" ]] && [[ -d "$MAIN_REPO/.hestai_venv/bin" ]]; then
    VENV_BIN_DIR="$MAIN_REPO/.hestai_venv/bin"
fi

# Check and install dev dependencies if needed
echo "🔍 Checking development dependencies..."
DEV_DEPS_NEEDED=false

# Check each dev dependency
for tool in ruff black isort pytest; do
    # Check if tool exists in venv or in PATH
    if [[ -n "$VENV_BIN_DIR" ]] && [[ -f "$VENV_BIN_DIR/$tool" ]]; then
        continue
    elif command -v $tool &> /dev/null; then
        continue
    else
        DEV_DEPS_NEEDED=true
        break
    fi
done

if [ "$DEV_DEPS_NEEDED" = true ]; then
    echo "📦 Installing development dependencies..."
    $PIP_CMD install -q -r requirements-dev.txt
    echo "✅ Development dependencies installed"
else
    echo "✅ Development dependencies already installed"
fi

# Set tool paths (prefer venv tools, fall back to system)
if [[ -n "$VENV_BIN_DIR" ]] && [[ -f "$VENV_BIN_DIR/ruff" ]]; then
    RUFF="$VENV_BIN_DIR/ruff"
    BLACK="$VENV_BIN_DIR/black"
    ISORT="$VENV_BIN_DIR/isort"
    PYTEST="$VENV_BIN_DIR/pytest"
else
    RUFF="ruff"
    BLACK="black"
    ISORT="isort"
    PYTEST="pytest"
fi
echo ""

# Step 1: Linting and Formatting
echo "📋 Step 1: Running Linting and Formatting Checks"
echo "--------------------------------------------------"

echo "🔧 Running ruff linting with auto-fix..."
$RUFF check --fix --exclude test_simulation_files --exclude decision-records --exclude worktrees --exclude ".hestai_venv" --exclude "venv"

echo "🎨 Running black code formatting..."
$BLACK . --exclude="test_simulation_files/" --exclude="decision-records/" --exclude="worktrees/" --exclude=".hestai_venv/" --exclude="venv/"

echo "📦 Running import sorting with isort..."
$ISORT . --skip-glob=".hestai_venv/*" --skip-glob="venv/*" --skip-glob="worktrees/*" --skip-glob="test_simulation_files/*" --skip-glob="decision-records/*"

echo "✅ Verifying all linting passes..."
$RUFF check --exclude test_simulation_files --exclude decision-records --exclude worktrees --exclude ".hestai_venv" --exclude "venv"

echo "✅ Step 1 Complete: All linting and formatting checks passed!"
echo ""

# Step 2: Unit Tests
echo "🧪 Step 2: Running Complete Unit Test Suite"
echo "---------------------------------------------"

echo "🏃 Running unit tests (excluding integration tests)..."
$PYTHON_CMD -m pytest tests/ -v -x -m "not integration"

echo "✅ Step 2 Complete: All unit tests passed!"
echo ""

# Step 3: Final Summary
echo "🎉 All Code Quality Checks Passed!"
echo "=================================="
echo "✅ Linting (ruff): PASSED"
echo "✅ Formatting (black): PASSED"
echo "✅ Import sorting (isort): PASSED"
echo "✅ Unit tests: PASSED"
echo ""
echo "🚀 Your code is ready for commit and GitHub Actions!"
echo "💡 Remember to add simulator tests if you modified tools"
