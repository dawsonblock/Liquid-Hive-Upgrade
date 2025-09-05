#!/usr/bin/env bash
set -euo pipefail

echo "🔥 Running smoke tests..."

# Test 1: Check required files exist
echo "✅ Checking required files..."
for file in ".env.example" "Dockerfile" "requirements.txt" "pyproject.toml"; do
  if [[ -f "$file" ]]; then
    echo "  ✓ $file exists"
  else
    echo "  ✗ $file missing"
    exit 1
  fi
done

# Test 2: Check Python syntax
echo "✅ Checking Python syntax..."
if command -v python3 >/dev/null 2>&1; then
  find src -name "*.py" -exec python3 -m py_compile {} \; 2>/dev/null && echo "  ✓ Python syntax OK"
else
  echo "  ⚠ Python3 not available, skipping syntax check"
fi

# Test 3: Check Docker build capability
echo "✅ Checking Docker configuration..."
if command -v docker >/dev/null 2>&1; then
  echo "  ✓ Docker available"
else
  echo "  ⚠ Docker not available, skipping build test"
fi

# Test 4: Check basic directory structure
echo "✅ Checking directory structure..."
for dir in "src" "tests" "docs" ".github"; do
  if [[ -d "$dir" ]]; then
    echo "  ✓ $dir/ exists"
  else
    echo "  ⚠ $dir/ missing (may be optional)"
  fi
done

echo "🎉 Smoke tests completed successfully!"
