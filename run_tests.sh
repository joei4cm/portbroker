#!/bin/bash

# Test runner script for PortBroker
# This script runs all tests and provides a summary

set -e

echo "🚀 Running PortBroker Test Suite"
echo "================================="

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "❌ uv is not installed. Please install uv first."
    echo "Visit: https://docs.astral.sh/uv/getting-started/installation/"
    exit 1
fi

# Install dependencies if needed
echo "📦 Installing dependencies..."
uv sync --dev

# Run tests with coverage
echo "🧪 Running tests..."
if uv run pytest tests/ -v --cov=app --cov-report=html --cov-report=term-missing; then
    echo "✅ All tests passed!"
else
    echo "❌ Some tests failed!"
    exit 1
fi

# Run linting
echo "🔍 Running linting..."
echo "Running black..."
uv run black --check app/ tests/

echo "Running isort..."
uv run isort --check-only app/ tests/

echo "Running flake8..."
uv run flake8 app/ tests/

echo "Running mypy..."
uv run mypy app/

echo "✅ All checks completed!"
echo "📊 Test coverage report available in htmlcov/index.html"